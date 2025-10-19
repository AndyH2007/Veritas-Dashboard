import os, json, uuid
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
import psycopg2, psycopg2.extras
from nacl.signing import VerifyKey
from nacl.encoding import HexEncoder
from time import time

from backend.storage import ensure_bucket, put_bytes
from backend.merkle import leaf_hash
from backend.policies import evaluate_policies
from fastapi import HTTPException, Query
from backend.chain_config import load_contract_info, ContractConfigError
from backend.ipfs import put_json, get_json
from backend.hashutil import canonical_bytes, compute_action_hash, bundle_for_hash
from backend.eth import get_contract, get_w3

load_dotenv()  # loads backend/.env

DB_URL = os.getenv("DATABASE_URL")
BUCKET = os.getenv("S3_BUCKET", "audit-traces")

app = FastAPI(title="Audit API")

from typing import Dict, Any, Optional, List

class PutBody(BaseModel):
    record: Dict[str, Any]

@app.post("/debug/ipfs-put")
def debug_ipfs_put(body: PutBody):
    """
    POST a JSON like {"record": {"hello": "world"}}
    Returns {"cid": "..."} and stores it under ipfs_store/<cid>.json
    """
    try:
        cid = put_json(body.record)
        return {"ok": True, "cid": cid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ipfs-put failed: {e}")

@app.get("/ipfs/{cid}")
def ipfs_get(cid: str):
    """
    GET the full JSON back by CID.
    """
    try:
        return get_json(cid)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"cid not found: {cid}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ipfs-get failed: {e}")


def db():
    return psycopg2.connect(DB_URL)

@app.on_event("startup")
def _startup():
    ensure_bucket(BUCKET)

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/debug/contract-info")
def debug_contract_info():
    try:
        address, abi = load_contract_info()
        # Keep response small: show a few function names only
        fn_names = [it.get("name") for it in abi if it.get("type") == "function"]
        return {
            "ok": True,
            "address": address,
            "abi_functions_count": len(fn_names),
            "sample_functions": fn_names[:5],
        }
    except ContractConfigError as e:
        # Return a helpful message to the browser
        raise HTTPException(status_code=500, detail=str(e))

class RunAttestation(BaseModel):
    agent_id: str
    run_id: str
    started_at: float
    finished_at: float
    model_name: str
    model_version: str
    container_digest: str
    params: dict
    input_hash: str
    output_hash: str
    claims: dict | None = None
    trace_hash: str | None = None
    signature: str

@app.get("/actions")
def list_actions(
    from_block: int = Query(0, description="Start block to scan from (0 = genesis)"),
    to_block: str = Query("latest", description='"latest" or a specific block number')
) -> List[Dict[str, Any]]:
    """
    Reads ActionRecorded events from the contract and returns a simple list:
    [
      {"actor":"0x...", "hash":"0x...", "cid":"...", "ts": 1729..., "block": 123, "txHash": "0x..."},
      ...
    ]
    """
    try:
        w3 = get_w3()
        contract = get_contract()

        # IMPORTANT: change "ActionRecorded" & arg names if your contract event differs.
        event_abi = contract.events.ActionRecorded

        # web3.py v6 pattern: use the event's get_logs
        logs = event_abi().get_logs(from_block=from_block, to_block=to_block)

        out = []
        for log in logs:
            # log.args contains the event parameters (names depend on your Solidity)
            args = log["args"]
            # Adjust these keys to match your event (hash/cid/ts/actor names):
            out.append({
                "actor": args.get("actor"),         # address
                "hash": args.get("hash"),           # string (0x... if you stored hex string)
                "cid": args.get("cid"),             # string
                "ts": int(args.get("ts")),          # uint256 -> Python int
                "block": log["blockNumber"],
                "txHash": log["transactionHash"].hex(),
            })

        return out

    except Exception as e:
        # Surface a helpful error (e.g., node not running, wrong event name)
        raise HTTPException(status_code=500, detail=f"/actions failed: {e}")


@app.post("/agents")
def register_agent(payload: dict):
    # payload = {id, name, owner_org, pubkey, stake_address?}
    with db() as cx, cx.cursor() as cur:
        cur.execute("""
            INSERT INTO agents (id, name, owner_org, pubkey, stake_address)
            VALUES (%s,%s,%s,%s,%s)
        """, (payload["id"], payload["name"], payload.get("owner_org"),
              payload["pubkey"], payload.get("stake_address")))
    return {"ok": True}

@app.post("/runs")
def ingest_run(att: RunAttestation):
    att = att.model_dump()

    # verify signature
    to_verify = {k: att[k] for k in att if k != "signature"}
    msg = json.dumps(to_verify, sort_keys=True, separators=(',', ':')).encode()

    with db() as cx, cx.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT pubkey FROM agents WHERE id=%s", (att["agent_id"],))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "unknown agent")
        vk = VerifyKey(row["pubkey"], encoder=HexEncoder)
        try:
            vk.verify(msg, bytes.fromhex(att["signature"]))
        except Exception:
            raise HTTPException(400, "invalid signature")

    # store canonical bytes as a trace artifact (demo)
    key = f"attestations/{att['agent_id']}/{att['run_id']}.json"
    put_bytes(BUCKET, key, msg)

    # evaluate policies
    status, summary, findings = evaluate_policies(att)

    with db() as cx, cx.cursor() as cur:
        cur.execute("""
        INSERT INTO runs (id, agent_id, started_at, finished_at, model_name, model_version, container_digest,
                          input_hash, output_hash, trace_hash, s3_trace_key, params, claim, signature, policy_summary, status)
        VALUES (%s,%s, to_timestamp(%s), to_timestamp(%s), %s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)
        """, (att["run_id"], att["agent_id"], att["started_at"], att["finished_at"],
              att["model_name"], att["model_version"], att["container_digest"],
              att["input_hash"], att["output_hash"], att.get("trace_hash"), key,
              json.dumps(att["params"]), json.dumps(att.get("claims") or {}),
              att["signature"], json.dumps(summary), status))

        for sev, code, msgtxt in findings:
            cur.execute("""
                INSERT INTO audit_findings (id, run_id, severity, code, message)
                VALUES (%s,%s,%s,%s,%s)
            """, (str(uuid.uuid4()), att["run_id"], sev, code, msgtxt))

    return {"ok": True, "run_id": att["run_id"], "leaf": leaf_hash(msg)}

@app.get("/agents/{agent_id}/runs")
def list_runs(agent_id: str):
    with db() as cx, cx.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT * FROM runs WHERE agent_id=%s ORDER BY created_at DESC LIMIT 50", (agent_id,))
        return [dict(r) for r in cur.fetchall()]

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

@app.post("/log-action")
def log_action(payload: LogBody):
    try:
        ts = int(time())

        # 1) Build the stable bundle (inputs, outputs, ts)
        bundle = bundle_for_hash(payload.inputs, payload.outputs, ts)

        # 2) Compute canonical SHA-256 over that bundle
        action_hash = compute_action_hash(payload.inputs, payload.outputs, ts)

        # 3) Evaluate policies using the same bundle + meta
        status, findings = evaluate_policies(bundle, payload.meta)

        # 4) Save full evidence off-chain (mock IPFS). We include status & findings for convenience
        record = {
            "hash": action_hash,
            **bundle,
            "meta": payload.meta,
            "policy": {"status": status, "findings": findings},
        }
        cid = put_json(record)

        # 5) (Optional next) Write (hash, cid, ts) to the smart contract
        #    txHash = <call your recordAction(...) and get tx hash>

        # 6) Return the receipt to the caller
        return {
            "ok": True,
            "hash": action_hash,
            "cid": cid,
            "ts": ts,
            "status": status,
            "findings": findings,
            # "txHash": txHash,  # add when you wire the contract call
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"log-action failed: {e}")

@app.post("/debug/hash")
def debug_hash(body: HashBody):
    """
    POST a minimal bundle and get back:
    - the canonical JSON (string) we hash
    - the SHA-256 hash (0x...)
    This lets you verify stability and see *exactly* what is hashed.
    """
    try:
        bundle = bundle_for_hash(body.inputs, body.outputs, body.ts)
        canon = canonical_bytes(bundle).decode("utf-8")
        digest = compute_action_hash(body.inputs, body.outputs, body.ts)
        return {"ok": True, "canonical_json": canon, "hash": digest}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"hashing failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
