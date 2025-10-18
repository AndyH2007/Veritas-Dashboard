import os, json, uuid
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
import psycopg2, psycopg2.extras
from nacl.signing import VerifyKey
from nacl.encoding import HexEncoder

from backend.storage import ensure_bucket, put_bytes
from backend.merkle import leaf_hash
from backend.policies import evaluate_policies

load_dotenv()  # loads backend/.env

DB_URL = os.getenv("DATABASE_URL")
BUCKET = os.getenv("S3_BUCKET", "audit-traces")

app = FastAPI(title="Audit API")

def db():
    return psycopg2.connect(DB_URL)

@app.on_event("startup")
def _startup():
    ensure_bucket(BUCKET)

@app.get("/health")
def health():
    return {"ok": True}

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
