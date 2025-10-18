"""
FastAPI backend for On-Chain Action Provenance
Main API endpoint for logging agent actions
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict, Optional
import os
from datetime import datetime

# Import our utilities
from utils.hash import generate_action_hash
from utils.ipfs import upload_action_record, retrieve_action_record, MockIPFSClient
from utils.verify import get_contract_instance

app = FastAPI(title="AgentVerifier API", version="1.0.0")

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ActionRequest(BaseModel):
    """Request model for logging an action."""
    input_data: Any
    output_data: Any
    agent_id: str = "default"
    timestamp: Optional[int] = None


class ActionResponse(BaseModel):
    """Response model for logged action."""
    success: bool
    hash: str
    cid: str
    timestamp: int
    tx_hash: Optional[str] = None
    message: str


class ActionRecord(BaseModel):
    """Model for action record."""
    hash: str
    cid: str
    timestamp: int
    agent_id: str
    tx_hash: Optional[str] = None


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "AgentVerifier API is running", "status": "healthy"}


@app.post("/log-action", response_model=ActionResponse)
async def log_action(request: ActionRequest):
    """
    Log an agent action to blockchain and IPFS.
    
    Workflow:
    1. Generate hash from input + output + timestamp
    2. Upload full record to IPFS
    3. Record hash + CID on blockchain
    """
    try:
        # Step 1: Generate hash
        timestamp = request.timestamp or int(datetime.now().timestamp())
        action_hash = generate_action_hash(
            request.input_data, 
            request.output_data, 
            timestamp
        )
        
        # Step 2: Upload to IPFS
        cid = upload_action_record(
            request.input_data,
            request.output_data,
            timestamp,
            request.agent_id
        )
        
        if not cid:
            raise HTTPException(status_code=500, detail="Failed to upload to IPFS")
        
        # Step 3: Record on blockchain
        contract = get_contract_instance()
        tx_hash = None
        
        if contract:
            # Convert hash string to bytes32
            hash_bytes = bytes.fromhex(action_hash)
            tx_hash = contract.record_action(hash_bytes, cid, timestamp)
        
        return ActionResponse(
            success=True,
            hash=action_hash,
            cid=cid,
            timestamp=timestamp,
            tx_hash=tx_hash,
            message="Action logged successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log action: {str(e)}")


@app.get("/action/{action_hash}")
async def get_action(action_hash: str):
    """Get action record by hash."""
    try:
        # Try to get from contract first
        contract = get_contract_instance()
        if contract and contract.account:
            # This is a simplified lookup - in production you'd need to track hash->agent mapping
            # For now, we'll return the hash info
            return {
                "hash": action_hash,
                "message": "Action found (contract lookup not fully implemented)"
            }
        else:
            return {"hash": action_hash, "message": "Contract not available"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get action: {str(e)}")


@app.get("/actions")
async def get_actions():
    """Get all recent actions from blockchain events."""
    try:
        contract = get_contract_instance()
        if not contract:
            return {"actions": [], "message": "Contract not available"}
        
        # Get latest events
        events = contract.get_latest_events()
        
        actions = []
        for event in events:
            actions.append({
                "agent": event["agent"],
                "hash": event["hash"],
                "cid": event["cid"],
                "timestamp": event["timestamp"],
                "tx_hash": event["transactionHash"],
                "block_number": event["blockNumber"]
            })
        
        return {"actions": actions, "count": len(actions)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get actions: {str(e)}")


@app.get("/ipfs/{cid}")
async def get_ipfs_record(cid: str):
    """Get full action record from IPFS."""
    try:
        record = retrieve_action_record(cid)
        if record:
            return {"success": True, "record": record}
        else:
            raise HTTPException(status_code=404, detail="IPFS record not found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get IPFS record: {str(e)}")


@app.get("/health")
async def health_check():
    """Comprehensive health check."""
    status = {
        "api": "healthy",
        "contract": "unknown",
        "ipfs": "unknown"
    }
    
    # Check contract connection
    contract = get_contract_instance()
    if contract:
        status["contract"] = "connected"
    else:
        status["contract"] = "disconnected"
    
    # Check IPFS connection
    try:
        from utils.ipfs import IPFSClient
        ipfs_client = IPFSClient()
        if ipfs_client.is_connected():
            status["ipfs"] = "connected"
        else:
            status["ipfs"] = "disconnected"
    except:
        status["ipfs"] = "mock"
    
    return status


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

