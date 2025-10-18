import hashlib

def leaf_hash(canonical_bytes: bytes) -> str:
    return hashlib.sha256(canonical_bytes).hexdigest()

def merkle_root(leaves: list[str]) -> str:
    if not leaves:
        return ""
    level = [bytes.fromhex(x) for x in leaves]
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            a = level[i]
            b = level[i+1] if i+1 < len(level) else a
            nxt.append(hashlib.sha256(a + b).digest())
        level = nxt
    return level[0].hex()
