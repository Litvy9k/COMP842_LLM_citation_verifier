import json, os
from web3 import Web3
from eth_account import Account
from eth_utils import to_checksum_address

from .config import (
    WEB3_PROVIDER_URI, PRIVATE_KEY, CHAIN_ID, REGISTRY_ADDRESS,
    REGISTRY_ABI_PATH, REGISTRY_ABI_JSON,
    FN_REGISTER, FN_GET_DOCID_BY_DOI, FN_GET_DOCID_BY_TAH, FN_GET_PAPER
)

class RegistryClient:
    def __init__(self):
        self.web3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER_URI))
        if not self.web3.is_connected():
            raise RuntimeError(f"Web3 provider not connected: {WEB3_PROVIDER_URI}")
        if not PRIVATE_KEY:
            raise RuntimeError("PRIVATE_KEY missing")
        self.account = Account.from_key(PRIVATE_KEY)
        self.chain_id = CHAIN_ID

        abi = None
        if REGISTRY_ABI_PATH and os.path.exists(REGISTRY_ABI_PATH):
            with open(REGISTRY_ABI_PATH, "r", encoding="utf-8") as f:
                abi = json.load(f)
        elif REGISTRY_ABI_JSON:
            abi = json.loads(REGISTRY_ABI_JSON)
        if not abi:
            raise RuntimeError("Contract ABI not found. Set REGISTRY_ABI_PATH or REGISTRY_ABI_JSON")

        if not REGISTRY_ADDRESS or not REGISTRY_ADDRESS.startswith("0x"):
            raise RuntimeError("REGISTRY_ADDRESS invalid")
        self.contract = self.web3.eth.contract(address=to_checksum_address(REGISTRY_ADDRESS), abi=abi)

    def get_doc_id_by_doi(self, hashed_doi: bytes) -> int:
        fn = getattr(self.contract.functions, FN_GET_DOCID_BY_DOI)
        return int(fn(hashed_doi).call())

    def get_doc_id_by_tah(self, hashed_tah: bytes) -> int:
        fn = getattr(self.contract.functions, FN_GET_DOCID_BY_TAH)
        return int(fn(hashed_tah).call())

    def get_paper(self, doc_id: int):
        fn = getattr(self.contract.functions, FN_GET_PAPER)
        return fn(int(doc_id)).call()  # (metadataRoot, fullTextRoot)

    def register(self, hashed_doi: bytes, hashed_tah: bytes, metadata_root: bytes, fulltext_root: bytes) -> str:
        fn = getattr(self.contract.functions, FN_REGISTER)
        tx = fn(hashed_doi, hashed_tah, metadata_root, fulltext_root).build_transaction({
            "from": self.account.address,
            "nonce": self.web3.eth.get_transaction_count(self.account.address),
            "chainId": self.chain_id,
            "gas": 600_000,
            "maxFeePerGas": self.web3.to_wei("2", "gwei"),
            "maxPriorityFeePerGas": self.web3.to_wei("1", "gwei"),
        })
        signed = self.account.sign_transaction(tx)
        tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1:
            raise RuntimeError("register transaction failed")
        return tx_hash.hex()
