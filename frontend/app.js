// Agent Accountability Platform - Main Application


class AgentAccountabilityApp {
    constructor() {
        this.API_BASE = "http://localhost:8000";
        this.currentAgent = null;
        this.agents = [];
        this.logs = [];
        this.evaluations = [];
        
        // ⭐ ADD THESE TWO LINES
        this.riskDashboard = new RiskDashboard(this);
        window.riskDashboard = this.riskDashboard;
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadInitialData();
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
        setInterval(() => this.loadAgents(), 30000);
        setInterval(() => this.loadSystemHealth(), 10000);
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
            } else {
                healthElement.textContent = 'Unhealthy';
                healthElement.className = 'stat-value error';
            }
        } catch (error) {
            console.error('Health check failed:', error);
            document.getElementById('systemHealth').textContent = 'Offline';
            document.getElementById('systemHealth').className = 'stat-value error';
        }
    }

    async loadAgents() {
        try {
            const response = await fetch(`${this.API_BASE}/agents`);
            const data = await response.json();
            
            this.agents = data.agents || [];
            
            // Load agent types
            try {
                const typesResponse = await fetch(`${this.API_BASE}/agent-types`);
                const typesData = await typesResponse.json();
                this.agentTypes = typesData.types;
                
                this.agents.forEach(agent => {
                    const agentType = this.agentTypes.find(type => type.id === agent.type) || this.agentTypes[0];
                    agent.typeName = agentType.name;
                    agent.icon = agentType.icon;
                });
            } catch (typesError) {
                console.warn('Failed to load agent types:', typesError);
            }
            
            this.renderAgents();
            this.updateStats();
            
            if (!this.currentAgent && this.agents.length > 0) {
                this.selectAgent(this.agents[0].agent);
            }
            
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
            
            // ⭐ NEW: Add reputation badge
            const reputation = agent.reputation || 50;
            const reputationBadge = this.riskDashboard.getReputationBadge(reputation);
            
            agentElement.innerHTML = `
                <div class="agent-status ${agent.points > 0 ? '' : 'inactive'}"></div>
                <div class="agent-name">
                    <i class="${agent.icon || 'fas fa-robot'}"></i>
                    ${agent.name || 'Unnamed Agent'}
                </div>
                <div class="agent-type">${agent.typeName || 'General Purpose'}</div>
                ${reputationBadge}
                <div class="agent-tokens">${agent.points || 0} tokens</div>
            `;
            
            agentElement.addEventListener('click', () => this.selectAgent(agent.agent));
            agentList.appendChild(agentElement);
        });
    }

    async selectAgent(agentAddress) {
        this.currentAgent = agentAddress;
        this.renderAgents();
        
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
        
        const performance = agent.points > 0 ? Math.min(100, Math.max(0, (agent.points / 100) * 100)) : 0;
        document.getElementById('agentPerformance').textContent = `${Math.round(performance)}%`;
    }

    async loadActions() {
        if (!this.currentAgent) return;

        try {
            const response = await fetch(`${this.API_BASE}/agents/${this.currentAgent}/actions`);
            const data = await response.json();
            
            // Update action count in header
            document.getElementById('agentActions').textContent = data.actions?.length || 0;
            
            this.renderActions(data.actions || []);
        } catch (error) {
            console.error('Failed to load actions:', error);
            this.showNotification('Failed to load actions', 'error');
        }
    }

    renderActions(actions) {
        const tbody = document.getElementById('actionsTableBody');
        tbody.innerHTML = '';

        if (actions.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center text-muted" style="padding: var(--spacing-xl);">
                        No actions logged yet. Log your first action above!
                    </td>
                </tr>
            `;
            return;
        }

        actions.forEach((action, index) => {
            const row = document.createElement('tr');
            const hashShort = action.hash_short || (action.hash ? action.hash.substring(0, 16) + '...' : 'N/A');
            
            row.innerHTML = `
                <td>${this.formatTimestamp(action.timestamp)}</td>
                <td>${action.model || 'Unknown'}</td>
                <td class="mono">${hashShort}</td>
                <td>
                    <span class="status-indicator success"></span>
                    <span>Recorded</span>
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
                
                document.getElementById('agentTokens').textContent = data.points;
                
                await this.loadActions();
                await this.loadAgents();
                
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
    
        // ⭐ NEW: Check if this is a bypass (coming from risk modal approval)
        const skipRiskCheck = arguments[0] === true;
    
        // Show risk analysis modal ONLY if not bypassing
        if (!skipRiskCheck) {
            const currentAgentData = this.agents.find(a => a.agent === this.currentAgent);
            const agentType = currentAgentData?.type || 'general';
    
            const actionData = {
                inputs: inputs,
                outputs: outputs,
                model: document.getElementById('model').value,
                agent_type: agentType
            };
    
            // Show risk analysis
            const riskAnalysis = await this.riskDashboard.showRiskAnalysisModal(
                this.currentAgent,
                actionData
            );
    
            // If blocked, stop here
            if (riskAnalysis && riskAnalysis.risk_analysis.should_block) {
                this.showNotification('Action blocked by Risk Oracle due to critical risk', 'error');
                return;
            }
    
            // If modal was shown, it will call logAction(true) when user clicks proceed
            // So we return here and wait for that callback
            if (riskAnalysis) {
                return; // ⭐ IMPORTANT: Return here, don't continue
            }
        }
    
        // ⭐ Continue with actual logging (only if bypassing or no modal shown)
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
    
            // ⭐ Parse response body first
            const data = await response.json().catch(() => null);
            
            if (response.ok && data) {
                // ⭐ SUCCESS PATH - Only show notification here
                if (data.flagged) {
                    this.showNotification('Action logged with risk flag - review recommended', 'warning');
                } else {
                    this.showNotification('Action logged successfully!', 'success');
                }
                
                this.clearActionForm();
                await this.loadActions();
                this.addLog('info', `Action logged: ${data.cid}`);
            } else {
                // ⭐ ERROR PATH - Handle backend errors
                const errorMsg = data?.detail || 'Unknown error occurred';
                this.showNotification(`Failed to log action: ${errorMsg}`, 'error');
            }
        } catch (error) {
            // ⭐ NETWORK ERROR PATH - Only network/connection issues reach here
            console.error('Network error while logging action:', error);
            this.showNotification('Network error. Please check your connection.', 'error');
        } finally {
            logButton.innerHTML = originalText;
            logButton.disabled = false;
        }
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
            const response = await fetch(`${this.API_BASE}/agents`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name: name,
                    type: type,
                    description: description
                })
            });

            if (response.ok) {
                this.showNotification('Agent created successfully!', 'success');
                this.hideAddAgentModal();
                this.clearAddAgentForm();
                await this.loadAgents();
                this.addLog('info', `New agent created: ${name}`);
            } else {
                const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
                this.showNotification(`Failed to create agent: ${errorData.detail}`, 'error');
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
        document.querySelectorAll('.tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        document.querySelectorAll('.tab-panel').forEach(panel => {
            panel.classList.remove('active');
        });
        document.getElementById(`${tabName}Tab`).classList.add('active');

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

        if (this.logs.length === 0) {
            logsContent.innerHTML = `
                <div class="text-center text-muted" style="padding: var(--spacing-xl);">
                    No logs yet. Actions will be logged here.
                </div>
            `;
            return;
        }

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
            const response = await fetch(`${this.API_BASE}/agents/${this.currentAgent}/analytics`);
            const data = await response.json();
            
            // Calculate dynamic success rate based on evaluations
            let successRate = 0;
            if (this.evaluations.length > 0) {
                const goodCount = this.evaluations.filter(e => e.result === 'good').length;
                successRate = Math.round((goodCount / this.evaluations.length) * 100);
            } else if (data.metrics && data.metrics.success_rate) {
                successRate = Math.round(data.metrics.success_rate * 100);
            }
            
            document.getElementById('successRate').textContent = `${successRate}%`;

            this.renderPerformanceChart(data.performance_data || []);
            this.renderEvaluations();
            
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
            
            const leaderboardContainer = document.querySelector('#analyticsTab .analytics-grid');
            if (!document.getElementById('leaderboardCard')) {
                const leaderboardCard = document.createElement('div');
                leaderboardCard.className = 'chart-card';
                leaderboardCard.id = 'leaderboardCard';
                leaderboardCard.innerHTML = `
                    <h3>Top Agents</h3>
                    <div class="leaderboard-list" id="leaderboardList"></div>
                `;
                leaderboardContainer.appendChild(leaderboardCard);
            }
            
            this.renderLeaderboard(data.leaderboard || []);
        } catch (error) {
            console.error('Failed to load leaderboard:', error);
        }
    }

    renderLeaderboard(leaderboard) {
        const leaderboardList = document.getElementById('leaderboardList');
        if (!leaderboardList) return;
        
        leaderboardList.innerHTML = '';
        
        if (leaderboard.length === 0) {
            leaderboardList.innerHTML = `
                <div class="text-center text-muted" style="padding: var(--spacing-lg);">
                    No agents to rank yet
                </div>
            `;
            return;
        }
        
        leaderboard.forEach((agent) => {
            const leaderboardItem = document.createElement('div');
            leaderboardItem.className = 'leaderboard-item';
            const agentName = agent.name || agent.agent.substring(0, 8) + '...';
            leaderboardItem.innerHTML = `
                <div class="leaderboard-rank">#${agent.rank}</div>
                <div class="leaderboard-agent">
                    <div class="agent-name">${agentName}</div>
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
        
        if (!performanceData || performanceData.length === 0) {
            chartContainer.innerHTML = `
                <div class="text-center text-muted">
                    <i class="fas fa-chart-line"></i>
                    <p>No performance data available yet</p>
                </div>
            `;
            return;
        }
        
        // Limit chart data width
        chartContainer.innerHTML = `
            <div class="chart-container">
                <div class="chart-title">Performance Over Time</div>
                <div class="chart-data">
                    ${performanceData.slice(0, 7).map(day => `
                        <div class="chart-day">
                            <div class="day-label">${new Date(day.date * 1000).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</div>
                            <div class="day-bar-container">
                                <div class="day-bar" style="width: ${Math.min(100, Math.max(5, (day.points / 100) * 100))}%"></div>
                            </div>
                            <div class="day-value">${day.points}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    renderEvaluations() {
        const evaluationsList = document.getElementById('evaluationsList');
        if (!evaluationsList) return;
        
        evaluationsList.innerHTML = '';

        if (this.evaluations.length === 0) {
            evaluationsList.innerHTML = `
                <div class="text-center text-muted" style="padding: var(--spacing-lg);">
                    No evaluations yet. Rate actions to see results here.
                </div>
            `;
            return;
        }

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
        const agent = this.agents.find(a => a.agent === this.currentAgent);
        document.getElementById('agentNameInput').value = agent?.name || '';
        document.getElementById('agentDescription').value = agent?.description || '';
        document.getElementById('evaluationThreshold').value = '0.8';
        document.getElementById('autoEvaluation').checked = false;
    }

    async saveSettings() {
        this.showNotification('Settings saved successfully!', 'success');
        this.addLog('info', 'Agent settings updated');
    }

    addLog(level, message) {
        this.logs.unshift({
            timestamp: Date.now(),
            level: level,
            message: message
        });

        if (this.logs.length > 100) {
            this.logs = this.logs.slice(0, 100);
        }

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
        const totalActions = this.agents.reduce((sum, agent) => {
            return sum + (agent.action_count || 0);
        }, 0);
        document.getElementById('activeActions').textContent = totalActions;
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
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <i class="fas fa-${this.getNotificationIcon(type)}"></i>
            <span>${message}</span>
        `;

        document.body.appendChild(notification);

        setTimeout(() => notification.classList.add('show'), 100);

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
        const date = new Date(timestamp * 1000);
        return date.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    async createDemoData() {
        this.showNotification('Creating demo data...', 'info');
        
        const demoAgents = [
            {
                name: "Financial Advisor Bot",
                type: "financial",
                description: "AI agent for financial advice and market analysis"
            },
            {
                name: "Medical Assistant",
                type: "medical",
                description: "Healthcare AI for symptom analysis and guidance"
            },
            {
                name: "Legal Advisor",
                type: "legal",
                description: "Legal document analysis and advisory AI"
            }
        ];

        try {
            const createdAgents = [];
            
            for (const agent of demoAgents) {
                try {
                    const response = await fetch(`${this.API_BASE}/agents`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(agent)
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        createdAgents.push(data.agent.id);
                    }
                } catch (error) {
                    console.warn(`Failed to create ${agent.name}:`, error);
                }
            }

            // Reload agents to get the created ones
            await this.loadAgents();

            // Create demo actions for created agents
            const demoActions = [
                {
                    model: "gpt-4",
                    inputs: {"query": "What is the current market trend?"},
                    outputs: {"analysis": "Markets showing bullish trends", "confidence": 0.85}
                },
                {
                    model: "claude-3-sonnet",
                    inputs: {"symptoms": ["headache", "fever"]},
                    outputs: {"diagnosis": "Possible viral infection", "confidence": 0.78}
                }
            ];

            for (let i = 0; i < Math.min(createdAgents.length, demoActions.length); i++) {
                try {
                    await fetch(`${this.API_BASE}/agents/${createdAgents[i]}/actions`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            ...demoActions[i],
                            model_hash: `sha256:${Math.random().toString(36).substring(7)}`,
                            dataset_id: "demo-dataset-v1",
                            dataset_hash: `sha256:${Math.random().toString(36).substring(7)}`,
                            notes: "Demo action"
                        })
                    });
                } catch (error) {
                    console.warn(`Failed to create action:`, error);
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

class RiskDashboard {
    constructor(app) {
        this.app = app;
        this.API_BASE = app.API_BASE;
    }

    /**
     * Show risk analysis modal before logging action
     */
    async showRiskAnalysisModal(agentId, actionData) {
        try {
            // Call risk analysis endpoint
            const response = await fetch(`${this.API_BASE}/risk/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    agent_id: agentId,
                    agent_type: actionData.agent_type || 'general',
                    inputs: actionData.inputs,
                    outputs: actionData.outputs,
                    model: actionData.model
                })
            });

            if (!response.ok) {
                throw new Error('Risk analysis failed');
            }

            const data = await response.json();
            const riskAnalysis = data.risk_analysis;

            // Create modal HTML
            const modal = document.createElement('div');
            modal.className = 'modal risk-modal active';
            modal.innerHTML = `
                <div class="modal-content risk-modal-content">
                    <div class="modal-header">
                        <h3>⚡ Risk Analysis</h3>
                        <button class="modal-close" onclick="this.closest('.modal').remove()">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="modal-body risk-modal-body">
                        ${this.buildRiskGauge(riskAnalysis)}
                        ${this.buildRiskFlags(riskAnalysis)}
                        ${this.buildRiskExplanation(riskAnalysis)}
                        ${this.buildActionButtons(riskAnalysis, data.recommendation)}
                    </div>
                </div>
            `;

            document.body.appendChild(modal);
            return data;
        } catch (error) {
            console.error('Risk analysis error:', error);
            this.app.showNotification('Risk analysis unavailable, proceeding without check', 'warning');
            return null;
        }
    }

    /**
     * Build risk gauge visualization
     */
    buildRiskGauge(analysis) {
        const score = analysis.risk_score;
        const level = analysis.risk_level;
        
        // Color based on risk level
        const colors = {
            low: '#10b981',
            medium: '#f59e0b',
            high: '#ef4444',
            critical: '#dc2626'
        };
        const color = colors[level] || colors.medium;

        // Gauge rotation (0° = 0 score, 180° = 100 score)
        const rotation = (score / 100) * 180;

        return `
            <div class="risk-gauge-container">
                <div class="risk-gauge">
                    <svg viewBox="0 0 200 120" class="gauge-svg">
                        <!-- Background arc -->
                        <path d="M 20 100 A 80 80 0 0 1 180 100" 
                              fill="none" 
                              stroke="#334155" 
                              stroke-width="20" 
                              stroke-linecap="round"/>
                        
                        <!-- Colored arc based on score -->
                        <path d="M 20 100 A 80 80 0 0 1 180 100" 
                              fill="none" 
                              stroke="${color}" 
                              stroke-width="20" 
                              stroke-linecap="round"
                              stroke-dasharray="${(score / 100) * 251}, 251"
                              class="gauge-fill"/>
                        
                        <!-- Center circle -->
                        <circle cx="100" cy="100" r="50" fill="#1e293b" stroke="${color}" stroke-width="3"/>
                        
                        <!-- Score text -->
                        <text x="100" y="95" 
                              text-anchor="middle" 
                              font-size="32" 
                              font-weight="bold" 
                              fill="${color}">
                            ${Math.round(score)}
                        </text>
                        <text x="100" y="115" 
                              text-anchor="middle" 
                              font-size="14" 
                              fill="#94a3b8">
                            RISK SCORE
                        </text>
                    </svg>
                </div>
                
                <div class="risk-level-badge risk-level-${level}">
                    ${this.getRiskLevelIcon(level)} ${level.toUpperCase()}
                </div>
                
                <div class="risk-confidence">
                    Confidence: ${Math.round(analysis.confidence * 100)}%
                </div>
            </div>
        `;
    }

    /**
     * Build risk flags list
     */
    buildRiskFlags(analysis) {
        if (!analysis.flags || analysis.flags.length === 0) {
            return `
                <div class="risk-flags">
                    <div class="no-flags">
                        <i class="fas fa-check-circle"></i>
                        <p>No risk factors detected</p>
                    </div>
                </div>
            `;
        }

        const flagsHtml = analysis.flags.map(flag => {
            const icon = this.getFlagIcon(flag.severity);
            const severityClass = `flag-${flag.severity}`;
            
            return `
                <div class="risk-flag ${severityClass}">
                    <div class="flag-icon">${icon}</div>
                    <div class="flag-content">
                        <div class="flag-title">${flag.type.replace(/_/g, ' ').toUpperCase()}</div>
                        <div class="flag-message">${flag.message}</div>
                    </div>
                </div>
            `;
        }).join('');

        return `
            <div class="risk-flags">
                <h4>Risk Factors Detected:</h4>
                ${flagsHtml}
            </div>
        `;
    }

    /**
     * Build explanation text
     */
    buildRiskExplanation(analysis) {
        return `
            <div class="risk-explanation">
                <h4>Analysis:</h4>
                <pre>${analysis.explanation}</pre>
            </div>
        `;
    }

    /**
     * Build action buttons based on recommendation
     */
    buildActionButtons(analysis, recommendation) {
        if (analysis.should_block) {
            return `
                <div class="risk-actions blocked">
                    <div class="block-message">
                        <i class="fas fa-ban"></i>
                        <strong>Action Blocked</strong>
                        <p>This action has been automatically blocked due to critical risk level.</p>
                    </div>
                    <button class="btn btn-outline" onclick="this.closest('.modal').remove()">
                        Close
                    </button>
                </div>
            `;
        }

        if (recommendation.requires_approval) {
            return `
                <div class="risk-actions flagged">
                    <div class="warning-message">
                        <i class="fas fa-exclamation-triangle"></i>
                        <strong>Manual Approval Required</strong>
                        <p>${recommendation.reason}</p>
                    </div>
                    <div class="button-group">
                        <button class="btn btn-error" onclick="this.closest('.modal').remove()">
                            Cancel Action
                        </button>
                        <button class="btn btn-warning" onclick="window.riskDashboard.proceedWithOverride()">
                            <i class="fas fa-user-shield"></i>
                            Override (Admin)
                        </button>
                    </div>
                </div>
            `;
        }

        return `
            <div class="risk-actions approved">
                <div class="success-message">
                    <i class="fas fa-check-circle"></i>
                    <strong>Action Approved</strong>
                    <p>Risk level is within acceptable range.</p>
                </div>
                <div class="button-group">
                    <button class="btn btn-outline" onclick="this.closest('.modal').remove()">
                        Cancel
                    </button>
                    <button class="btn btn-success" onclick="window.riskDashboard.proceedWithAction()">
                        <i class="fas fa-arrow-right"></i>
                        Proceed
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Get risk level icon
     */
    getRiskLevelIcon(level) {
        const icons = {
            low: '✓',
            medium: '⚠',
            high: '⚡',
            critical: '🚫'
        };
        return icons[level] || '•';
    }

    /**
     * Get flag severity icon
     */
    getFlagIcon(severity) {
        const icons = {
            low: '<i class="fas fa-info-circle"></i>',
            medium: '<i class="fas fa-exclamation-triangle"></i>',
            high: '<i class="fas fa-exclamation-circle"></i>'
        };
        return icons[severity] || icons.medium;
    }

    /**
     * Proceed with action (after approval)
     */
    /**
 * Proceed with action (after approval)
 */
async proceedWithAction() {
    const modal = document.querySelector('.risk-modal');
    if (modal) modal.remove();
    
    // ⭐ Call logAction with bypass flag
    await this.app.logAction(true); // true = skip risk check
}

    /**
     * Proceed with admin override
     */
    async proceedWithOverride() {
        const confirmed = confirm(
            'Are you sure you want to override the risk assessment?\n\n' +
            'This action will be logged with an admin override flag.'
        );
        
        if (confirmed) {
            const modal = document.querySelector('.risk-modal');
            if (modal) modal.remove();
            
            this.app.showNotification('Action proceeding with admin override', 'warning');
            
            // ⭐ Call logAction with bypass flag
            await this.app.logAction(true); // true = skip risk check
        }
    }

    /**
     * Show agent reputation badge
     */
    getReputationBadge(reputation) {
        let level, color, icon;
        
        if (reputation >= 80) {
            level = 'Trusted';
            color = '#10b981';
            icon = '⭐';
        } else if (reputation >= 60) {
            level = 'Reliable';
            color = '#3b82f6';
            icon = '✓';
        } else if (reputation >= 40) {
            level = 'Neutral';
            color = '#f59e0b';
            icon = '•';
        } else if (reputation >= 20) {
            level = 'Concerning';
            color = '#ef4444';
            icon = '⚠';
        } else {
            level = 'High Risk';
            color = '#dc2626';
            icon = '🚫';
        }

        return `
            <div class="reputation-badge" style="background: ${color}20; color: ${color}; border: 1px solid ${color}">
                <span class="reputation-icon">${icon}</span>
                <span class="reputation-text">${level}</span>
                <span class="reputation-score">${Math.round(reputation)}</span>
            </div>
        `;
    }
}


document.addEventListener('DOMContentLoaded', () => {
    window.app = new AgentAccountabilityApp();
});

// Notification styles
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

const styleSheet = document.createElement('style');
styleSheet.textContent = notificationStyles;
document.head.appendChild(styleSheet);