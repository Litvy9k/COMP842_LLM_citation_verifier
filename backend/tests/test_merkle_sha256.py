from app.merkle_sha256 import build_merkle

def test_merkle_sha256_basic():
    root, levels = build_merkle([b"a", b"b", b"c", b"d", b"e"])
    assert isinstance(root, (bytes, bytearray))
    assert len(root) == 32
    root2, _ = build_merkle([b"a", b"b", b"c", b"d", b"e"])
    assert root == root2
