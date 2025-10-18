CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS agents (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  owner_org TEXT,
  pubkey TEXT NOT NULL,
  stake_address TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);


CREATE TABLE IF NOT EXISTS runs (
  id UUID PRIMARY KEY,
  agent_id UUID REFERENCES agents(id),
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  model_name TEXT,
  model_version TEXT,
  container_digest TEXT,
  input_hash TEXT,
  output_hash TEXT,
  trace_hash TEXT,
  s3_trace_key TEXT,
  params JSONB,
  claim JSONB,
  signature TEXT,
  policy_summary JSONB,
  status TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_findings (
  id UUID PRIMARY KEY,
  run_id UUID REFERENCES runs(id),
  severity TEXT,
  code TEXT,
  message TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS merkle_batches (
  id BIGSERIAL PRIMARY KEY,
  batch_start TIMESTAMPTZ,
  batch_end TIMESTAMPTZ,
  root_hash TEXT NOT NULL,
  onchain_tx TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
