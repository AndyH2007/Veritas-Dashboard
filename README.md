# Blockchain Logging System - AgentVerifier

A simple Hardhat-based smart contract system for logging agent actions on the blockchain.

## 📋 Overview

The AgentVerifier contract provides a decentralized logging system that stores action data (hash, content identifier, and timestamp) for each agent on the blockchain. This ensures immutability and transparency for all recorded actions.

## 🏗️ Project Structure

```
DubHacks/
├── contracts/
│   └── AgentVerifier.sol       # Main smart contract
├── scripts/
│   └── deploy.js               # Deployment script
├── artifacts/
│   ├── contracts/
│   │   └── AgentVerifier.sol/
│   │       └── AgentVerifier.json  # Contract ABI
│   └── deployments/
│       └── AgentVerifier.json      # Deployment info (address, network, etc.)
├── hardhat.config.js           # Hardhat configuration
└── package.json                # Project dependencies
```

## 🚀 Setup Instructions

### Prerequisites

- Node.js (v14+ recommended)
- npm or yarn

### Installation

1. Dependencies are already installed. If you need to reinstall:
   ```bash
   npm install
   ```

## 📝 Contract Details

### AgentVerifier.sol

**Solidity Version:** ^0.8.20

**Key Features:**
- Stores action data for each agent (address)
- Each action contains:
  - `bytes32 hash` - Hash of the action data
  - `string cid` - Content identifier (e.g., IPFS CID)
  - `uint256 ts` - Timestamp of the action

**Main Functions:**

1. **recordAction(bytes32 _hash, string memory _cid, uint256 _ts)**
   - Records a new action for the calling agent
   - Emits `ActionRecorded` event
   - Parameters:
     - `_hash`: Hash of the action data
     - `_cid`: Content identifier (e.g., IPFS CID)
     - `_ts`: Timestamp

2. **getActionCount(address _agent) returns (uint256)**
   - Returns the number of actions recorded for a specific agent

3. **getAction(address _agent, uint256 _index) returns (bytes32, string, uint256)**
   - Retrieves a specific action by index for an agent

4. **getAllActions(address _agent) returns (ActionData[])**
   - Retrieves all actions for a specific agent

**Events:**
- `ActionRecorded(address indexed agent, bytes32 hash, string cid, uint256 ts, uint256 indexed actionIndex)`

## 🔧 Usage

### Compile Contract

```bash
npm run compile
```

### Deploy Contract

Deploy to local Hardhat network:
```bash
npm run deploy
```

Deploy to localhost (requires running node):
```bash
npm run deploy:localhost
```

### Run Local Hardhat Node

```bash
npm run node
```

### Run Tests

```bash
npm test
```

## 📦 Integration with Backend

After deployment, you'll find the following files in the `artifacts` directory:

1. **Contract ABI**: `artifacts/contracts/AgentVerifier.sol/AgentVerifier.json`
   - Contains the full contract ABI, bytecode, and metadata
   - Use this to interact with the contract from your backend

2. **Deployment Info**: `artifacts/deployments/AgentVerifier.json`
   - Contains:
     - Contract address
     - Network name
     - Deployer address
     - Deployment timestamp

### Example Integration (JavaScript/Node.js)

```javascript
const { ethers } = require("ethers");
const fs = require("fs");

// Load contract ABI and deployment info
const contractArtifact = JSON.parse(
  fs.readFileSync("artifacts/contracts/AgentVerifier.sol/AgentVerifier.json")
);
const deploymentInfo = JSON.parse(
  fs.readFileSync("artifacts/deployments/AgentVerifier.json")
);

// Connect to provider
const provider = new ethers.JsonRpcProvider("http://127.0.0.1:8545");
const signer = await provider.getSigner();

// Create contract instance
const contract = new ethers.Contract(
  deploymentInfo.address,
  contractArtifact.abi,
  signer
);

// Record an action
const hash = ethers.keccak256(ethers.toUtf8Bytes("action data"));
const cid = "QmExampleCIDString";
const timestamp = Math.floor(Date.now() / 1000);

const tx = await contract.recordAction(hash, cid, timestamp);
await tx.wait();

console.log("Action recorded!");

// Get action count
const count = await contract.getActionCount(signer.address);
console.log("Total actions:", count.toString());

// Get specific action
const action = await contract.getAction(signer.address, 0);
console.log("Action:", action);
```

## 🌐 Network Configuration

The project is configured for:

- **Local Hardhat Network** (default)
  - Chain ID: 31337
  - Auto-mining enabled
  
- **Localhost Network** (for persistent node)
  - URL: http://127.0.0.1:8545
  - Chain ID: 31337

## 📜 Latest Deployment

**Contract Address:** `0x5FbDB2315678afecb367f032d93F642f64180aa3`  
**Network:** hardhat (local)  
**Deployed:** 2025-10-18T20:17:15.932Z  
**Deployer:** 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266

## 🛠️ Development

### Available Scripts

- `npm run compile` - Compile contracts
- `npm run deploy` - Deploy to default network (hardhat)
- `npm run deploy:localhost` - Deploy to localhost network
- `npm run node` - Start local Hardhat node
- `npm run test` - Run tests

### Adding Tests

Create test files in the `test/` directory:

```javascript
const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("AgentVerifier", function () {
  it("Should record an action", async function () {
    const AgentVerifier = await ethers.getContractFactory("AgentVerifier");
    const contract = await AgentVerifier.deploy();
    await contract.waitForDeployment();

    const hash = ethers.keccak256(ethers.toUtf8Bytes("test"));
    const cid = "QmTest";
    const ts = Math.floor(Date.now() / 1000);

    await contract.recordAction(hash, cid, ts);
    const count = await contract.getActionCount(await ethers.provider.getSigner().getAddress());
    expect(count).to.equal(1);
  });
});
```

## 📄 License

ISC

## 🤝 Contributing

This is a DubHacks project. Feel free to extend and improve!

---

Built with ❤️ using Hardhat

