import hashlib

def sha256(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()

def build_merkle_root(items):
    # Step 1: hash all items (leaves)
    layer = [sha256(x) for x in items]
    print("Level 0 (leaves):", layer)   # 👈 show initial hashes

    level = 1
    # Step 2: keep building until one hash remains
    while len(layer) > 1:
        new_layer = []
        for i in range(0, len(layer), 2):
            left = layer[i]
            right = layer[i+1] if i+1 < len(layer) else left
            new_layer.append(sha256(left + right))

        print(f"Level {level}:", new_layer)   # 👈 show each level
        level += 1
        layer = new_layer

    return layer[0]

docs = ["doc1", "doc2", "doc3", "doc4", "doc5"]
root = build_merkle_root(docs)
print("Merkle Root:", root)
