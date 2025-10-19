# Agent Accountability Platform

A comprehensive platform for managing, monitoring, and evaluating AI agents with blockchain-based accountability and token rewards.

## 🚀 Features

### ✨ Modern Frontend
- **Beautiful UI/UX**: Modern dark theme with smooth animations and responsive design
- **Real-time Updates**: Live agent monitoring with WebSocket support
- **Interactive Dashboard**: Comprehensive analytics and performance metrics
- **Mobile Responsive**: Works seamlessly on all device sizes

### 🤖 Multi-Agent System
- **Agent Types**: Support for different agent specializations:
  - General Purpose
  - Financial Advisor
  - Medical Assistant
  - Legal Advisor
  - Technical Support
- **Agent Management**: Create, configure, and monitor multiple agents
- **Agent Discovery**: Easy agent selection and switching

### 🪙 Token System
- **Smart Contract Integration**: Blockchain-based token rewards and penalties
- **Real-time Evaluation**: Instant feedback on agent actions
- **Token Balance Tracking**: Live updates of agent token balances
- **Performance Incentives**: Reward good behavior, penalize bad actions

### 📊 Analytics & Monitoring
- **Performance Metrics**: Success rates, action counts, and trends
- **Leaderboard**: Rank agents by performance and token balance
- **Action Timeline**: Complete history of agent activities
- **Real-time Logs**: Comprehensive logging with filtering

### 🔒 Accountability Features
- **Action Logging**: Record all agent inputs and outputs
- **IPFS Storage**: Decentralized storage for action records
- **Hash Verification**: Cryptographic verification of actions
- **Audit Trail**: Complete traceability of agent decisions

## 🏗️ Architecture

### Backend (FastAPI)
- **RESTful API**: Comprehensive endpoints for all operations
- **Database Integration**: PostgreSQL for persistent storage
- **Blockchain Integration**: Web3.py for smart contract interaction
- **IPFS Integration**: Decentralized file storage

### Frontend (Vanilla JS)
- **Modern CSS**: Custom design system with CSS variables
- **Component-based**: Modular JavaScript architecture
- **Real-time Updates**: Live data synchronization
- **Progressive Enhancement**: Works without JavaScript

### Smart Contract (Solidity)
- **Agent Registry**: Track registered agents
- **Action Recording**: Store action hashes and metadata
- **Token Management**: Points-based reward system
- **Event Logging**: Comprehensive event emission

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- PostgreSQL
- Ethereum node (local or remote)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd agent-accountability-platform
   ```

2. **Install backend dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Install frontend dependencies**
   ```bash
   npm install
   ```

4. **Set up environment variables**
   ```bash
   cp backend/.env.example backend/.env
   # Edit backend/.env with your configuration
   ```

5. **Set up database**
   ```bash
   createdb agent_accountability
   psql agent_accountability < backend/db.sql
   ```

6. **Deploy smart contract**
   ```bash
   npx hardhat compile
   npx hardhat run scripts/deploy.js --network localhost
   ```

7. **Start the application**
   ```bash
   # Terminal 1: Start backend
   cd backend
   python main.py

   # Terminal 2: Start frontend
   cd frontend
   python -m http.server 8080
   ```

8. **Access the application**
   Open http://localhost:8080 in your browser

## 📖 Usage Guide

### Creating Agents
1. Click "Add Agent" in the sidebar
2. Fill in agent details (name, type, description)
3. Agent is automatically registered on the blockchain

### Logging Actions
1. Select an agent from the sidebar
2. Fill in the action form with:
   - Model information
   - Dataset details
   - Input/output JSON
   - Additional notes
3. Click "Log Action" to record the action

### Evaluating Actions
1. View the action timeline
2. Click "Good" or "Bad" for each action
3. Tokens are automatically adjusted via smart contract
4. View updated balances in real-time

### Monitoring Performance
1. Switch to the "Analytics" tab
2. View performance metrics and charts
3. Check the leaderboard for rankings
4. Monitor success rates and trends

## 🔧 API Endpoints

### Agent Management
- `GET /agents` - List all agents
- `POST /agents` - Register new agent
- `GET /agents/{address}/actions` - Get agent actions
- `POST /agents/{address}/actions` - Log agent action
- `POST /agents/{address}/evaluate` - Evaluate agent action

### Analytics
- `GET /agents/{address}/analytics` - Get agent analytics
- `GET /leaderboard` - Get agent leaderboard
- `GET /agent-types` - Get available agent types

### System
- `GET /health` - System health check
- `GET /ipfs/{cid}` - Retrieve IPFS content
- `POST /log-action` - Log action (legacy)

## 🎨 Customization

### Adding New Agent Types
1. Update `backend/main.py` - `get_agent_types()` endpoint
2. Add type configuration with capabilities and thresholds
3. Update frontend to handle new types

### Styling
- Modify `frontend/styles.css` for visual changes
- CSS variables in `:root` for easy theme customization
- Responsive breakpoints for different screen sizes

### Smart Contract
- Extend `contracts/AgentVerifier.sol` for new features
- Add new events and functions as needed
- Update ABI and redeploy

## 🔒 Security Considerations

- **Input Validation**: All inputs are validated and sanitized
- **Access Control**: Smart contract functions are protected
- **Data Integrity**: Cryptographic hashing ensures data integrity
- **Audit Trail**: Complete logging of all operations

## 🚀 Deployment

### Production Setup
1. Use a production database (PostgreSQL)
2. Deploy smart contract to mainnet/testnet
3. Use production IPFS node
4. Configure proper CORS settings
5. Set up monitoring and logging

### Docker Deployment
```bash
docker-compose up -d
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with FastAPI, Web3.py, and modern web technologies
- Smart contract based on OpenZeppelin standards
- UI inspired by modern design systems

## 📞 Support

For questions and support, please open an issue on GitHub or contact the development team.

---

**Note**: This is a demonstration platform. For production use, ensure proper security audits and testing.