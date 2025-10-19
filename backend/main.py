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
import psycopg2
import psycopg2.extras

# Your local helpers
from backend.ipfs import put_json, get_json
from backend.hashutil import canonical_bytes, compute_action_hash, bundle_for_hash
from backend.merkle import leaf_hash

# Try to import blockchain helpers (optional)
try:
    from backend.eth import get_contract, get_w3
    from backend.chain_config import load_contract_info, ContractConfigError
    from backend.policies import evaluate_policies
    HAS_BLOCKCHAIN = True
except ImportError:
    HAS_BLOCKCHAIN = False
    class ContractConfigError(Exception):
        pass

# -----------------------------
# Environment & Database
# -----------------------------
load_dotenv("backend/.env")

DB_URL = os.getenv("DATABASE_URL")
S3_BUCKET = os.getenv("S3_BUCKET", "audit-traces")

if not DB_URL:
    raise RuntimeError("DATABASE_URL not set in .env file!")

def get_db():
    """Get database connection."""
    return psycopg2.connect(DB_URL)

# Optional storage (S3 helper). Fallback writes into ipfs_store/ for demo.
try:
    from backend.storage import ensure_bucket, put_bytes
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

@app.on_event("startup")
def _startup():
    try:
        ensure_bucket(S3_BUCKET)
    except Exception:
        pass
    
    # Test database connection
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        print("✓ Database connected successfully")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        raise

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

class HashBody(BaseModel):
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    ts: float

# -----------------------------
# Basic utilities & debug routes
# -----------------------------
@app.get("/health")
def health():
    # Database connectivity
    db_connected = False
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        db_connected = True
    except Exception as e:
        print(f"DB health check failed: {e}")

    # Chain connectivity (optional)
    chain_connected = False
    if HAS_BLOCKCHAIN:
        try:
            w3 = get_w3()
            chain_connected = w3.is_connected()
        except Exception:
            pass

    return {
        "ok": True,
        "chainConnected": chain_connected,
        "dbConnected": db_connected,
        "timestamp": int(time()),
    }

@app.get("/debug/contract-info")
def debug_contract_info():
    if not HAS_BLOCKCHAIN:
        raise HTTPException(status_code=501, detail="Blockchain not configured")
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
# Agent Management (Database-backed)
# -----------------------------
@app.post("/agents")
def register_agent(payload: Dict[str, Any]):
    """Create a new agent in the database."""
    try:
        agent_id = payload.get("id") or f"0x{uuid.uuid4().hex[:40]}"
        
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO agents (id, name, owner_org, pubkey, stake_address, agent_type, description)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, name, agent_type, description, created_at
                    """,
                    (
                        agent_id,
                        payload.get("name", "Unnamed Agent"),
                        payload.get("owner_org"),
                        payload.get("pubkey", ""),
                        payload.get("stake_address"),
                        payload.get("type", "general"),
                        payload.get("description", "")
                    ),
                )
                row = cur.fetchone()
                conn.commit()
                
                return {
                    "ok": True,
                    "agent": {
                        "id": row[0],
                        "address": row[0],
                        "agent": row[0],
                        "name": row[1],
                        "type": row[2],
                        "description": row[3],
                        "created_at": row[4].isoformat() if row[4] else None,
                        "points": 0
                    }
                }
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(status_code=400, detail="Agent ID already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {e}")

@app.get("/agents")
def list_agents():
    """List all agents from database."""
    try:
        with get_db() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT 
                        id,
                        name,
                        agent_type,
                        description,
                        owner_org,
                        created_at
                    FROM agents
                    ORDER BY created_at DESC
                """)
                rows = cur.fetchall()
                
                agents = []
                for row in rows:
                    agents.append({
                        "agent": row["id"],
                        "address": row["id"],
                        "name": row["name"],
                        "type": row["agent_type"],
                        "description": row["description"],
                        "owner_org": row["owner_org"],
                        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                        "points": 0  # Can calculate from actions later
                    })
                
                return {"agents": agents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {e}")

@app.get("/agents/{agent_address}")
def get_agent(agent_address: str):
    """Get a specific agent's details."""
    try:
        with get_db() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT 
                        id,
                        name,
                        agent_type,
                        description,
                        owner_org,
                        created_at
                    FROM agents
                    WHERE id = %s
                """, (agent_address,))
                row = cur.fetchone()
                
                if not row:
                    raise HTTPException(status_code=404, detail="Agent not found")
                
                return {
                    "agent": row["id"],
                    "address": row["id"],
                    "name": row["name"],
                    "type": row["agent_type"],
                    "description": row["description"],
                    "owner_org": row["owner_org"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "points": 0
                }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent: {e}")

@app.get("/agents/{agent_address}/actions")
def get_agent_actions(agent_address: str):
    """Get all actions for a specific agent."""
    try:
        # Verify agent exists
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM agents WHERE id = %s", (agent_address,))
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="Agent not found")
        
        # Try blockchain if available
        if HAS_BLOCKCHAIN:
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
        
        # Return empty if no blockchain
        return {"agent": agent_address, "points": 0, "actions": []}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent actions: {e}")

@app.post("/agents/{agent_address}/actions")
def log_agent_action(agent_address: str, payload: Dict[str, Any]):
    """Log an action for a specific agent."""
    try:
        # Verify agent exists
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM agents WHERE id = %s", (agent_address,))
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="Agent not found")
        
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

        # Store to IPFS
        cid = put_json(record)
        action_hash = compute_action_hash(inputs, outputs, ts)
        
        # Try blockchain if available
        tx_hash_hex = f"mock_{uuid.uuid4().hex[:16]}"
        if HAS_BLOCKCHAIN:
            try:
                hash_bytes = bytes.fromhex(action_hash[2:])
                w3 = get_w3()
                contract = get_contract()
                tx_hash = contract.functions.recordActionFor(agent_address, hash_bytes, cid, ts)\
                                           .transact({"from": w3.eth.accounts[0]})
                tx_hash_hex = tx_hash.hex()
            except Exception as e:
                print(f"Blockchain logging failed (using mock): {e}")

        return {
            "ok": True,
            "cid": cid,
            "hash": action_hash,
            "timestamp": ts,
            "txHash": tx_hash_hex
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log action: {e}")

@app.post("/agents/{agent_address}/evaluate")
def evaluate_agent_action(agent_address: str, payload: Dict[str, Any]):
    """Evaluate an agent action."""
    try:
        # Verify agent exists
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM agents WHERE id = %s", (agent_address,))
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="Agent not found")
        
        index = int(payload["index"])
        good = bool(payload["good"])
        delta = int(payload.get("delta", 1))
        reason = str(payload.get("reason", "manual evaluation"))

        # Blockchain evaluation if available
        if HAS_BLOCKCHAIN:
            try:
                w3 = get_w3()
                contract = get_contract()
                tx_hash = contract.functions.evaluateAction(agent_address, index, good, delta, reason)\
                                           .transact({"from": w3.eth.accounts[0]})
                points = int(contract.functions.getPoints(agent_address).call())
                return {"ok": True, "points": points, "txHash": tx_hash.hex()}
            except Exception as e:
                print(f"Blockchain evaluation failed: {e}")
        
        # Mock response
        points = delta if good else -delta
        return {
            "ok": True,
            "points": points,
            "txHash": f"mock_{uuid.uuid4().hex[:16]}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to evaluate action: {e}")

# -----------------------------
# Catalogs & Analytics
# -----------------------------
@app.get("/agent-types")
def get_agent_types():
    return {
        "types": [
            {"id": "general", "name": "General Purpose", "description": "Versatile agent",
             "capabilities": ["text_generation", "question_answering", "summarization"], 
             "default_threshold": 0.8, "icon": "fas fa-robot"},
            {"id": "financial", "name": "Financial Advisor", "description": "Finance-focused",
             "capabilities": ["market_analysis", "risk_assessment", "investment_advice"], 
             "default_threshold": 0.9, "icon": "fas fa-chart-line"},
            {"id": "medical", "name": "Medical Assistant", "description": "Healthcare domain",
             "capabilities": ["symptom_analysis", "drug_interactions", "medical_guidance"], 
             "default_threshold": 0.95, "icon": "fas fa-user-md"},
            {"id": "legal", "name": "Legal Advisor", "description": "Legal analysis",
             "capabilities": ["contract_review", "legal_research", "compliance_check"], 
             "default_threshold": 0.9, "icon": "fas fa-gavel"},
            {"id": "technical", "name": "Technical Support", "description": "Support & debugging",
             "capabilities": ["debugging", "code_review", "system_diagnostics"], 
             "default_threshold": 0.85, "icon": "fas fa-code"},
        ]
    }

@app.get("/agents/{agent_address}/analytics")
def get_agent_analytics(agent_address: str):
    """Get analytics for an agent."""
    try:
        # Verify agent exists
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM agents WHERE id = %s", (agent_address,))
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="Agent not found")

        # Mock analytics for now
        now = int(time())
        performance_data = []
        for i in range(7):
            performance_data.append({
                "date": now - (6 - i) * 86400,
                "points": max(0, 100 - (6 - i) * 10),
                "actions": max(0, 20 - (6 - i) * 2),
            })

        return {
            "agent": agent_address,
            "metrics": {
                "total_points": 100,
                "total_actions": 20,
                "success_rate": 0.75,
                "performance_trend": "up",
            },
            "performance_data": performance_data,
            "recent_evaluations": [],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {e}")

@app.get("/leaderboard")
def get_leaderboard():
    """Get agent leaderboard."""
    try:
        with get_db() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT id, name, agent_type
                    FROM agents
                    ORDER BY created_at DESC
                    LIMIT 10
                """)
                rows = cur.fetchall()
                
                board = []
                for i, row in enumerate(rows):
                    board.append({
                        "rank": i + 1,
                        "agent": row["id"],
                        "name": row["name"],
                        "points": 100 - (i * 10),  # Mock points
                        "action_count": 20 - (i * 2)  # Mock action count
                    })
                
                return {"leaderboard": board, "total_agents": len(board)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get leaderboard: {e}")

# -----------------------------
# Logs (Mock)
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
# Runs (Attestations)
# -----------------------------
@app.post("/runs")
def ingest_run(att: RunAttestation):
    try:
        att_d = att.model_dump()
        to_verify = {k: att_d[k] for k in att_d if k != "signature"}
        msg = json.dumps(to_verify, sort_keys=True, separators=(",", ":")).encode()

        with get_db() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT pubkey FROM agents WHERE id=%s", (att.agent_id,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="unknown agent")

        key = f"attestations/{att.agent_id}/{att.run_id}.json"
        put_bytes(S3_BUCKET, key, msg)

        if HAS_BLOCKCHAIN:
            status, summary, findings = evaluate_policies(att_d)
        else:
            status, summary, findings = "pass", {}, []

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO runs (id, agent_id, started_at, finished_at, model_name, model_version, container_digest,
                                      input_hash, output_hash, trace_hash, s3_trace_key, params, claim, signature, policy_summary, status)
                    VALUES (%s,%s, to_timestamp(%s), to_timestamp(%s), %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
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
                conn.commit()

        return {"ok": True, "run_id": att.run_id, "leaf": leaf_hash(msg)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ingest_run failed: {e}")

@app.get("/agents/{agent_id}/runs")
def list_runs(agent_id: str):
    try:
        with get_db() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(
                    "SELECT * FROM runs WHERE agent_id=%s ORDER BY created_at DESC LIMIT 50",
                    (agent_id,),
                )
                return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"list_runs failed: {e}")

# -----------------------------
# On-chain events (optional)
# -----------------------------
@app.get("/actions")
def list_actions(
    from_block: int = Query(0, description="Start block (0 = genesis)"),
    to_block: str = Query("latest", description='"latest" or block number')
) -> List[Dict[str, Any]]:
    if not HAS_BLOCKCHAIN:
        return []
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
# Dev entrypoint
# -----------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)