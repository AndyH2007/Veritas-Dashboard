"""
IPFS integration for storing action records
Uploads {input, output, timestamp} JSON to IPFS and returns CID
"""

import json
import requests
from typing import Dict, Any, Optional
import os
from datetime import datetime


class IPFSClient:
    """Simple IPFS client for uploading and retrieving JSON records."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 5001):
        """
        Initialize IPFS client.
        
        Args:
            host: IPFS daemon host
            port: IPFS API port
        """
        self.base_url = f"http://{host}:{port}/api/v0"
        self.host = host
        self.port = port
    
    def upload_json(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Upload JSON data to IPFS and return CID.
        
        Args:
            data: Dictionary to upload as JSON
            
        Returns:
            IPFS CID if successful, None if failed
        """
        try:
            # Convert to JSON string
            json_str = json.dumps(data, indent=2)
            
            # Upload to IPFS
            files = {'file': ('data.json', json_str, 'application/json')}
            response = requests.post(f"{self.base_url}/add", files=files)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('Hash')
            else:
                print(f"IPFS upload failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"IPFS upload error: {e}")
            return None
    
    def retrieve_json(self, cid: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve JSON data from IPFS using CID.
        
        Args:
            cid: IPFS content identifier
            
        Returns:
            Parsed JSON data if successful, None if failed
        """
        try:
            response = requests.post(f"{self.base_url}/cat", params={'arg': cid})
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"IPFS retrieval failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"IPFS retrieval error: {e}")
            return None
    
    def is_connected(self) -> bool:
        """Check if IPFS daemon is running."""
        try:
            response = requests.post(f"{self.base_url}/id")
            return response.status_code == 200
        except:
            return False


def upload_action_record(input_data: Any, output_data: Any, timestamp: Optional[int] = None, agent_id: str = "default") -> Optional[str]:
    """
    Upload action record to IPFS.
    
    Args:
        input_data: Agent input
        output_data: Agent output
        timestamp: Unix timestamp (defaults to current time)
        agent_id: Agent identifier
        
    Returns:
        IPFS CID if successful, None if failed
    """
    if timestamp is None:
        timestamp = int(datetime.now().timestamp())
    
    # Create action record JSON
    record = {
        "input": input_data,
        "output": output_data,
        "timestamp": timestamp,
        "agent_id": agent_id
    }
    
    # Upload to IPFS
    client = IPFSClient()
    return client.upload_json(record)


def retrieve_action_record(cid: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve action record from IPFS.
    
    Args:
        cid: IPFS content identifier
        
    Returns:
        Action record dictionary if successful, None if failed
    """
    client = IPFSClient()
    return client.retrieve_json(cid)


# Mock IPFS for development/testing
class MockIPFSClient:
    """Mock IPFS client for development when IPFS is not available."""
    
    def __init__(self):
        self.storage = {}
        self.counter = 0
    
    def upload_json(self, data: Dict[str, Any]) -> str:
        """Mock upload - stores data locally and returns fake CID."""
        self.counter += 1
        cid = f"QmMockCID{self.counter:06d}"
        self.storage[cid] = data
        return cid
    
    def retrieve_json(self, cid: str) -> Optional[Dict[str, Any]]:
        """Mock retrieval - returns stored data."""
        return self.storage.get(cid)
    
    def is_connected(self) -> bool:
        """Mock connection check."""
        return True


# Example usage
if __name__ == "__main__":
    # Test with real IPFS (if available) or mock
    client = IPFSClient()
    
    if not client.is_connected():
        print("IPFS not available, using mock client")
        client = MockIPFSClient()
    
    # Test upload
    test_data = {
        "input": {"prompt": "Hello world"},
        "output": {"response": "Hello! How can I help?"},
        "timestamp": 1697654321,
        "agent_id": "test_agent"
    }
    
    cid = client.upload_json(test_data)
    print(f"Uploaded to IPFS, CID: {cid}")
    
    # Test retrieval
    if cid:
        retrieved = client.retrieve_json(cid)
        print(f"Retrieved data: {retrieved}")
        print(f"Data matches: {retrieved == test_data}")

