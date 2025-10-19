-- Drop tables if they exist (for clean setup)
DROP TABLE IF EXISTS audit_findings CASCADE;
DROP TABLE IF EXISTS runs CASCADE;
DROP TABLE IF EXISTS agents CASCADE;

-- Agents table
CREATE TABLE agents (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    owner_org VARCHAR(255),
    pubkey TEXT,
    stake_address VARCHAR(255),
    agent_type VARCHAR(50) DEFAULT 'general',
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Runs table (for attestations)
CREATE TABLE runs (
    id VARCHAR(255) PRIMARY KEY,
    agent_id VARCHAR(255) REFERENCES agents(id),
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP NOT NULL,
    model_name VARCHAR(255),
    model_version VARCHAR(255),
    container_digest VARCHAR(255),
    input_hash VARCHAR(255),
    output_hash VARCHAR(255),
    trace_hash VARCHAR(255),
    s3_trace_key TEXT,
    params JSONB,
    claim JSONB,
    signature TEXT,
    policy_summary JSONB,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit findings table
CREATE TABLE audit_findings (
    id VARCHAR(255) PRIMARY KEY,
    run_id VARCHAR(255) REFERENCES runs(id),
    severity VARCHAR(50),
    code VARCHAR(100),
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_agents_created_at ON agents(created_at DESC);
CREATE INDEX idx_runs_agent_id ON runs(agent_id);
CREATE INDEX idx_runs_created_at ON runs(created_at DESC);
CREATE INDEX idx_findings_run_id ON audit_findings(run_id);