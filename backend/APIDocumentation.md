# Agent Accountability Platform API Documentation

## Overview
The Agent Accountability Platform provides a comprehensive API for managing AI agents, logging their actions, evaluating performance, and maintaining accountability through blockchain integration.

**Base URL**: `http://localhost:8000`

## Authentication
Currently no authentication is required for local development. In production, implement proper API key or JWT authentication.

---

## Health & System Status

### GET `/health`
Check system health and connectivity status.

**Response:**
```json
{
  "ok": true,
  "chainConnected": true,
  "dbConnected": false,
  "timestamp": 1703123456
}
```

**Status Codes:**
- `200` - System healthy
- `500` - System error

---

## Contract Information

### GET `/debug/contract-info`
Get smart contract configuration and ABI information.

**Response:**
```json
{
  "ok": true,
  "address": "0x1234567890123456789012345678901234567890",
  "abi_functions_count": 8,
  "sample_functions": ["recordAction", "evaluateAction", "getPoints", "listAgents", "getActionCount"]
}
```

**Status Codes:**
- `200` - Contract info retrieved
- `500` - Contract configuration error

---

## IPFS Operations

### POST `/debug/ipfs-put`
Store a JSON record in IPFS and return the content identifier.

**Request Body:**
```json
{
  "record": {
    "agent": "0x1234567890123456789012345678901234567890",
    "action": "text_generation",
    "timestamp": 1703123456
  }
}
```

**Response:**
```json
{
  "ok": true,
  "cid": "QmXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXx"
}
```

### GET `/ipfs/{cid}`
Retrieve a JSON record by its content identifier.

**Path Parameters:**
- `cid` (string) - Content identifier

**Response:**
```json
{
  "agent": "0x1234567890123456789012345678901234567890",
  "action": "text_generation",
  "timestamp": 1703123456,
  "inputs": {"prompt": "Hello world"},
  "outputs": {"response": "Hello! How can I help?"}
}
```

**Status Codes:**
- `200` - Record retrieved
- `404` - CID not found
- `500` - IPFS error

---

## Hash Debugging

### POST `/debug/hash`
Compute canonical hash for debugging purposes.

**Request Body:**
```json
{
  "inputs": {"prompt": "Hello world"},
  "outputs": {"response": "Hello! How can I help?"},
  "ts": 1703123456
}
```

**Response:**
```json
{
  "ok": true,
  "canonical_json": "{\"inputs\":{\"prompt\":\"Hello world\"},\"outputs\":{\"response\":\"Hello! How can I help?\"},\"ts\":1703123456}",
  "hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
}
```

---

## Blockchain Events

### GET `/actions`
Retrieve action events from the smart contract.

**Query Parameters:**
- `from_block` (int, optional) - Start block number (default: 0)
- `to_block` (string, optional) - End block number or "latest" (default: "latest")

**Response:**
```json
[
  {
    "actor": "0x1234567890123456789012345678901234567890",
    "hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
    "cid": "QmXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXx",
    "ts": 1703123456,
    "block": 12345,
    "txHash": "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
  }
]
```

---

## Agent Management

### POST `/agents`
Register a new agent in the system.

**Request Body:**
```json
{
  "id": "0x1234567890123456789012345678901234567890",
  "name": "Financial Advisor Bot",
  "owner_org": "Demo Corp",
  "pubkey": "demo_pubkey_123",
  "stake_address": "0x1234567890123456789012345678901234567890"
}
```

**Response:**
```json
{
  "ok": true
}
```

**Status Codes:**
- `200` - Agent registered successfully
- `500` - Registration failed
- `501` - Database not configured

### GET `/agents`
Retrieve all registered agents with their current points.

**Response:**
```json
{
  "agents": [
    {
      "agent": "0x1234567890123456789012345678901234567890",
      "points": 150,
      "address": "0x1234567890123456789012345678901234567890",
      "name": "Financial Advisor Bot",
      "owner_org": "Demo Corp"
    }
  ]
}
```

---

## Agent Actions

### GET `/agents/{agent_address}/actions`
Get all actions performed by a specific agent.

**Path Parameters:**
- `agent_address` (string) - Agent's blockchain address

**Response:**
```json
{
  "agent": "0x1234567890123456789012345678901234567890",
  "points": 150,
  "actions": [
    {
      "index": 0,
      "hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
      "cid": "QmXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXx",
      "timestamp": 1703123456,
      "hash_short": "0x1234567...abcdef"
    }
  ]
}
```

### POST `/agents/{agent_address}/actions`
Log a new action for a specific agent.

**Path Parameters:**
- `agent_address` (string) - Agent's blockchain address

**Request Body:**
```json
{
  "model": "gpt-4o-mini",
  "model_hash": "sha256:abc123def456...",
  "dataset_id": "financial-data-v1",
  "dataset_hash": "sha256:def456ghi789...",
  "inputs": {
    "prompt": "What is the current market trend for tech stocks?",
    "user_id": "user123"
  },
  "outputs": {
    "analysis": "Tech stocks are showing bullish trends...",
    "confidence": 0.85
  },
  "notes": "Market analysis request"
}
```

**Response:**
```json
{
  "ok": true,
  "cid": "QmXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXx",
  "hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
  "timestamp": 1703123456,
  "txHash": "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
}
```

### POST `/agents/{agent_address}/evaluate`
Evaluate an agent's action and adjust their points.

**Path Parameters:**
- `agent_address` (string) - Agent's blockchain address

**Request Body:**
```json
{
  "index": 0,
  "good": true,
  "delta": 1,
  "reason": "Correct analysis provided"
}
```

**Response:**
```json
{
  "ok": true,
  "points": 151,
  "txHash": "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
}
```

---

## Agent Types & Configuration

### GET `/agent-types`
Get available agent types and their configurations.

**Response:**
```json
{
  "types": [
    {
      "id": "general",
      "name": "General Purpose",
      "description": "Versatile agent",
      "capabilities": ["text_generation", "question_answering", "summarization"],
      "default_threshold": 0.8,
      "icon": "fas fa-robot"
    },
    {
      "id": "financial",
      "name": "Financial Advisor",
      "description": "Finance-focused",
      "capabilities": ["market_analysis", "risk_assessment", "investment_advice"],
      "default_threshold": 0.9,
      "icon": "fas fa-chart-line"
    },
    {
      "id": "medical",
      "name": "Medical Assistant",
      "description": "Healthcare domain",
      "capabilities": ["symptom_analysis", "drug_interactions", "medical_guidance"],
      "default_threshold": 0.95,
      "icon": "fas fa-user-md"
    },
    {
      "id": "legal",
      "name": "Legal Advisor",
      "description": "Legal analysis",
      "capabilities": ["contract_review", "legal_research", "compliance_check"],
      "default_threshold": 0.9,
      "icon": "fas fa-gavel"
    },
    {
      "id": "technical",
      "name": "Technical Support",
      "description": "Support & debugging",
      "capabilities": ["debugging", "code_review", "system_diagnostics"],
      "default_threshold": 0.85,
      "icon": "fas fa-code"
    }
  ]
}
```

---

## Analytics & Leaderboard

### GET `/agents/{agent_address}/analytics`
Get analytics data for a specific agent.

**Path Parameters:**
- `agent_address` (string) - Agent's blockchain address

**Response:**
```json
{
  "agent": "0x1234567890123456789012345678901234567890",
  "metrics": {
    "total_points": 150,
    "total_actions": 25,
    "success_rate": 0.75,
    "performance_trend": "up"
  },
  "performance_data": [
    {
      "date": 1703037056,
      "points": 140,
      "actions": 23
    },
    {
      "date": 1703123456,
      "points": 150,
      "actions": 25
    }
  ],
  "recent_evaluations": []
}
```

### GET `/leaderboard`
Get agent leaderboard sorted by points.

**Response:**
```json
{
  "leaderboard": [
    {
      "agent": "0x1234567890123456789012345678901234567890",
      "points": 150,
      "action_count": 25,
      "rank": 1
    },
    {
      "agent": "0x2345678901234567890123456789012345678901",
      "points": 120,
      "action_count": 18,
      "rank": 2
    }
  ],
  "total_agents": 2
}
```

---

## Logging

### POST `/agents/{agent_address}/logs`
Add a log entry for an agent.

**Path Parameters:**
- `agent_address` (string) - Agent's blockchain address

**Request Body:**
```json
{
  "level": "info",
  "message": "Agent completed action successfully"
}
```

**Response:**
```json
{
  "ok": true,
  "log_id": "0x1234567890123456789012345678901234567890_1703123456",
  "timestamp": 1703123456,
  "level": "info",
  "message": "Agent completed action successfully"
}
```

### GET `/agents/{agent_address}/logs`
Get logs for a specific agent.

**Path Parameters:**
- `agent_address` (string) - Agent's blockchain address

**Query Parameters:**
- `limit` (int, optional) - Maximum number of logs to return (default: 50)

**Response:**
```json
{
  "agent": "0x1234567890123456789012345678901234567890",
  "logs": [
    {
      "timestamp": 1703123456,
      "level": "info",
      "message": "Mock log message 1 for agent 0x1234567890123456789012345678901234567890"
    },
    {
      "timestamp": 1703119856,
      "level": "warning",
      "message": "Mock log message 2 for agent 0x1234567890123456789012345678901234567890"
    }
  ],
  "total": 2
}
```

---

## Run Attestations (Database Required)

### POST `/runs`
Ingest a run attestation (requires database configuration).

**Request Body:**
```json
{
  "agent_id": "0x1234567890123456789012345678901234567890",
  "run_id": "run_12345",
  "started_at": 1703123400.0,
  "finished_at": 1703123456.0,
  "model_name": "gpt-4o-mini",
  "model_version": "2024-01-01",
  "container_digest": "sha256:abc123...",
  "params": {"temperature": 0.7, "max_tokens": 1000},
  "input_hash": "sha256:def456...",
  "output_hash": "sha256:ghi789...",
  "claims": {"accuracy": 0.95},
  "trace_hash": "sha256:jkl012...",
  "signature": "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
}
```

**Response:**
```json
{
  "ok": true,
  "run_id": "run_12345",
  "leaf": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
}
```

**Status Codes:**
- `200` - Run ingested successfully
- `400` - Invalid signature
- `404` - Unknown agent
- `501` - Database not configured

### GET `/agents/{agent_id}/runs`
Get runs for a specific agent (requires database configuration).

**Path Parameters:**
- `agent_id` (string) - Agent's blockchain address

**Response:**
```json
[
  {
    "id": "run_12345",
    "agent_id": "0x1234567890123456789012345678901234567890",
    "started_at": "2023-12-21T10:30:00Z",
    "finished_at": "2023-12-21T10:30:56Z",
    "model_name": "gpt-4o-mini",
    "model_version": "2024-01-01",
    "status": "completed",
    "policy_summary": {"violations": 0, "warnings": 1}
  }
]
```

---

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "detail": "Invalid input data"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

### 501 Not Implemented
```json
{
  "detail": "Database not configured"
}
```

---

## Rate Limiting
Currently no rate limiting is implemented. In production, implement appropriate rate limiting based on your requirements.

---

## CORS
CORS is enabled for all origins (`*`) in development. In production, restrict to specific domains.

---

## WebSocket Support
WebSocket support is not currently implemented but can be added for real-time updates.

---

## Examples

### Complete Agent Workflow

1. **Register Agent:**
```bash
curl -X POST http://localhost:8000/agents \
  -H "Content-Type: application/json" \
  -d '{"id":"0x1234567890123456789012345678901234567890","name":"Test Agent","owner_org":"Test Org","pubkey":"test_pubkey","stake_address":"0x1234567890123456789012345678901234567890"}'
```

2. **Log Action:**
```bash
curl -X POST http://localhost:8000/agents/0x1234567890123456789012345678901234567890/actions \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","inputs":{"prompt":"Hello"},"outputs":{"response":"Hi there!"}}'
```

3. **Evaluate Action:**
```bash
curl -X POST http://localhost:8000/agents/0x1234567890123456789012345678901234567890/evaluate \
  -H "Content-Type: application/json" \
  -d '{"index":0,"good":true,"delta":1,"reason":"Good response"}'
```

4. **Check Agent Status:**
```bash
curl http://localhost:8000/agents/0x1234567890123456789012345678901234567890/actions
```
