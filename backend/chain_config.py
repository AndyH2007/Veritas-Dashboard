# backend/chain_config.py
import json, pathlib

ARTIFACTS = (pathlib.Path(__file__).resolve().parents[1] / "artifacts").resolve()

ABI_PATH = ARTIFACTS / "contracts" / "AgentVerifier.sol" / "AgentVerifier.json"
DEPLOYMENT_PATH = ARTIFACTS / "deployments" / "AgentVerifier.json"

class ContractConfigError(RuntimeError):
    pass

def load_contract_info():
    # 1) Check ABI
    if not ABI_PATH.exists():
        raise ContractConfigError(
            f"ABI not found at {ABI_PATH}. Did you run `npm run deploy:localhost`?"
        )
    abi_json = json.loads(ABI_PATH.read_text(encoding="utf-8"))
    abi = abi_json.get("abi")
    if not abi:
        raise ContractConfigError(f"ABI missing in {ABI_PATH}")

    # 2) Check address
    if not DEPLOYMENT_PATH.exists():
        raise ContractConfigError(
            f"Deployment file not found at {DEPLOYMENT_PATH}. "
            "Make sure your deploy script writes a JSON like "
            '{"address":"0x..."} there.'
        )
    deployment = json.loads(DEPLOYMENT_PATH.read_text(encoding="utf-8"))
    address = deployment.get("address")
    if not address:
        raise ContractConfigError(
            f"`address` key missing in {DEPLOYMENT_PATH}. "
            "Update scripts/deploy.js to write it."
        )

    return address, abi
