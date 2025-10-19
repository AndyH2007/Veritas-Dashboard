# Agent Accountability MVP — Getting Started

This repo is a minimal, end‑to‑end **agent accountability** system:
- **Frontend**: simple dashboard (static) to log actions and view records
- **Backend**: FastAPI (Python) with IPFS‑like JSON store (local), on‑chain anchors, optional Postgres
- **Chain**: Hardhat local network + contract for actions & points (token/score)
- **Database (optional)**: PostgreSQL (you can run with or without it). This guide covers **pgAdmin 4** setup.

> If you just want to click around without Postgres, skip to **Quick Start (No DB)**.

---

## Prerequisites

- **Node.js** (18+), **npm**
- **Python 3.11** (recommended) and **pip**
- **Git Bash / WSL** on Windows (for scripts)
- **PostgreSQL 14+** and **pgAdmin 4** (only if you want DB‑backed routes like `/runs`, `/agents` POST)
- **OpenSSL** on Windows is helpful but not required

---

## Repo Layout (high level)

```
.
├─ backend/
│  ├─ main.py                # FastAPI app (DB optional)
│  ├─ ipfs.py                # local JSON store (CID-like)
│  ├─ eth.py                 # web3 helpers (Hardhat)
│  ├─ chain_config.py        # ABI/address loader
│  ├─ hashutil.py, policies.py, merkle.py
│  ├─ requirements.txt
├─ contracts/ … (solidity, ABI) 
├─ frontend/                 # static html/js dashboard
├─ scripts/deploy.js         # Hardhat deploy
├─ hardhat.config.js
├─ docker-compose.yml        # optional: compose DB + app
└─ start.sh                  # one-shot dev script (bash)
```

---

## Environment Variables

Create **`.env`** files from the templates below. Never commit real secrets — commit **`.env.example`** only.

**Project root** → `.env` (used by Hardhat or tooling if any)  
**backend/** → `backend/.env` (read by `load_dotenv()` inside the API)

**backend/.env example**
```
# Postgres (optional)
DATABASE_URL=postgresql://app:app@localhost:5432/appdb

# S3 bucket name for artifacts (fallbacks to local folder if storage module not present)
S3_BUCKET=audit-traces

# Hardhat RPC (defaults assumed)
RPC_URL=http://127.0.0.1:8545
```

If you do **not** want to run a DB, either leave `DATABASE_URL` unset or remove the line.

---

## Database Setup (PostgreSQL + pgAdmin 4)

If you want DB‑backed endpoints — `/runs`, `/agents` (POST), `/agents/{id}/runs` — set up Postgres:

1. **Create database & user**
   - In **pgAdmin 4** → *Servers* → *PostgreSQL* → **Create → Database…**
     - Name: `appdb`
   - Create a role/user `app` with password `app` (or choose your own). Grant privileges on `appdb`.

2. **Apply schema**
   - In pgAdmin 4, open **Query Tool** for `appdb`.
   - Paste and run your schema (from your repo). You can also save it as `db/init/schema.sql` and run:
     ```sql
     -- Your provided schema (example)
     -- (Keep one version: TEXT/VARCHAR or UUID version — don't create dup tables)
     -- Drop existing tables (for clean setup)
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

     -- Indexes
     CREATE INDEX idx_agents_created_at ON agents(created_at DESC);
     CREATE INDEX idx_runs_agent_id ON runs(agent_id);
     CREATE INDEX idx_runs_created_at ON runs(created_at DESC);
     CREATE INDEX idx_findings_run_id ON audit_findings(run_id);

     -- Optional extension if you plan to use UUIDs and crypto helpers
     CREATE EXTENSION IF NOT EXISTS pgcrypto;
     ```

   > You also pasted a **UUID schema** variant in your snippet. **Pick one approach** (VARCHAR IDs *or* UUID IDs). Don’t create both sets of tables. If you want UUIDs, replace the `VARCHAR(255)` schema with your UUID version and keep `CREATE EXTENSION pgcrypto;`.

3. **Seed data (optional)**
   ```sql
   INSERT INTO agents (id, name, owner_org, pubkey)
   VALUES ('demo-agent','Demo Agent','DemoOrg','0xDEADBEEF') ON CONFLICT DO NOTHING;
   ```

---

## Quick Start (No DB)

If you don’t need DB features right now, you can run chain + backend + frontend only.

**Windows (PowerShell)**
```powershell
# 1) Create & activate venv
py -3.11 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1

# 2) Install backend deps (no compiling issues)
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r backend\requirements.txt

# 3) Start Hardhat (Terminal A)
npx hardhat node

# 4) Deploy contract (Terminal B)
npx hardhat run scripts/deploy.js --network localhost

# 5) Start FastAPI (Terminal C, project root)
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

# 6) Serve frontend (Terminal D)
cd frontend
python -m http.server 8080
```

**macOS / Linux**
```bash
# 1) venv
python3 -m venv .venv
source .venv/bin/activate

# 2) deps
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r backend/requirements.txt

# 3~6) same as above
npx hardhat node
npx hardhat run scripts/deploy.js --network localhost
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
(cd frontend && python -m http.server 8080)
```

**URLs**
- Frontend: http://localhost:8080  
- Backend:  http://localhost:8000  
- Chain:    http://localhost:8545

---

## Quick Start (With DB + pgAdmin 4)

1. Ensure Postgres is running and the schema has been applied (see above).  
2. Set `DATABASE_URL` in `backend/.env`.  
3. Use the same steps as **No DB**, then hit `http://localhost:8000/health` and confirm:
   ```json
   { "ok": true, "chainConnected": true, "dbConnected": true, ... }
   ```
4. DB‑only endpoints enabled:
   - `POST /agents` (register)
   - `POST /runs`
   - `GET /agents/{id}/runs`

> If `dbConnected: false`, verify credentials and that you can connect with pgAdmin using the same URL.

---

## One‑Shot Script (optional)

You can use `start.sh` (bash) to orchestrate everything. On Windows, run it in **Git Bash** or **WSL**:
```bash
chmod +x start.sh
./start.sh
# PowerShell alternative: bash start.sh
```

---

## Common Issues & Fixes (Windows)

- **`ModuleNotFoundError: No module named 'backend'`**  
  Run the API **from the project root**:  
  `python -m uvicorn backend.main:app --port 8000 --reload` and ensure `backend/__init__.py` exists (even empty).

- **C‑extension build errors** (e.g., `psycopg2`, `cytoolz`, `bitarray`)  
  - Prefer **Python 3.11** venv (wheels are available).  
  - For Postgres: `pip install psycopg2-binary==2.9.9`.  
  - If you don’t need Postgres, leave `DATABASE_URL` unset.

- **Port already in use** (8545/8000/8080)  
  Kill old processes or change ports.

---

## Testing the Flow

1. **Log an action** (frontend or cURL):
   ```bash
   curl -X POST http://localhost:8000/log-action \
     -H "Content-Type: application/json" \
     -d '{"inputs":{"prompt":"buy 1 BTC"},"outputs":{"decision":"deny","reason":"policy"} }'
   ```
   Response includes `{hash, cid, ts, findings}`.

2. **On‑chain record for a specific agent**:
   ```bash
   curl -X POST "http://localhost:8000/agents/0xABC.../actions" \
     -H "Content-Type: application/json" \
     -d '{"inputs": {"order":"#123"}, "outputs": {"decision":"approve"}}'
   ```

3. **Evaluate with token/points adjustment**:
   ```bash
   curl -X POST "http://localhost:8000/agents/0xABC.../evaluate" \
     -H "Content-Type: application/json" \
     -d '{"index":0, "good":true, "delta":2, "reason":"manual check"}'
   ```

4. **View IPFS‑like record**:
   ```bash
   curl http://localhost:8000/ipfs/<cid>
   ```

---

## Docker (optional, for DB + API)

If you want a reproducible Postgres along with your app, you can use `docker-compose.yml` (included). A typical pattern:

```
docker compose up -d db
# apply schema:
docker exec -it <postgres-container> psql -U app -d appdb -f /docker-entrypoint-initdb.d/schema.sql
```

Populate `db/init/` with `schema.sql` and `seed.sql` to auto‑init the DB on first run.

---

## Contributing / Scripts

- `scripts/deploy.js` — deploys contract to local Hardhat
- `backend/requirements.txt` — pin Python deps (use 3.11 to avoid C build pain on Windows)
- `start.sh` — convenience launcher (Git Bash/WSL)

---

## License

MIT (or your preferred license). Update this section as needed.
