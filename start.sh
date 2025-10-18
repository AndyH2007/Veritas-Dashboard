#!/bin/bash

# AgentVerifier Quick Start Script
# For 24-hour hackathon demo

echo "🚀 Starting AgentVerifier On-Chain Action Provenance System"
echo "=========================================================="

# Check if we're in the right directory
if [ ! -f "hardhat.config.js" ]; then
    echo "❌ Please run this script from the DubHacks directory"
    exit 1
fi

echo "📋 Step 1: Starting Hardhat local network..."
npx hardhat node &
HARDHAT_PID=$!
sleep 5

echo "📋 Step 2: Deploying AgentVerifier contract..."
npx hardhat run scripts/deploy.js --network localhost
sleep 2

echo "📋 Step 3: Installing Python dependencies..."
cd backend
pip3 install -r requirements.txt
cd ..

echo "📋 Step 4: Starting FastAPI backend..."
cd backend
python3 main.py &
BACKEND_PID=$!
sleep 3

echo "📋 Step 5: Opening frontend dashboard..."
cd ../frontend
python3 -m http.server 8080 &
FRONTEND_PID=$!

echo ""
echo "✅ AgentVerifier is now running!"
echo "=================================="
echo "🌐 Frontend Dashboard: http://localhost:8080"
echo "🔗 Backend API: http://localhost:8000"
echo "⛓️  Hardhat Network: http://localhost:8545"
echo ""
echo "📖 API Endpoints:"
echo "  POST /log-action - Log new agent action"
echo "  GET  /actions - Get all actions"
echo "  GET  /ipfs/{cid} - Get IPFS record"
echo "  GET  /health - Health check"
echo ""
echo "🎯 Demo Workflow:"
echo "  1. Open http://localhost:8080"
echo "  2. Fill in input/output data"
echo "  3. Click 'Log Action'"
echo "  4. View action in the list"
echo "  5. Click 'View Full Record' to see IPFS data"
echo ""
echo "🛑 To stop all services:"
echo "  kill $HARDHAT_PID $BACKEND_PID $FRONTEND_PID"
echo ""
echo "Press Ctrl+C to stop this script and all services"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping all services..."
    kill $HARDHAT_PID $BACKEND_PID $FRONTEND_PID 2>/dev/null
    echo "✅ All services stopped"
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Wait for user to stop
wait

