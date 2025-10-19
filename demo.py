#!/usr/bin/env python3
"""
Demo script for Agent Accountability Platform
This script demonstrates the key features of the platform.
"""

import requests
import json
import time
import random

API_BASE = "http://localhost:8000"

def create_demo_agents():
    """Create some demo agents for testing."""
    agents = [
        {
            "id": "0x1234567890123456789012345678901234567890",
            "name": "Financial Advisor Bot",
            "owner_org": "Demo Corp",
            "pubkey": "demo_pubkey_1",
            "stake_address": "0x1234567890123456789012345678901234567890"
        },
        {
            "id": "0x2345678901234567890123456789012345678901",
            "name": "Medical Assistant",
            "owner_org": "HealthTech Inc",
            "pubkey": "demo_pubkey_2",
            "stake_address": "0x2345678901234567890123456789012345678901"
        },
        {
            "id": "0x3456789012345678901234567890123456789012",
            "name": "Legal Advisor",
            "owner_org": "LawFirm LLC",
            "pubkey": "demo_pubkey_3",
            "stake_address": "0x3456789012345678901234567890123456789012"
        }
    ]
    
    print("Creating demo agents...")
    for agent in agents:
        try:
            response = requests.post(f"{API_BASE}/agents", json=agent)
            if response.status_code == 200:
                print(f"✓ Created agent: {agent['name']}")
            else:
                print(f"✗ Failed to create agent: {agent['name']}")
        except Exception as e:
            print(f"✗ Error creating agent {agent['name']}: {e}")

def log_demo_actions():
    """Log some demo actions for the agents."""
    actions = [
        {
            "agent": "0x1234567890123456789012345678901234567890",
            "model": "gpt-4o-mini",
            "model_hash": "sha256:abc123...",
            "dataset_id": "financial-data-v1",
            "dataset_hash": "sha256:def456...",
            "inputs": {"query": "What is the current market trend for tech stocks?", "user_id": "user123"},
            "outputs": {"analysis": "Tech stocks are showing bullish trends...", "confidence": 0.85},
            "notes": "Market analysis request"
        },
        {
            "agent": "0x2345678901234567890123456789012345678901",
            "model": "gpt-4o-mini",
            "model_hash": "sha256:ghi789...",
            "dataset_id": "medical-data-v1",
            "dataset_hash": "sha256:jkl012...",
            "inputs": {"symptoms": ["headache", "fever"], "age": 35, "gender": "female"},
            "outputs": {"diagnosis": "Possible viral infection", "recommendation": "Rest and hydration", "confidence": 0.78},
            "notes": "Symptom analysis"
        },
        {
            "agent": "0x3456789012345678901234567890123456789012",
            "model": "gpt-4o-mini",
            "model_hash": "sha256:mno345...",
            "dataset_id": "legal-data-v1",
            "dataset_hash": "sha256:pqr678...",
            "inputs": {"contract_text": "This agreement is between...", "question": "Are there any liability issues?"},
            "outputs": {"analysis": "No major liability concerns found", "risk_level": "low", "confidence": 0.92},
            "notes": "Contract review"
        }
    ]
    
    print("\nLogging demo actions...")
    for action in actions:
        try:
            response = requests.post(f"{API_BASE}/agents/{action['agent']}/actions", json=action)
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Logged action for {action['agent'][:8]}... CID: {data['cid'][:16]}...")
            else:
                print(f"✗ Failed to log action for {action['agent'][:8]}...")
        except Exception as e:
            print(f"✗ Error logging action: {e}")

def evaluate_actions():
    """Evaluate some actions to demonstrate the token system."""
    agents = [
        "0x1234567890123456789012345678901234567890",
        "0x2345678901234567890123456789012345678901",
        "0x3456789012345678901234567890123456789012"
    ]
    
    print("\nEvaluating actions...")
    for agent in agents:
        try:
            # Get agent actions
            response = requests.get(f"{API_BASE}/agents/{agent}/actions")
            if response.status_code == 200:
                data = response.json()
                actions = data.get('actions', [])
                
                if actions:
                    # Randomly evaluate some actions
                    for i, action in enumerate(actions[:3]):  # Evaluate first 3 actions
                        is_good = random.choice([True, False])
                        evaluation = {
                            "index": i,
                            "good": is_good,
                            "delta": 1,
                            "reason": "Good analysis" if is_good else "Incorrect information"
                        }
                        
                        eval_response = requests.post(f"{API_BASE}/agents/{agent}/evaluate", json=evaluation)
                        if eval_response.status_code == 200:
                            result = eval_response.json()
                            print(f"✓ Evaluated action {i} for {agent[:8]}... as {'good' if is_good else 'bad'}. New balance: {result['points']}")
                        else:
                            print(f"✗ Failed to evaluate action {i} for {agent[:8]}...")
                        
                        time.sleep(0.5)  # Small delay between evaluations
                else:
                    print(f"No actions found for agent {agent[:8]}...")
        except Exception as e:
            print(f"✗ Error evaluating actions for {agent[:8]}...: {e}")

def show_analytics():
    """Show analytics and leaderboard."""
    print("\nFetching analytics...")
    
    try:
        # Get leaderboard
        response = requests.get(f"{API_BASE}/leaderboard")
        if response.status_code == 200:
            data = response.json()
            print("\n🏆 LEADERBOARD:")
            print("-" * 50)
            for agent in data['leaderboard']:
                print(f"#{agent['rank']:2d} {agent['agent'][:8]}... | {agent['points']:3d} tokens | {agent['action_count']:2d} actions")
        else:
            print("✗ Failed to fetch leaderboard")
    except Exception as e:
        print(f"✗ Error fetching leaderboard: {e}")
    
    try:
        # Get agent types
        response = requests.get(f"{API_BASE}/agent-types")
        if response.status_code == 200:
            data = response.json()
            print("\n🤖 AVAILABLE AGENT TYPES:")
            print("-" * 50)
            for agent_type in data['types']:
                print(f"• {agent_type['name']}: {agent_type['description']}")
        else:
            print("✗ Failed to fetch agent types")
    except Exception as e:
        print(f"✗ Error fetching agent types: {e}")

def check_system_health():
    """Check system health."""
    print("Checking system health...")
    
    try:
        response = requests.get(f"{API_BASE}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ System Status: {'Healthy' if data['ok'] else 'Unhealthy'}")
            print(f"✓ Blockchain: {'Connected' if data.get('chainConnected') else 'Disconnected'}")
            print(f"✓ Database: {'Connected' if data.get('dbConnected') else 'Disconnected'}")
        else:
            print("✗ System health check failed")
    except Exception as e:
        print(f"✗ Error checking system health: {e}")

def main():
    """Run the demo."""
    print("🚀 Agent Accountability Platform Demo")
    print("=" * 50)
    
    # Check if API is running
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code != 200:
            print("❌ API is not running. Please start the backend server first.")
            return
    except:
        print("❌ Cannot connect to API. Please start the backend server first.")
        return
    
    # Run demo steps
    check_system_health()
    create_demo_agents()
    log_demo_actions()
    evaluate_actions()
    show_analytics()
    
    print("\n✅ Demo completed!")
    print("\n🌐 Open http://localhost:8080 to view the frontend")
    print("📊 The platform now has:")
    print("   • Multiple agent types with different capabilities")
    print("   • Token-based reward/penalty system")
    print("   • Real-time analytics and leaderboard")
    print("   • Modern, responsive UI")
    print("   • Comprehensive logging and monitoring")

if __name__ == "__main__":
    main()
