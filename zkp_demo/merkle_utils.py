import hashlib

def sha256_hex(x: bytes) -> str:
    return hashlib.sha256(x).hexdigest()

class MerkleTree:
    def __init__(self, leaves):
        self.leaves = [sha256_hex(l.encode()) for l in leaves]
        self.levels = []
        self._build()

    def _build(self):
        level = self.leaves
        self.levels.append(level)
        while len(level) > 1:
            new = []
            for i in range(0, len(level), 2):
                left = level[i]
                right = level[i+1] if i+1 < len(level) else left
                new.append(sha256_hex((left + right).encode()))
            self.levels.append(new)
            level = new
        self.root = level[0]

    def get_proof(self, index):
        proof = []
        for lvl in self.levels[:-1]:
            sibling = index ^ 1
            if sibling < len(lvl):
                proof.append({
                    "sibling": lvl[sibling],
                    "is_left": sibling < index
                })
            index //= 2
        return proof

    def verify(self, leaf, proof, root):
        node = sha256_hex(leaf.encode())
        for p in proof:
            sib = p["sibling"]
            if p["is_left"]:
                node = sha256_hex((sib + node).encode())
            else:
                node = sha256_hex((node + sib).encode())
        return node == root

