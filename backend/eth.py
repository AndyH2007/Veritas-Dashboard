# backend/eth.py
import os
from web3 import Web3
from backend.chain_config import load_contract_info

# Use localhost Hardhat node by default
RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:8545")

_w3 = None
_contract = None

def get_w3() -> Web3:
    global _w3
    if _w3 is None:
        _w3 = Web3(Web3.HTTPProvider(RPC_URL))
        if not _w3.is_connected():
            raise RuntimeError(f"Web3 not connected. Is Hardhat node running at {RPC_URL}?")
    return _w3

def get_contract():
    global _contract
    if _contract is None:
        address, abi = load_contract_info()  # uses artifacts written by your deploy script
        _contract = get_w3().eth.contract(address=address, abi=abi)
    return _contract
