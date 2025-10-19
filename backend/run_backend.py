import os, json, pathlib, uvicorn

def resolve_contract_address():
    addr = os.getenv("CONTRACT_ADDRESS")
    if addr: return addr
    dep = pathlib.Path(__file__).resolve().parent / "citationregistry-hardhat-kit" / "deployments" / "localhost.json"
    if dep.exists():
        j = json.loads(dep.read_text(encoding="utf-8-sig"))
        if j.get("CitationRegistry"): return j["CitationRegistry"]
    raise SystemExit("CONTRACT_ADDRESS not set and deployments/localhost.json not found")

def main():
    os.environ.setdefault("ETH_RPC_URL", "http://127.0.0.1:8545")
    os.environ["CONTRACT_ADDRESS"] = resolve_contract_address()
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)

if __name__ == "__main__":
    main()
