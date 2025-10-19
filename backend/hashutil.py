# backend/hashutil.py
import json, hashlib
from typing import Any, Dict

def canonical_bytes(obj: Any) -> bytes:
    """
    Return a stable JSON byte representation:
    - Keys sorted
    - No extra spaces
    - UTF-8 encoded
    This ensures the same logical object => the same bytes => the same hash.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")

def sha256_hex(b: bytes, prefix: bool = True) -> str:
    """
    SHA-256 of bytes -> hex string. '0x' prefix is nice for blockchain contexts.
    """
    h = hashlib.sha256(b).hexdigest()
    return f"0x{h}" if prefix else h

def bundle_for_hash(inputs: Dict, outputs: Dict, ts: float | int) -> Dict:
    """
    Build the minimal canonical bundle we commit to the hash.
    IMPORTANT: Do NOT include fields that are non-deterministic or likely to vary
    (e.g., 'meta', ids, random seeds). Keep this as small and stable as possible.
    """
    return {
        "inputs": inputs,
        "outputs": outputs,
        "ts": ts,  # numeric timestamp (seconds)
    }

def compute_action_hash(inputs: Dict, outputs: Dict, ts: float | int) -> str:
    """
    Convenience wrapper: build bundle -> canonicalize -> hash -> '0x...'
    """
    bundle = bundle_for_hash(inputs, outputs, ts)
    return sha256_hex(canonical_bytes(bundle))
