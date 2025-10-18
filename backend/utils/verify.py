"""
Smart contract integration for AgentVerifier
Handles blockchain interactions and contract calls
"""

import os
from web3 import Web3
from eth_account import Account
from typing import Optional, Dict, Any
import json


class AgentVerifierContract:
    """Interface for AgentVerifier smart contract."""
    
    def __init__(self, rpc_url: str, contract_address: str, private_key: Optional[str] = None):
        """
        Initialize contract interface.
        
        Args:
            rpc_url: Ethereum RPC endpoint
            contract_address: Deployed contract address
            private_key: Private key for signing transactions (optional)
        """
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.contract_address = contract_address
        self.private_key = private_key
        
        if private_key:
            self.account = Account.from_key(private_key)
            self.w3.eth.default_account = self.account.address
        else:
            self.account = None
        
        # Load contract ABI (will be populated from artifacts)
        self.contract_abi = self._load_contract_abi()
        self.contract = self.w3.eth.contract(
            address=contract_address,
            abi=self.contract_abi
        )
    
    def _load_contract_abi(self) -> list:
        """Load contract ABI from artifacts."""
        try:
            # Try to load from artifacts
            artifacts_path = os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "contracts", "AgentVerifier.sol", "AgentVerifier.json")
            with open(artifacts_path, 'r') as f:
                artifact = json.load(f)
                return artifact['abi']
        except:
            # Fallback ABI for basic functionality
            return [
                {
                    "inputs": [
                        {"internalType": "bytes32", "name": "_hash", "type": "bytes32"},
                        {"internalType": "string", "name": "_cid", "type": "string"},
                        {"internalType": "uint256", "name": "_ts", "type": "uint256"}
                    ],
                    "name": "recordAction",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                {
                    "anonymous": False,
                    "inputs": [
                        {"indexed": True, "internalType": "address", "name": "agent", "type": "address"},
                        {"indexed": False, "internalType": "bytes32", "name": "hash", "type": "bytes32"},
                        {"indexed": False, "internalType": "string", "name": "cid", "type": "string"},
                        {"indexed": False, "internalType": "uint256", "name": "ts", "type": "uint256"},
                        {"indexed": True, "internalType": "uint256", "name": "actionIndex", "type": "uint256"}
                    ],
                    "name": "ActionRecorded",
                    "type": "event"
                }
            ]
    
    def record_action(self, hash_bytes: bytes, cid: str, timestamp: int) -> Optional[str]:
        """
        Record an action on the blockchain.
        
        Args:
            hash_bytes: 32-byte hash of the action
            cid: IPFS content identifier
            timestamp: Unix timestamp
            
        Returns:
            Transaction hash if successful, None if failed
        """
        try:
            if not self.account:
                print("No private key provided, cannot sign transactions")
                return None
            
            # Build transaction
            transaction = self.contract.functions.recordAction(
                hash_bytes, cid, timestamp
            ).build_transaction({
                'from': self.account.address,
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
            })
            
            # Sign and send transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                return tx_hash.hex()
            else:
                print("Transaction failed")
                return None
                
        except Exception as e:
            print(f"Contract interaction error: {e}")
            return None
    
    def get_action_count(self, agent_address: str) -> int:
        """Get number of actions for an agent."""
        try:
            return self.contract.functions.getActionCount(agent_address).call()
        except Exception as e:
            print(f"Error getting action count: {e}")
            return 0
    
    def get_action(self, agent_address: str, index: int) -> Optional[Dict[str, Any]]:
        """Get specific action for an agent."""
        try:
            result = self.contract.functions.getAction(agent_address, index).call()
            return {
                'hash': result[0].hex(),
                'cid': result[1],
                'timestamp': result[2]
            }
        except Exception as e:
            print(f"Error getting action: {e}")
            return None
    
    def get_latest_events(self, from_block: int = 0) -> list:
        """Get latest ActionRecorded events."""
        try:
            events = self.contract.events.ActionRecorded.get_logs(fromBlock=from_block)
            return [
                {
                    'agent': event['args']['agent'],
                    'hash': event['args']['hash'].hex(),
                    'cid': event['args']['cid'],
                    'timestamp': event['args']['ts'],
                    'actionIndex': event['args']['actionIndex'],
                    'blockNumber': event['blockNumber'],
                    'transactionHash': event['transactionHash'].hex()
                }
                for event in events
            ]
        except Exception as e:
            print(f"Error getting events: {e}")
            return []


def get_contract_instance() -> Optional[AgentVerifierContract]:
    """Get configured contract instance."""
    try:
        # Load from environment or use defaults
        rpc_url = os.getenv('WEB3_PROVIDER_URI', 'http://127.0.0.1:8545')
        contract_address = os.getenv('CONTRACT_ADDRESS', '0x5FbDB2315678afecb367f032d93F642f64180aa3')
        private_key = os.getenv('PRIVATE_KEY')
        
        return AgentVerifierContract(rpc_url, contract_address, private_key)
    except Exception as e:
        print(f"Error creating contract instance: {e}")
        return None


# Example usage
if __name__ == "__main__":
    # Test contract connection
    contract = get_contract_instance()
    
    if contract:
        print(f"Connected to contract at {contract.contract_address}")
        print(f"Account: {contract.account.address if contract.account else 'No account'}")
        
        # Test getting action count
        count = contract.get_action_count(contract.account.address if contract.account else "0x0")
        print(f"Action count: {count}")
        
        # Test getting events
        events = contract.get_latest_events()
        print(f"Latest events: {len(events)}")
    else:
        print("Failed to connect to contract")

