# backend/main.py

import os
import json
import uuid
from time import time
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Your local helpers
from backend.ipfs import put_json, get_json
from backend.hashutil import canonical_bytes, compute_action_hash, bundle_for_hash
from backend.eth import get_contract, get_w3
from backend.chain_config import load_contract_info, ContractConfigError
from backend.policies import evaluate_policies
from backend.merkle import leaf_hash

# -----------------------------
# Environment & optional backends
# -----------------------------
load_dotenv()  # loads backend/.env

DB_URL = os.getenv("DATABASE_URL")
S3_BUCKET = os.getenv("S3_BUCKET", "audit-traces")

# ⭐ NEW: In-memory agent registry (fallback when no DB)
MOCK_AGENTS = {}  # {agent_address: {name, type, description, created_at, points, actions}}

# Optional Postgres (psycopg2). We run fine without a DB.
HAS_DB = False
try:
    import psycopg2  # type: ignore
    import psycopg2.extras  # type: ignore
    HAS_DB = bool(DB_URL)
except Exception:
    HAS_DB = False

def db():
    """Return a psycopg2 connection if DB is configured; otherwise raise."""
    if not HAS_DB:
        raise RuntimeError("DATABASE_URL/psycopg2 not configured")
    return psycopg2.connect(DB_URL)

# Optional storage (S3 helper). Fallback writes into ipfs_store/ for demo.
try:
    from backend.storage import ensure_bucket, put_bytes  # type: ignore
except ImportError:
    from pathlib import Path
    def ensure_bucket(_bucket: str) -> None:
        (Path("ipfs_store")).mkdir(exist_ok=True)
    def put_bytes(_bucket: str, key: str, data: bytes) -> None:
        p = Path("ipfs_store") / key
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

# -----------------------------
# FastAPI app
# -----------------------------
app = FastAPI(title="Audit API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # for local dev; tighten for prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Make sure our local 'bucket' exists (no-op on fallback)
@app.on_event("startup")
def _startup():
    try:
        ensure_bucket(S3_BUCKET)
    except Exception:
        # Non-fatal: we can still serve chain/IPFS features
        pass

# -----------------------------
# Schemas
# -----------------------------
class PutBody(BaseModel):
    record: Dict[str, Any]

class RunAttestation(BaseModel):
    agent_id: str
    run_id: str
    started_at: float
    finished_at: float
    model_name: str
    model_version: str
    container_digest: str
    params: Dict[str, Any]
    input_hash: str
    output_hash: str
    claims: Optional[Dict[str, Any]] = None
    trace_hash: Optional[str] = None
    signature: str

class LogBody(BaseModel):
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    meta: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "inputs": {"prompt": "buy 1 BTC", "account": "A123"},
                "outputs": {"decision": "approve", "reason": "ok"},
                "meta": {"agent_id": "demo-agent", "type": "order", "amount_usd": 5000}
            }
        }

class HashBody(BaseModel):
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    ts: float

# -----------------------------
# Basic utilities & debug routes
# -----------------------------
@app.get("/health")
def health():
    # Chain connectivity
    try:
        w3 = get_w3()
        chain_connected = w3.is_connected()
    except Exception:
        chain_connected = False

    # DB connectivity (optional)
    db_connected = False
    if HAS_DB:
        try:
            with db() as cx:
                cx.cursor().execute("SELECT 1")
            db_connected = True
        except Exception:
            db_connected = False

    return {
        "ok": True,
        "chainConnected": chain_connected,
        "dbConnected": db_connected,
        "timestamp": int(time()),
    }

@app.get("/debug/contract-info")
def debug_contract_info():
    try:
        address, abi = load_contract_info()
        fn_names = [it.get("name") for it in abi if it.get("type") == "function"]
        return {
            "ok": True,
            "address": address,
            "abi_functions_count": len(fn_names),
            "sample_functions": fn_names[:5],
        }
    except ContractConfigError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/debug/ipfs-put")
def debug_ipfs_put(body: PutBody):
    try:
        cid = put_json(body.record)
        return {"ok": True, "cid": cid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ipfs-put failed: {e}")

@app.get("/ipfs/{cid}")
def ipfs_get(cid: str):
    try:
        return get_json(cid)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"cid not found: {cid}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ipfs-get failed: {e}")

@app.post("/debug/hash")
def debug_hash(body: HashBody):
    try:
        bundle = bundle_for_hash(body.inputs, body.outputs, body.ts)
        canon = canonical_bytes(bundle).decode("utf-8")
        digest = compute_action_hash(body.inputs, body.outputs, body.ts)
        return {"ok": True, "canonical_json": canon, "hash": digest}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"hashing failed: {e}")

# -----------------------------
# On-chain events view (optional helper)
# -----------------------------
@app.get("/actions")
def list_actions(
    from_block: int = Query(0, description="Start block (0 = genesis)"),
    to_block: str = Query("latest", description='"latest" or block number')
) -> List[Dict[str, Any]]:
    try:
        contract = get_contract()
        event_abi = contract.events.ActionRecorded
        logs = event_abi().get_logs(from_block=from_block, to_block=to_block)

        out = []
        for log in logs:
            args = log["args"]
            out.append({
                "actor": args.get("actor"),
                "hash": args.get("hash"),
                "cid": args.get("cid"),
                "ts": int(args.get("ts")),
                "block": log["blockNumber"],
                "txHash": log["transactionHash"].hex(),
            })
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"/actions failed: {e}")

# -----------------------------
# ⭐ FIXED: Agent registry with mock fallback
# -----------------------------
@app.post("/agents")
def register_agent(payload: Dict[str, Any]):
    """Create a new agent - works with or without DB."""
    agent_id = payload.get("id") or f"0x{uuid.uuid4().hex[:40]}"
    
    # Try blockchain first (if available)
    try:
        w3 = get_w3()
        contract = get_contract()
        # If your contract has a registerAgent function, call it here
        # For now, we'll just use mock storage
    except Exception:
        pass
    
    # Store in mock registry (in-memory)
    MOCK_AGENTS[agent_id] = {
        "id": agent_id,
        "address": agent_id,
        "agent": agent_id,
        "name": payload.get("name", "Unnamed Agent"),
        "type": payload.get("type", "general"),
        "description": payload.get("description", ""),
        "owner_org": payload.get("owner_org"),
        "pubkey": payload.get("pubkey", ""),
        "stake_address": payload.get("stake_address"),
        "created_at": int(time()),
        "points": 0,
        "actions": []
    }
    
    # If DB is available, also store there
    if HAS_DB:
        try:
            with db() as cx, cx.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO agents (id, name, owner_org, pubkey, stake_address)
                    VALUES (%s,%s,%s,%s,%s)
                    """,
                    (
                        agent_id,
                        payload.get("name"),
                        payload.get("owner_org"),
                        payload.get("pubkey", ""),
                        payload.get("stake_address"),
                    ),
                )
        except Exception:
            pass  # Non-fatal if DB insert fails
    
    return {"ok": True, "agent": MOCK_AGENTS[agent_id]}

@app.get("/agents")
def list_agents():
    """List agents from blockchain, DB, or mock storage."""
    # Try blockchain first
    try:
        contract = get_contract()
        addresses = contract.functions.listAgents().call()
        agents = []
        for addr in addresses:
            points = int(contract.functions.getPoints(addr).call())
            # Merge with mock data if available
            mock_data = MOCK_AGENTS.get(addr, {})
            agents.append({
                "agent": addr,
                "address": addr,
                "points": points,
                "name": mock_data.get("name", f"Agent {addr[:8]}..."),
                "type": mock_data.get("type", "general")
            })
        agents.sort(key=lambda x: x["points"], reverse=True)
        return {"agents": agents}
    except Exception:
        pass
    
    # Try DB fallback
    if HAS_DB:
        try:
            with db() as cx, cx.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT id, name, owner_org FROM agents ORDER BY created_at DESC")
                agents = []
                for row in cur.fetchall():
                    agents.append({
                        "agent": row["id"],
                        "address": row["id"],
                        "points": 0,
                        "name": row["name"],
                        "owner_org": row["owner_org"]
                    })
                return {"agents": agents}
        except Exception:
            pass
    
    # Use mock storage
    agents = []
    for agent_id, data in MOCK_AGENTS.items():
        agents.append({
            "agent": agent_id,
            "address": agent_id,
            "points": data.get("points", 0),
            "name": data.get("name", "Unnamed Agent"),
            "type": data.get("type", "general"),
            "created_at": data.get("created_at")
        })
    agents.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return {"agents": agents}

@app.get("/agents/{agent_address}/actions")
def get_agent_actions(agent_address: str):
    """Get all actions for a specific agent with points."""
    # Try blockchain first
    try:
        contract = get_contract()
        points = int(contract.functions.getPoints(agent_address).call())
        actions = contract.functions.getAllActions(agent_address).call()
        formatted = []
        for i, a in enumerate(actions):
            h, cid, ts = a
            hhex = h.hex() if hasattr(h, "hex") else str(h)
            formatted.append({
                "index": i,
                "hash": hhex,
                "cid": cid,
                "timestamp": int(ts),
                "hash_short": f"{hhex[:8]}...{hhex[-8:]}" if hhex.startswith("0x") else hhex,
            })
        formatted.sort(key=lambda x: x["timestamp"], reverse=True)
        return {"agent": agent_address, "points": points, "actions": formatted}
    except Exception:
        pass
    
    # Use mock storage
    if agent_address in MOCK_AGENTS:
        agent_data = MOCK_AGENTS[agent_address]
        return {
            "agent": agent_address,
            "points": agent_data.get("points", 0),
            "actions": agent_data.get("actions", [])
        }
    
    return {"agent": agent_address, "points": 0, "actions": []}

@app.post("/agents/{agent_address}/actions")
def log_agent_action(agent_address: str, payload: Dict[str, Any]):
    """Log an action for a specific agent."""
    try:
        ts = int(time())
        inputs = payload.get("inputs", {}) or {}
        outputs = payload.get("outputs", {}) or {}
        
        record = {
            "agent": agent_address,
            "model": payload.get("model", ""),
            "model_hash": payload.get("model_hash", ""),
            "dataset_id": payload.get("dataset_id", ""),
            "dataset_hash": payload.get("dataset_hash", ""),
            "inputs": inputs,
            "outputs": outputs,
            "notes": payload.get("notes", ""),
            "timestamp": ts,
            "version": "v1",
        }

        # Store to mock IPFS
        cid = put_json(record)
        action_hash = compute_action_hash(inputs, outputs, ts)
        
        # Try blockchain
        try:
            hash_bytes = bytes.fromhex(action_hash[2:])
            w3 = get_w3()
            contract = get_contract()
            tx_hash = contract.functions.recordActionFor(agent_address, hash_bytes, cid, ts)\
                                       .transact({"from": w3.eth.accounts[0]})
            tx_hash_hex = tx_hash.hex()
        except Exception:
            tx_hash_hex = f"mock_{uuid.uuid4().hex[:16]}"
        
        # Store in mock registry
        if agent_address not in MOCK_AGENTS:
            MOCK_AGENTS[agent_address] = {
                "id": agent_address,
                "address": agent_address,
                "agent": agent_address,
                "name": f"Agent {agent_address[:8]}...",
                "points": 0,
                "actions": []
            }
        
        action_data = {
            "index": len(MOCK_AGENTS[agent_address]["actions"]),
            "hash": action_hash,
            "cid": cid,
            "timestamp": ts,
            "model": payload.get("model", ""),
            "status": "pending"
        }
        MOCK_AGENTS[agent_address]["actions"].append(action_data)

        return {
            "ok": True,
            "cid": cid,
            "hash": action_hash,
            "timestamp": ts,
            "txHash": tx_hash_hex
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log action: {e}")

@app.post("/agents/{agent_address}/evaluate")
def evaluate_agent_action(agent_address: str, payload: Dict[str, Any]):
    """Evaluate an agent action (good/bad) and adjust points."""
    try:
        index = int(payload["index"])
        good = bool(payload["good"])
        delta = int(payload.get("delta", 1))
        reason = str(payload.get("reason", "manual evaluation"))

        # Try blockchain
        try:
            w3 = get_w3()
            contract = get_contract()
            tx_hash = contract.functions.evaluateAction(agent_address, index, good, delta, reason)\
                                       .transact({"from": w3.eth.accounts[0]})
            points = int(contract.functions.getPoints(agent_address).call())
        except Exception:
            # Use mock
            if agent_address in MOCK_AGENTS:
                if good:
                    MOCK_AGENTS[agent_address]["points"] += delta
                else:
                    MOCK_AGENTS[agent_address]["points"] -= delta
                points = MOCK_AGENTS[agent_address]["points"]
                tx_hash = f"mock_{uuid.uuid4().hex[:16]}"
            else:
                points = 0
                tx_hash = "mock_no_agent"
        
        return {
            "ok": True,
            "points": points,
            "txHash": tx_hash if isinstance(tx_hash, str) else tx_hash.hex()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to evaluate action: {e}")

# -----------------------------
# Catalogs / Analytics / Leaderboard (demo-friendly)
# -----------------------------
@app.get("/agent-types")
def get_agent_types():
    return {
        "types": [
            {"id": "general",   "name": "General Purpose",  "description": "Versatile agent",
             "capabilities": ["text_generation", "question_answering", "summarization"], "default_threshold": 0.8, "icon": "fas fa-robot"},
            {"id": "financial", "name": "Financial Advisor","description": "Finance-focused",
             "capabilities": ["market_analysis", "risk_assessment", "investment_advice"], "default_threshold": 0.9, "icon": "fas fa-chart-line"},
            {"id": "medical",   "name": "Medical Assistant","description": "Healthcare domain",
             "capabilities": ["symptom_analysis", "drug_interactions", "medical_guidance"], "default_threshold": 0.95, "icon": "fas fa-user-md"},
            {"id": "legal",     "name": "Legal Advisor",    "description": "Legal analysis",
             "capabilities": ["contract_review", "legal_research", "compliance_check"], "default_threshold": 0.9, "icon": "fas fa-gavel"},
            {"id": "technical", "name": "Technical Support","description": "Support & debugging",
             "capabilities": ["debugging", "code_review", "system_diagnostics"], "default_threshold": 0.85, "icon": "fas fa-code"},
        ]
    }

@app.get("/agents/{agent_address}/analytics")
def get_agent_analytics(agent_address: str):
    """Lightweight demo analytics."""
    try:
        # Try blockchain
        try:
            contract = get_contract()
            points = int(contract.functions.getPoints(agent_address).call())
            actions = contract.functions.getAllActions(agent_address).call()
            total_actions = len(actions)
        except Exception:
            # Use mock
            if agent_address in MOCK_AGENTS:
                points = MOCK_AGENTS[agent_address].get("points", 0)
                total_actions = len(MOCK_AGENTS[agent_address].get("actions", []))
            else:
                points = 0
                total_actions = 0

        success_rate = 0.75 if total_actions else 0.0
        performance_data = []
        now = int(time())
        for i in range(7):
            performance_data.append({
                "date": now - (6 - i) * 86400,
                "points": max(0, points - (6 - i) * 10),
                "actions": max(0, total_actions - (6 - i) * 2),
            })

        return {
            "agent": agent_address,
            "metrics": {
                "total_points": points,
                "total_actions": total_actions,
                "success_rate": success_rate,
                "performance_trend": "up" if points > 0 else "stable",
            },
            "performance_data": performance_data,
            "recent_evaluations": [],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {e}")

@app.get("/leaderboard")
def get_leaderboard():
    """Top agents by points."""
    try:
        # Try blockchain
        try:
            contract = get_contract()
            addrs = contract.functions.listAgents().call()
            board = []
            for a in addrs:
                pts = int(contract.functions.getPoints(a).call())
                cnt = int(contract.functions.getActionCount(a).call())
                board.append({"agent": a, "points": pts, "action_count": cnt})
        except Exception:
            # Use mock
            board = []
            for agent_id, data in MOCK_AGENTS.items():
                board.append({
                    "agent": agent_id,
                    "points": data.get("points", 0),
                    "action_count": len(data.get("actions", []))
                })
        
        board.sort(key=lambda x: (x["points"], x["action_count"]), reverse=True)
        for i, row in enumerate(board):
            row["rank"] = i + 1
        return {"leaderboard": board[:10], "total_agents": len(board)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get leaderboard: {e}")

# -----------------------------
# Logs (mock)
# -----------------------------
@app.post("/agents/{agent_address}/logs")
def add_agent_log(agent_address: str, payload: Dict[str, Any]):
    try:
        level = str(payload.get("level", "info"))
        message = str(payload.get("message", ""))
        ts = int(time())
        return {"ok": True, "log_id": f"{agent_address}_{ts}", "timestamp": ts, "level": level, "message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add log: {e}")

@app.get("/agents/{agent_address}/logs")
def get_agent_logs(agent_address: str, limit: int = 50):
    try:
        logs = []
        now = int(time())
        for i in range(min(limit, 10)):
            logs.append({
                "timestamp": now - i * 3600,
                "level": ["info", "warning", "error"][i % 3],
                "message": f"Mock log message {i+1} for agent {agent_address}",
            })
        return {"agent": agent_address, "logs": logs, "total": len(logs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {e}")

# -----------------------------
# Runs (DB-only features; gated)
# -----------------------------
@app.post("/runs")
def ingest_run(att: RunAttestation):
    if not HAS_DB:
        raise HTTPException(status_code=501, detail="Database not configured")
    try:
        att_d = att.model_dump()
        to_verify = {k: att_d[k] for k in att_d if k != "signature"}
        msg = json.dumps(to_verify, sort_keys=True, separators=(",", ":")).encode()

        with db() as cx, cx.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT pubkey FROM agents WHERE id=%s", (att.agent_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="unknown agent")

        key = f"attestations/{att.agent_id}/{att.run_id}.json"
        put_bytes(S3_BUCKET, key, msg)

        status, summary, findings = evaluate_policies(att_d)

        with db() as cx, cx.cursor() as cur:
            cur.execute(
                """
                INSERT INTO runs (id, agent_id, started_at, finished_at, model_name, model_version, container_digest,
                                  input_hash, output_hash, trace_hash, s3_trace_key, params, claim, signature, policy_summary, status)
                VALUES (%s,%s, to_timestamp(%s), to_timestamp(%s), %s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)
                """,
                (
                    att.run_id, att.agent_id, att.started_at, att.finished_at,
                    att.model_name, att.model_version, att.container_digest,
                    att.input_hash, att.output_hash, att.trace_hash, key,
                    json.dumps(att.params), json.dumps(att.claims or {}),
                    att.signature, json.dumps(summary), status,
                ),
            )
            for sev, code, msgtxt in findings:
                cur.execute(
                    "INSERT INTO audit_findings (id, run_id, severity, code, message) VALUES (%s,%s,%s,%s,%s)",
                    (str(uuid.uuid4()), att.run_id, sev, code, msgtxt),
                )

        return {"ok": True, "run_id": att.run_id, "leaf": leaf_hash(msg)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ingest_run failed: {e}")

@app.get("/agents/{agent_id}/runs")
def list_runs(agent_id: str):
    if not HAS_DB:
        raise HTTPException(status_code=501, detail="Database not configured")
    try:
        with db() as cx, cx.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                "SELECT * FROM runs WHERE agent_id=%s ORDER BY created_at DESC LIMIT 50",
                (agent_id,),
            )
            return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"list_runs failed: {e}")

# -----------------------------
# Dev entrypoint
# -----------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)