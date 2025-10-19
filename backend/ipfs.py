# backend/ipfs.py
import json, hashlib
from pathlib import Path
from typing import Any, Dict

# Put the store at the repo root: <repo>/ipfs_store/
# (parents[1] = parent of "backend" = the repo root)
REPO_ROOT = Path(__file__).resolve().parents[1]
STORE_DIR = REPO_ROOT / "ipfs_store"
STORE_DIR.mkdir(exist_ok=True)

def _canonical_bytes(obj: Any) -> bytes:
    """
    Stable JSON encoding: keys sorted, no extra spaces.
    This ensures the same object => same CID.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")

def _sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def put_json(record: Dict[str, Any]) -> str:
    """
    Save 'record' as <cid>.json and return the cid (sha256 of canonical JSON).
    """
    payload = _canonical_bytes(record)
    cid = _sha256_hex(payload)  # fake CID for the hackathon (deterministic)
    out_path = STORE_DIR / f"{cid}.json"
    out_path.write_bytes(payload)
    return cid

def get_json(cid: str) -> Dict[str, Any]:
    """
    Read back the JSON for this cid.
    Raises FileNotFoundError if not present.
    """
    in_path = STORE_DIR / f"{cid}.json"
    data = in_path.read_bytes()  # will raise if missing (good for surfacing errors)
    return json.loads(data)
