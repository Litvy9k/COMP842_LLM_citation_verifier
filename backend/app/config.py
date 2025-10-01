import os
from dotenv import load_dotenv
load_dotenv()

def _to_bool(v: str, default=False) -> bool:
    if v is None: return default
    return str(v).strip().lower() in {"1","true","yes","y","on"}

WEB3_PROVIDER_URI = os.getenv("WEB3_PROVIDER_URI", "http://127.0.0.1:8545")
CHAIN_ID = int(os.getenv("CHAIN_ID", "31337"))
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
REGISTRY_ADDRESS = os.getenv("REGISTRY_ADDRESS", "")

REGISTRY_ABI_PATH = os.getenv("REGISTRY_ABI_PATH", "./contracts/registry_abi.json")
REGISTRY_ABI_JSON = os.getenv("REGISTRY_ABI_JSON", "")

FN_REGISTER = os.getenv("FN_REGISTER", "registerPaper")
FN_GET_DOCID_BY_DOI = os.getenv("FN_GET_DOCID_BY_DOI", "getDocIdByDoi")
FN_GET_DOCID_BY_TAH = os.getenv("FN_GET_DOCID_BY_TAH", "getDocIdByTAH")
FN_GET_PAPER = os.getenv("FN_GET_PAPER", "getPaper")

LOCAL_STORE_LEAVES = _to_bool(os.getenv("LOCAL_STORE_LEAVES", "true"))
DATA_DIR = os.getenv("DATA_DIR", "./data/leaves")
