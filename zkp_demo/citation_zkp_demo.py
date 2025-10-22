import json, secrets
from cryptography.fernet import Fernet
from merkle_utils import MerkleTree, sha256_hex

def make_commitment(msg: str):
    r = secrets.token_hex(16)
    c = sha256_hex((msg + r).encode())
    return c, r

def verify_commitment(msg: str, r: str, c: str):
    return c == sha256_hex((msg + r).encode())

citations = [
    {
        "doi": "10.5555/zkp.citations.2025.001",
        "title": "Privacy-Preserving Citation Registry with ZK Proofs",
        "authors": ["A. Admin", "U. User"],
        "year": 2025,
        "publisher": "DemoConf"
    },
    {
        "doi": "10.5555/zkp.citations.2025.002",
        "title": "Federated Learning for Decentralized Peer Review",
        "authors": ["M. Reviewer", "J. Scholar"],
        "year": 2025,
        "publisher": "OpenAI Press"
    },
    {
        "doi": "10.5555/zkp.citations.2025.003",
        "title": "Blockchain-based Authorship Verification Protocols",
        "authors": ["R. Researcher"],
        "year": 2024,
        "publisher": "IEEE Blockchain Symposium"
    }
]

key = Fernet.generate_key()
fernet = Fernet(key)

leaves = []
registry = []

for meta in citations:
    enc = fernet.encrypt(json.dumps(meta, sort_keys=True).encode())
    c, r = make_commitment(json.dumps(meta, sort_keys=True))
    leaf = meta["doi"] + "|" + c
    leaves.append(leaf)
    registry.append({
        "doi": meta["doi"],
        "commitment": c,
        "nonce": r,
        "cipher": enc
    })

tree = MerkleTree(leaves)
root = tree.root
print("Merkle root:", root[:24], "...")

record = registry[1]
leaf = record["doi"] + "|" + record["commitment"]
proof = tree.get_proof(1)

print("Proof verified:", tree.verify(leaf, proof, root))
print("Commitment verified:", verify_commitment(
    json.dumps(citations[1], sort_keys=True),
    record["nonce"],
    record["commitment"]
))

print("Selective disclosure:", {
    "doi": citations[1]["doi"],
    "title": citations[1]["title"]
})

plaintext = json.loads(fernet.decrypt(record["cipher"]))
print("Decrypted metadata:")
print(json.dumps(plaintext, indent=2))

