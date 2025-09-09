# Doing some experiments about the basic logic

from merklelib import MerkleTree
import hashlib
import json
import math

def canonicalize_json(obj) -> str:
    def _check_numbers(x):
        if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
            raise ValueError("NaN/Infinity not allowed in canonical JSON")
        return x

    def _walk(x):
        if isinstance(x, dict):
            return {k: _walk(_check_numbers(v)) for k, v in x.items()}
        elif isinstance(x, list):
            return [_walk(_check_numbers(v)) for v in x]
        else:
            return _check_numbers(x)

    obj = _walk(obj)
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)

sample_metadata = {
    "title": "How to cook a perfect steak",
    "author": "John Doe, Jane Doe",
    "date": "2024-06-01",
    "journal": "New York Times"
}

sample_metadata2 = {
    "title": "how to cook a perfect steak",
    "author": "john doe,jane doe",
    "date": "2024.06.01",
    "journal": "new york times"
}

print(canonicalize_json(sample_metadata))
print(canonicalize_json(sample_metadata2))