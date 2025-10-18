from typing import List, Tuple
import hashlib

def hash_leaf(data: bytes) -> bytes:
    return hashlib.sha256(b"\x00" + data).digest()

def hash_node(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()

def build_merkle(leaves_raw: List[bytes]) -> Tuple[bytes, List[List[bytes]]]:
    if not leaves_raw:
        return b"\x00"*32, []
    level = [hash_leaf(x) for x in leaves_raw]
    levels = [level]
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            a = level[i]
            b = level[i+1] if i+1 < len(level) else a
            nxt.append(hash_node(a, b))
        level = nxt
        levels.append(level)
    return level[0], levels
