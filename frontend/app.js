// Agent Accountability Platform - Main Application
class AgentAccountabilityApp {
    constructor() {
        this.API_BASE = "http://localhost:8000";
        this.currentAgent = null;
        this.agents = [];
        this.logs = [];
        this.evaluations = [];
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadInitialData();
        this.setupWebSocket();
    }

    bindEvents() {
        // Tab switching
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        // Agent management
        document.getElementById('refreshAgents').addEventListener('click', () => this.loadAgents());
        document.getElementById('addAgentBtn').addEventListener('click', () => this.showAddAgentModal());
        document.getElementById('createAgent').addEventListener('click', () => this.createAgent());

        // Action logging
        document.getElementById('logActionBtn').addEventListener('click', () => this.logAction());
        document.getElementById('refreshActions').addEventListener('click', () => this.loadActions());

        // Logs
        document.getElementById('clearLogs').addEventListener('click', () => this.clearLogs());
        document.getElementById('logLevel').addEventListener('change', (e) => this.filterLogs(e.target.value));

        // Settings
        document.getElementById('saveSettings').addEventListener('click', () => this.saveSettings());

        // Modals
        document.getElementById('closeModal').addEventListener('click', () => this.hideModal());
        document.getElementById('closeAddAgentModal').addEventListener('click', () => this.hideAddAgentModal());

        // Demo data creation
        document.getElementById('createDemoData').addEventListener('click', () => this.createDemoData());

        // Auto-refresh
        setInterval(() => this.loadAgents(), 30000); // Refresh every 30 seconds
        setInterval(() => this.loadSystemHealth(), 10000); // Health check every 10 seconds
    }

    async loadInitialData() {
        await Promise.all([
            this.loadSystemHealth(),
            this.loadAgents()
        ]);
    }

    async loadSystemHealth() {
        try {
            const response = await fetch(`${this.API_BASE}/health`);
            const data = await response.json();
            
            const healthElement = document.getElementById('systemHealth');
            if (data.ok) {
                healthElement.textContent = 'Healthy';
                healthElement.className = 'stat-value health';
                
                // Update additional health info if available
                if (data.chainConnected !== undefined) {
                    console.log('Blockchain:', data.chainConnected ? 'Connected' : 'Disconnected');
                }
                if (data.dbConnected !== undefined) {
                    console.log('Database:', data.dbConnected ? 'Connected' : 'Disconnected');
                }
            } else {
                healthElement.textContent = 'Unhealthy';
                healthElement.className = 'stat-value error';
            }
        } catch (error) {
            console.error('Health check failed:', error);
            document.getElementById('systemHealth').textContent = 'Offline';
            document.getElementById('systemHealth').className = 'stat-value error';
            this.showNotification('Backend connection failed. Please ensure the API server is running.', 'error');
        }
    }

    async loadAgents() {
        try {
            const response = await fetch(`${this.API_BASE}/agents`);
            const data = await response.json();
            
            this.agents = data.agents || [];
            
            // Load agent types for additional metadata
            try {
                const typesResponse = await fetch(`${this.API_BASE}/agent-types`);
                const typesData = await typesResponse.json();
                this.agentTypes = typesData.types;
                
                // Enhance agents with type information
                this.agents.forEach(agent => {
                    const agentType = this.agentTypes.find(type => type.id === agent.type) || this.agentTypes[0];
                    agent.typeName = agentType.name;
                    agent.icon = agentType.icon;
                    agent.description = agentType.description;
                });
            } catch (typesError) {
                console.warn('Failed to load agent types:', typesError);
                // Use default agent types
                this.agentTypes = [
                    { id: 'general', name: 'General Purpose', icon: 'fas fa-robot' },
                    { id: 'financial', name: 'Financial Advisor', icon: 'fas fa-chart-line' },
                    { id: 'medical', name: 'Medical Assistant', icon: 'fas fa-user-md' },
                    { id: 'legal', name: 'Legal Advisor', icon: 'fas fa-gavel' },
                    { id: 'technical', name: 'Technical Support', icon: 'fas fa-code' }
                ];
                
                this.agents.forEach(agent => {
                    agent.typeName = 'General Purpose';
                    agent.icon = 'fas fa-robot';
                    agent.description = 'AI Agent';
                });
            }
            
            this.renderAgents();
            this.updateStats();
            
            // Auto-select first agent if none selected
            if (!this.currentAgent && this.agents.length > 0) {
                this.selectAgent(this.agents[0].agent);
            }
            
            // If no agents exist, show a helpful message
            if (this.agents.length === 0) {
                this.showNotification('No agents found. Click "Add Agent" to create your first agent.', 'info');
            }
        } catch (error) {
            console.error('Failed to load agents:', error);
            this.showNotification('Failed to load agents. Please check if the backend is running.', 'error');
        }
    }

    renderAgents() {
        const agentList = document.getElementById('agentList');
        agentList.innerHTML = '';

        if (this.agents.length === 0) {
            agentList.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-robot"></i>
                    <h3>No Agents Found</h3>
                    <p>Create your first agent to get started with the platform.</p>
                    <button class="btn btn-primary" onclick="document.getElementById('addAgentBtn').click()">
                        <i class="fas fa-plus"></i>
                        Add Agent
                    </button>
                </div>
            `;
            return;
        }

        this.agents.forEach(agent => {
            const agentElement = document.createElement('div');
            agentElement.className = `agent-item ${this.currentAgent === agent.agent ? 'active' : ''}`;
            agentElement.innerHTML = `
                <div class="agent-status ${agent.points > 0 ? '' : 'inactive'}"></div>
                <div class="agent-name">
                    <i class="${agent.icon || 'fas fa-robot'}"></i>
                    ${agent.name || 'Unnamed Agent'}
                </div>
                <div class="agent-type">${agent.typeName || 'General Purpose'}</div>
                <div class="agent-tokens">${agent.points || 0} tokens</div>
            `;
            
            agentElement.addEventListener('click', () => this.selectAgent(agent.agent));
            agentList.appendChild(agentElement);
        });
    }

    async selectAgent(agentAddress) {
        this.currentAgent = agentAddress;
        this.renderAgents(); // Update active state
        
        // Show agent details
        const agent = this.agents.find(a => a.agent === agentAddress);
        if (agent) {
            this.showAgentDetails(agent);
            await this.loadActions();
        }
    }

    showAgentDetails(agent) {
        document.getElementById('agentHeader').style.display = 'block';
        document.getElementById('tabsContainer').style.display = 'flex';
        
        document.getElementById('agentName').textContent = agent.name || 'Unnamed Agent';
        document.getElementById('agentAddress').textContent = agent.agent;
        document.getElementById('agentTokens').textContent = agent.points || 0;
        document.getElementById('agentActions').textContent = agent.actions?.length || 0;
        
        // Calculate performance (placeholder)
        const performance = agent.points > 0 ? Math.min(100, Math.max(0, (agent.points / 100) * 100)) : 0;
        document.getElementById('agentPerformance').textContent = `${Math.round(performance)}%`;
    }

    async loadActions() {
        if (!this.currentAgent) return;

        try {
            const response = await fetch(`${this.API_BASE}/agents/${this.currentAgent}/actions`);
            const data = await response.json();
            
            this.renderActions(data.actions || []);
            this.updateAgentStats(data);
        } catch (error) {
            console.error('Failed to load actions:', error);
            this.showNotification('Failed to load actions', 'error');
        }
    }

    renderActions(actions) {
        const tbody = document.getElementById('actionsTableBody');
        tbody.innerHTML = '';

        actions.forEach((action, index) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${this.formatTimestamp(action.timestamp)}</td>
                <td>${action.model || 'Unknown'}</td>
                <td class="mono">${action.hash_short || action.hash?.substring(0, 16) + '...'}</td>
                <td>
                    <span class="status-indicator success"></span>
                    <span>Pending</span>
                </td>
                <td class="action-buttons">
                    <button class="btn btn-sm btn-success" onclick="app.evaluateAction(${index}, true)">
                        <i class="fas fa-thumbs-up"></i>
                        Good
                    </button>
                    <button class="btn btn-sm btn-error" onclick="app.evaluateAction(${index}, false)">
                        <i class="fas fa-thumbs-down"></i>
                        Bad
                    </button>
                    <button class="btn btn-sm btn-outline" onclick="app.viewActionDetails('${action.cid}')">
                        <i class="fas fa-eye"></i>
                        View
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    async evaluateAction(index, isGood) {
        if (!this.currentAgent) return;

        try {
            const response = await fetch(`${this.API_BASE}/agents/${this.currentAgent}/evaluate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    index: index,
                    good: isGood,
                    delta: 1,
                    reason: isGood ? 'Correct behavior' : 'Incorrect behavior'
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.showNotification(
                    `Action ${isGood ? 'rewarded' : 'penalized'}! New balance: ${data.points} tokens`,
                    isGood ? 'success' : 'warning'
                );
                
                // Update UI
                document.getElementById('agentTokens').textContent = data.points;
                
                // Reload actions to update status
                await this.loadActions();
                await this.loadAgents();
                
                // Add to evaluations
                this.evaluations.unshift({
                    timestamp: Date.now(),
                    result: isGood ? 'good' : 'bad',
                    points: data.points,
                    reason: isGood ? 'Correct behavior' : 'Incorrect behavior'
                });
                this.renderEvaluations();
            } else {
                this.showNotification('Failed to evaluate action', 'error');
            }
        } catch (error) {
            console.error('Failed to evaluate action:', error);
            this.showNotification('Failed to evaluate action', 'error');
        }
    }

    async viewActionDetails(cid) {
        try {
            const response = await fetch(`${this.API_BASE}/ipfs/${cid}`);
            const data = await response.json();
            
            document.getElementById('actionDetails').textContent = JSON.stringify(data, null, 2);
            document.getElementById('actionModal').classList.add('active');
        } catch (error) {
            console.error('Failed to load action details:', error);
            this.showNotification('Failed to load action details', 'error');
        }
    }

    async logAction() {
        if (!this.currentAgent) {
            this.showNotification('Please select an agent first', 'warning');
            return;
        }

        const inputs = this.parseJSON(document.getElementById('inputs').value);
        const outputs = this.parseJSON(document.getElementById('outputs').value);

        if (!inputs || !outputs) {
            this.showNotification('Please provide valid JSON for inputs and outputs', 'error');
            return;
        }

        // Show loading state
        const logButton = document.getElementById('logActionBtn');
        const originalText = logButton.innerHTML;
        logButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Logging...';
        logButton.disabled = true;

        try {
            const response = await fetch(`${this.API_BASE}/agents/${this.currentAgent}/actions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    model: document.getElementById('model').value,
                    model_hash: document.getElementById('modelHash').value,
                    dataset_id: document.getElementById('dataset').value,
                    dataset_hash: document.getElementById('datasetHash').value,
                    inputs: inputs,
                    outputs: outputs,
                    notes: document.getElementById('notes').value
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.showNotification('Action logged successfully!', 'success');
                
                // Clear form
                this.clearActionForm();
                
                // Reload actions
                await this.loadActions();
                
                // Add to logs
                this.addLog('info', `Action logged: ${data.cid}`);
            } else {
                const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
                this.showNotification(`Failed to log action: ${errorData.detail}`, 'error');
            }
        } catch (error) {
            console.error('Failed to log action:', error);
            this.showNotification('Failed to log action. Please check backend connection.', 'error');
        } finally {
            // Restore button state
            logButton.innerHTML = originalText;
            logButton.disabled = false;
        }
    }

    clearActionForm() {
        document.getElementById('model').value = '';
        document.getElementById('modelHash').value = '';
        document.getElementById('dataset').value = '';
        document.getElementById('datasetHash').value = '';
        document.getElementById('inputs').value = '';
        document.getElementById('outputs').value = '';
        document.getElementById('notes').value = '';
    }

    async createAgent() {
        const name = document.getElementById('newAgentName').value;
        const type = document.getElementById('newAgentType').value;
        const description = document.getElementById('newAgentDescription').value;

        if (!name) {
            this.showNotification('Please enter an agent name', 'warning');
    return;
  }

        try {
            // Generate a mock address for demo purposes
            const mockAddress = '0x' + Math.random().toString(16).substr(2, 40);
            
            const response = await fetch(`${this.API_BASE}/agents`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    id: mockAddress,
                    name: name,
                    owner_org: 'Demo Organization',
                    pubkey: 'mock_pubkey_' + Date.now(),
                    stake_address: mockAddress
                })
            });

            if (response.ok) {
                this.showNotification('Agent created successfully!', 'success');
                this.hideAddAgentModal();
                this.clearAddAgentForm();
                await this.loadAgents();
                this.addLog('info', `New agent created: ${name}`);
            } else {
                this.showNotification('Failed to create agent', 'error');
            }
        } catch (error) {
            console.error('Failed to create agent:', error);
            this.showNotification('Failed to create agent', 'error');
        }
    }

    clearAddAgentForm() {
        document.getElementById('newAgentName').value = '';
        document.getElementById('newAgentType').value = 'general';
        document.getElementById('newAgentDescription').value = '';
    }

    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update tab panels
        document.querySelectorAll('.tab-panel').forEach(panel => {
            panel.classList.remove('active');
        });
        document.getElementById(`${tabName}Tab`).classList.add('active');

        // Load tab-specific data
        switch (tabName) {
            case 'logs':
                this.renderLogs();
                break;
            case 'analytics':
                this.renderAnalytics();
                break;
            case 'settings':
                this.loadSettings();
                break;
        }
    }

    renderLogs() {
        const logsContent = document.getElementById('logsContent');
        logsContent.innerHTML = '';

        this.logs.forEach(log => {
            const logElement = document.createElement('div');
            logElement.className = `log-entry ${log.level}`;
            logElement.innerHTML = `
                <span class="log-timestamp">${this.formatTimestamp(log.timestamp / 1000)}</span>
                <span class="log-level ${log.level}">${log.level.toUpperCase()}</span>
                <span class="log-message">${log.message}</span>
            `;
            logsContent.appendChild(logElement);
        });
    }

    async renderAnalytics() {
        if (!this.currentAgent) return;

        try {
            // Load analytics data
            const response = await fetch(`${this.API_BASE}/agents/${this.currentAgent}/analytics`);
            const data = await response.json();
            
            // Update success rate
            const successRate = Math.round(data.metrics.success_rate * 100);
            document.getElementById('successRate').textContent = `${successRate}%`;

            // Render performance chart (placeholder)
            this.renderPerformanceChart(data.performance_data);
            
            // Render evaluations
            this.renderEvaluations();
            
            // Load leaderboard
            await this.loadLeaderboard();
        } catch (error) {
            console.error('Failed to load analytics:', error);
            this.showNotification('Failed to load analytics', 'error');
        }
    }

    async loadLeaderboard() {
        try {
            const response = await fetch(`${this.API_BASE}/leaderboard`);
            const data = await response.json();
            
            // Add leaderboard to analytics tab
            const leaderboardContainer = document.querySelector('#analyticsTab .analytics-grid');
            if (!document.getElementById('leaderboardCard')) {
                const leaderboardCard = document.createElement('div');
                leaderboardCard.className = 'chart-card';
                leaderboardCard.id = 'leaderboardCard';
                leaderboardCard.innerHTML = `
                    <h3>Top Agents</h3>
                    <div class="leaderboard-list" id="leaderboardList">
                        <!-- Leaderboard will be populated here -->
                    </div>
                `;
                leaderboardContainer.appendChild(leaderboardCard);
            }
            
            this.renderLeaderboard(data.leaderboard);
        } catch (error) {
            console.error('Failed to load leaderboard:', error);
        }
    }

    renderLeaderboard(leaderboard) {
        const leaderboardList = document.getElementById('leaderboardList');
        if (!leaderboardList) return;
        
        leaderboardList.innerHTML = '';
        
        leaderboard.forEach((agent, index) => {
            const leaderboardItem = document.createElement('div');
            leaderboardItem.className = 'leaderboard-item';
            leaderboardItem.innerHTML = `
                <div class="leaderboard-rank">#${agent.rank}</div>
                <div class="leaderboard-agent">
                    <div class="agent-name">${agent.agent.substring(0, 8)}...</div>
                    <div class="agent-stats">${agent.points} tokens • ${agent.action_count} actions</div>
                </div>
                <div class="leaderboard-points">${agent.points}</div>
            `;
            leaderboardList.appendChild(leaderboardItem);
        });
    }

    renderPerformanceChart(performanceData) {
        const chartContainer = document.getElementById('performanceChart');
        if (!chartContainer) return;
        
        // Simple text-based chart for demo
        chartContainer.innerHTML = `
            <div class="chart-title">Performance Over Time</div>
            <div class="chart-data">
                ${performanceData.map(day => `
                    <div class="chart-day">
                        <div class="day-label">${new Date(day.date * 1000).toLocaleDateString()}</div>
                        <div class="day-bar" style="width: ${Math.min(100, (day.points / 100) * 100)}%"></div>
                        <div class="day-value">${day.points} pts</div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    renderEvaluations() {
        const evaluationsList = document.getElementById('evaluationsList');
        evaluationsList.innerHTML = '';

        this.evaluations.slice(0, 10).forEach(evaluation => {
            const evaluationElement = document.createElement('div');
            evaluationElement.className = 'evaluation-item';
            evaluationElement.innerHTML = `
                <div>
                    <div class="evaluation-result ${evaluation.result}">
                        ${evaluation.result === 'good' ? '✓ Good' : '✗ Bad'}
                    </div>
                    <div class="evaluation-reason">${evaluation.reason}</div>
                </div>
                <div class="evaluation-time">${this.formatTimestamp(evaluation.timestamp / 1000)}</div>
            `;
            evaluationsList.appendChild(evaluationElement);
        });
    }

    loadSettings() {
        // Load current agent settings (placeholder)
        document.getElementById('agentNameInput').value = this.currentAgent ? 'Current Agent' : '';
        document.getElementById('agentDescription').value = 'Agent description...';
        document.getElementById('evaluationThreshold').value = '0.8';
        document.getElementById('autoEvaluation').checked = false;
    }

    async saveSettings() {
        const settings = {
            name: document.getElementById('agentNameInput').value,
            description: document.getElementById('agentDescription').value,
            threshold: document.getElementById('evaluationThreshold').value,
            autoEvaluation: document.getElementById('autoEvaluation').checked
        };

        // In a real app, this would save to the backend
        this.showNotification('Settings saved successfully!', 'success');
        this.addLog('info', 'Agent settings updated');
    }

    addLog(level, message) {
        this.logs.unshift({
            timestamp: Date.now(),
            level: level,
            message: message
        });

        // Keep only last 100 logs
        if (this.logs.length > 100) {
            this.logs = this.logs.slice(0, 100);
        }

        // Re-render if logs tab is active
        if (document.querySelector('[data-tab="logs"]').classList.contains('active')) {
            this.renderLogs();
        }
    }

    clearLogs() {
        this.logs = [];
        this.renderLogs();
    }

    filterLogs(level) {
        const logsContent = document.getElementById('logsContent');
        const logEntries = logsContent.querySelectorAll('.log-entry');
        
        logEntries.forEach(entry => {
            if (level === 'all' || entry.classList.contains(level)) {
                entry.style.display = 'block';
            } else {
                entry.style.display = 'none';
            }
        });
    }

    updateStats() {
        document.getElementById('totalAgents').textContent = this.agents.length;
        document.getElementById('activeActions').textContent = this.agents.reduce((sum, agent) => sum + (agent.actions?.length || 0), 0);
    }

    updateAgentStats(data) {
        document.getElementById('agentActions').textContent = data.actions?.length || 0;
    }

    showAddAgentModal() {
        document.getElementById('addAgentModal').classList.add('active');
    }

    hideAddAgentModal() {
        document.getElementById('addAgentModal').classList.remove('active');
    }

    hideModal() {
        document.getElementById('actionModal').classList.remove('active');
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <i class="fas fa-${this.getNotificationIcon(type)}"></i>
            <span>${message}</span>
        `;

        // Add to page
        document.body.appendChild(notification);

        // Animate in
        setTimeout(() => notification.classList.add('show'), 100);

        // Remove after 3 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    getNotificationIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    }

    parseJSON(str) {
        try {
            return str ? JSON.parse(str) : {};
        } catch (error) {
            return null;
        }
    }

    formatTimestamp(timestamp) {
        return new Date(timestamp * 1000).toLocaleString();
    }

    async createDemoData() {
        this.showNotification('Creating demo data...', 'info');
        
        const demoAgents = [
            {
                id: "0x1234567890123456789012345678901234567890",
                name: "Financial Advisor Bot",
                owner_org: "Demo Corp",
                pubkey: "demo_pubkey_1",
                stake_address: "0x1234567890123456789012345678901234567890",
                type: "financial"
            },
            {
                id: "0x2345678901234567890123456789012345678901", 
                name: "Medical Assistant",
                owner_org: "HealthTech Inc",
                pubkey: "demo_pubkey_2",
                stake_address: "0x2345678901234567890123456789012345678901",
                type: "medical"
            },
            {
                id: "0x3456789012345678901234567890123456789012",
                name: "Legal Advisor",
                owner_org: "LawFirm LLC", 
                pubkey: "demo_pubkey_3",
                stake_address: "0x3456789012345678901234567890123456789012",
                type: "legal"
            }
        ];

        try {
            // Create demo agents
            for (const agent of demoAgents) {
                try {
                    await fetch(`${this.API_BASE}/agents`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(agent)
                    });
                } catch (error) {
                    console.warn(`Agent ${agent.name} might already exist:`, error);
                }
            }

            // Create demo actions for each agent
            const demoActions = [
                {
                    agent: "0x1234567890123456789012345678901234567890",
                    model: "gpt-4o-mini",
                    model_hash: "sha256:abc123...",
                    dataset_id: "financial-data-v1",
                    dataset_hash: "sha256:def456...",
                    inputs: {"query": "What is the current market trend for tech stocks?", "user_id": "user123"},
                    outputs: {"analysis": "Tech stocks are showing bullish trends...", "confidence": 0.85},
                    notes: "Market analysis request"
                },
                {
                    agent: "0x2345678901234567890123456789012345678901",
                    model: "gpt-4o-mini", 
                    model_hash: "sha256:ghi789...",
                    dataset_id: "medical-data-v1",
                    dataset_hash: "sha256:jkl012...",
                    inputs: {"symptoms": ["headache", "fever"], "age": 35, "gender": "female"},
                    outputs: {"diagnosis": "Possible viral infection", "recommendation": "Rest and hydration", "confidence": 0.78},
                    notes: "Symptom analysis"
                },
                {
                    agent: "0x3456789012345678901234567890123456789012",
                    model: "gpt-4o-mini",
                    model_hash: "sha256:mno345...",
                    dataset_id: "legal-data-v1", 
                    dataset_hash: "sha256:pqr678...",
                    inputs: {"contract_text": "This agreement is between...", "question": "Are there any liability issues?"},
                    outputs: {"analysis": "No major liability concerns found", "risk_level": "low", "confidence": 0.92},
                    notes: "Contract review"
                }
            ];

            for (const action of demoActions) {
                try {
                    await fetch(`${this.API_BASE}/agents/${action.agent}/actions`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(action)
                    });
                } catch (error) {
                    console.warn(`Failed to create action for ${action.agent}:`, error);
                }
            }

            this.showNotification('Demo data created successfully!', 'success');
            await this.loadAgents();
            
        } catch (error) {
            console.error('Failed to create demo data:', error);
            this.showNotification('Failed to create demo data. Please check backend connection.', 'error');
        }
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new AgentAccountabilityApp();
});

// Add notification styles
const notificationStyles = `
.notification {
    position: fixed;
    top: 20px;
    right: 20px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: var(--spacing-md) var(--spacing-lg);
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    box-shadow: var(--shadow-lg);
    z-index: 1001;
    transform: translateX(100%);
    transition: transform 0.3s ease;
}

.notification.show {
    transform: translateX(0);
}

.notification-success {
    border-left: 4px solid var(--success);
    color: var(--success);
}

.notification-error {
    border-left: 4px solid var(--error);
    color: var(--error);
}

.notification-warning {
    border-left: 4px solid var(--warning);
    color: var(--warning);
}

.notification-info {
    border-left: 4px solid var(--info);
    color: var(--info);
}
`;

// Add styles to head
const styleSheet = document.createElement('style');
styleSheet.textContent = notificationStyles;
document.head.appendChild(styleSheet);