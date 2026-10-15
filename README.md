# RecoverAI — AI-Powered Revenue Recovery Agent

> Razorpay AI Buildathon — AI Revenue Recovery Track

RecoverAI detects at-risk revenue, diagnoses failure patterns, recommends recovery actions, enforces deterministic policy rules, executes simulated recovery workflows, and measures outcomes with full audit trails.

**⚠ Simulation Mode:** All payment operations are simulated. No real financial transactions are processed. Recovered values are simulated outcomes and do not represent real merchant revenue.

---

## Table of Contents

1. [Business Problem](#business-problem)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Technology Stack](#technology-stack)
5. [Quick Start](#quick-start)
6. [Environment Variables](#environment-variables)
7. [Database Schema](#database-schema)
8. [AI Decision Process](#ai-decision-process)
9. [Recovery Policy](#recovery-policy)
10. [CSV Format](#csv-format)
11. [Synthetic Dataset](#synthetic-dataset)
12. [Evaluation Methodology](#evaluation-methodology)
13. [Metric Definitions](#metric-definitions)
14. [API Documentation](#api-documentation)
15. [Running Tests](#running-tests)
16. [Docker Deployment](#docker-deployment)
17. [AWS Deployment Guide](#aws-deployment-guide)
18. [Razorpay Test Mode](#razorpay-test-mode)
19. [Known Limitations](#known-limitations)
20. [Security Considerations](#security-considerations)

---

## Business Problem

Merchants lose revenue through:

- Failed payments (network failures, auth issues, insufficient funds)
- Checkout abandonment
- Failed recurring subscription payments
- Overdue invoices and receivables
- Poorly timed or irrelevant recovery communications
- Unnecessary retries that annoy customers
- No visibility into which cases are actually recoverable

RecoverAI provides a complete recovery lifecycle with measurable outcomes.

---

## Features

| Feature | Status |
|---------|--------|
| Failed payment detection & categorization | ✅ |
| Risk scoring (0–100) | ✅ |
| AI-assisted recovery recommendations | ✅ |
| Deterministic policy engine (overrides LLM) | ✅ |
| 5 recovery workflows | ✅ |
| Simulated payment provider | ✅ |
| Optional Razorpay test-mode adapter | ✅ |
| Optional OpenRouter LLM integration | ✅ |
| Append-only audit trail | ✅ |
| Batch CSV import with validation | ✅ |
| 100+ record synthetic dataset generator | ✅ |
| Batch evaluation engine | ✅ |
| 3-strategy comparison (baseline/fixed/AI) | ✅ |
| 20 evaluation metrics | ✅ |
| Idempotency / duplicate prevention | ✅ |
| Human approval workflow | ✅ |
| Policy configuration UI | ✅ |
| Evaluation report export (CSV/JSON) | ✅ |
| Responsive fintech dashboard | ✅ |
| 126 automated tests | ✅ |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   React Frontend (Vite)                  │
│  Dashboard · Transactions · Recovery · Evaluation · Audit│
└────────────────────────┬────────────────────────────────┘
                         │ HTTP /api/v1
┌────────────────────────▼────────────────────────────────┐
│                 FastAPI Backend                          │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │  CSV Import │  │  Recovery    │  │  Evaluation    │  │
│  │  + Validate │  │  Agent       │  │  Engine        │  │
│  └─────────────┘  └──────┬───────┘  └────────────────┘  │
│                          │                               │
│  ┌─────────────────────────────────────────────────────┐ │
│  │           Recovery Agent State Machine               │ │
│  │  DETECTED→DIAGNOSED→RECOMMENDED→POLICY_CHECKED→     │ │
│  │  APPROVED→EXECUTING→SUCCEEDED|FAILED|BLOCKED        │ │
│  └──────────┬──────────────────┬───────────────────────┘ │
│             │                  │                          │
│  ┌──────────▼──────┐  ┌───────▼──────────────────────┐  │
│  │  AI Provider    │  │  Policy Engine (authoritative)│  │
│  │  Rule-based     │  │  Retry limits · Consent ·     │  │
│  │  OpenRouter LLM │  │  Fraud stops · Action budget  │  │
│  └─────────────────┘  └──────────────────────────────┘  │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │           Payment Provider Adapter                   │ │
│  │  SimulationProvider | RazorpayTestProvider           │ │
│  └─────────────────────────────────────────────────────┘ │
└────────────────────────┬────────────────────────────────┘
                         │ SQLAlchemy async
              ┌──────────▼──────────┐
              │   SQLite / PostgreSQL│
              │   15 normalized tables│
              └─────────────────────┘
```

### Data Flow

1. **Import** — CSV upload or synthetic generation → transaction records
2. **Detect** — Failed/abandoned/overdue transactions flagged as at-risk
3. **Diagnose** — Risk score calculated (0–100), failure category mapped, recoverability classified
4. **Recommend** — AI or rule engine produces structured recommendation (action + reason + evidence + confidence)
5. **Policy Check** — Deterministic engine validates recommendation against all configured rules
6. **Execute** — Allowed action is executed via payment provider adapter (simulation or Razorpay test mode)
7. **Audit** — Every state transition, policy decision, and action result is appended to the audit log
8. **Measure** — Evaluation engine calculates 20 metrics across 3 strategies

---

## Technology Stack

### Backend
- Python 3.12, FastAPI 0.115, Uvicorn
- SQLAlchemy 2.0 (async), Alembic, aiosqlite / psycopg2
- Pydantic v2, pydantic-settings
- Pandas, scikit-learn (evaluation)
- structlog, slowapi, tenacity, httpx

### Frontend
- React 18, TypeScript, Vite 5
- Tailwind CSS 3, Recharts 2
- React Router 6

### Infrastructure
- PostgreSQL 16 (production), SQLite (development)
- Docker + Docker Compose
- nginx (frontend serving + API proxy)

---

## Quick Start

### Option A: Local Development (SQLite, no Docker)

```powershell
# 1. Clone / open the project
cd "AI-Powered Revenue Recovery Agent"

# 2. Backend
cd backend
pip install -r requirements.txt
python -c "
import asyncio, sys; sys.path.insert(0,'.')
from app.core.database import init_db, engine, Base
import app.models
async def s():
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
asyncio.run(s())
"
uvicorn app.main:app --reload --port 8000

# 3. Frontend (new terminal)
cd ../frontend
npm install
npm run dev

# 4. Open http://localhost:5173
```

Or use the startup scripts:

```powershell
# Terminal 1
.\scripts\start_backend.ps1

# Terminal 2
.\scripts\start_frontend.ps1
```

### Option B: Docker Compose (PostgreSQL)

```bash
cp .env.example .env
# Edit .env with your settings
docker-compose up --build
# Open http://localhost:3000
```

### Option C: Docker Dev (SQLite, hot reload)

```bash
docker-compose -f docker-compose.dev.yml up --build
```

---

## Environment Variables

See `.env.example` for full documentation. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./recoverai.db` | Async DB URL |
| `AI_PROVIDER` | `rule_based` | `rule_based` or `openrouter` |
| `OPENROUTER_API_KEY` | _(empty)_ | OpenRouter API key (optional) |
| `PAYMENT_PROVIDER` | `simulation` | `simulation` or `razorpay_test` |
| `RAZORPAY_KEY_ID` | _(empty)_ | Razorpay test key ID (optional) |
| `RAZORPAY_KEY_SECRET` | _(empty)_ | Razorpay test secret (optional) |
| `MAX_RETRY_ATTEMPTS` | `3` | Global retry limit default |
| `APPROVAL_THRESHOLD_INR` | `50000` | Amount requiring human approval |

**Never commit `.env` to version control.**

---

## Database Schema

15 tables:

| Table | Purpose |
|-------|---------|
| `merchants` | Merchant profiles |
| `customers` | Anonymised customer references |
| `transactions` | Core transaction records |
| `checkout_sessions` | Abandoned checkout tracking |
| `subscriptions` | Recurring payment subscriptions |
| `invoices` | Overdue invoice tracking |
| `recovery_cases` | Recovery lifecycle state machine |
| `recovery_recommendations` | Structured AI/rule recommendations |
| `recovery_actions` | Executed recovery action records |
| `policy_rules` | Per-merchant policy configuration |
| `approval_records` | Human approval decisions |
| `promises_to_pay` | Promise-to-pay tracking |
| `evaluation_runs` | Evaluation experiment results |
| `evaluation_results` | Per-transaction evaluation data |
| `audit_events` | Append-only audit log |
| `batch_imports` | CSV import tracking |

All monetary values stored as `NUMERIC(18,2)` in INR (configurable currency field per record).

---

## AI Decision Process

```
Transaction → Risk Scoring → AI Provider → Policy Engine → Action
                                 ↓               ↓
                          Recommendation    ALLOWED / BLOCKED
                          (structured)      (deterministic)
```

### Rule-Based Provider (default, no API key needed)
Selects action deterministically based on failure category:
- `temp_failure` → `retry` (if retries remaining)
- `auth_required` → `request_auth`
- `insufficient_funds` → `stop`
- `fraud` → `stop`
- `unknown` → `human_review`
- `checkout` / `invoice` → `send_reminder`

### OpenRouter LLM Provider (optional)
- Receives minimal sanitised context (no PII, no credentials)
- Returns structured JSON recommendation
- Output validated against allowed action set
- Rejected/malformed responses fall back to rule-based
- All prompts treat transaction descriptions as untrusted input

**The AI never overrides a blocked policy decision.**

---

## Recovery Policy

Configurable per merchant via `/api/v1/policy`. Default rules:

| Rule | Default | ID |
|------|---------|-----|
| Max retry attempts | 3 | RETRY_001 |
| Min delay between retries | 24h | RETRY_002 |
| Max actions per transaction | 5 | ACT_001 |
| Max reminders/customer/week | 2 | COMM_001 |
| Approval threshold | ₹50,000 | — |
| Batch action limit | 500 | ACT_002 |

### Permanent Stopping Rules (cannot be disabled)
- Payment confirmed successful → STOP_001
- Fraud restriction → STOP_003
- Non-retryable failure category → STOP_004
- Cancelled subscription → STOP_005
- Disputed invoice → STOP_006 (human review only)
- Customer opted out → STOP_007

---

## CSV Format

### Required columns
`external_id`, `customer_ref`, `amount`, `currency`, `transaction_type`, `status`

### Optional columns
`failure_reason`, `failure_category`, `failure_code`, `retry_count`, `payment_method`, `gateway`, `description`, `is_synthetic`

### Valid values
- `transaction_type`: `payment` | `subscription` | `invoice` | `checkout`
- `status`: `pending` | `success` | `failed` | `abandoned` | `overdue` | `cancelled`
- `failure_category`: `temp_failure` | `insufficient_funds` | `auth_required` | `invalid_details` | `fraud` | `unknown`
- `currency`: `INR` | `USD` | `EUR` | `GBP` | `AED` | `SGD`

See `data/samples/sample_transactions.csv` for an example.

---

## Synthetic Dataset

Generate via API or UI:

```bash
curl -X POST "http://localhost:8000/api/v1/imports/generate-synthetic?count=100&seed=42"
```

**Scenarios included** (100 records, seed=42):
- 20 successful payments (paid, not at risk)
- 15 retryable temp failures (recoverable)
- 5 temp failures with exhausted retries (blocked)
- 8 insufficient funds (non-retryable)
- 7 auth-required (recoverable via request_auth)
- 5 invalid card details (non-retryable)
- 5 fraud-blocked (hard stop)
- 5 unknown failures (human review)
- 10 abandoned checkouts
- 8 failed subscriptions
- 3 cancelled subscriptions (stopped)
- 5 overdue invoices
- 2 disputed invoices (human review)
- 2 opted-out customers (communication blocked)

All records have `synthetic_ground_truth_recoverable` and `synthetic_recovery_outcome` labels for evaluation.

---

## Evaluation Methodology

Three strategies are evaluated on the **same dataset** with the **same random seed**:

1. **baseline**: No automated recovery (0 actions taken)
2. **fixed_rule**: Deterministic rule-based recovery with policy checks
3. **ai_assisted**: Risk-score-adjusted action selection with policy enforcement

### Strategy Comparison
```bash
curl -X POST "http://localhost:8000/api/v1/evaluation/run?batch_id=YOUR_BATCH_ID&seed=42"
curl "http://localhost:8000/api/v1/evaluation/compare?batch_id=YOUR_BATCH_ID"
```

### Export Results
```bash
# CSV
curl "http://localhost:8000/api/v1/evaluation/runs/RUN_ID/export?format=csv" -o report.csv

# JSON
curl "http://localhost:8000/api/v1/evaluation/runs/RUN_ID/export?format=json" -o report.json
```

---

## Metric Definitions

| # | Metric | Definition |
|---|--------|-----------|
| 1 | Total transaction count | All transactions in the dataset |
| 2 | Total transaction value | Sum of all transaction amounts |
| 3 | Eligible at-risk count | Transactions with non-null ground truth outcome |
| 4 | Total revenue at risk | Sum of at-risk transaction amounts |
| 5 | Estimated recoverable value | At-risk amount × 0.40 (conservative base rate) |
| 6 | Successful recoveries | Count where `recovery_succeeded = True` |
| 7 | Simulated recovered value | Sum of amounts for successful recoveries |
| 8 | Recovery rate by count | successful_recoveries / eligible_at_risk_count |
| 9 | Recovery rate by value | simulated_recovered_value / total_revenue_at_risk |
| 10 | Retry success rate | successful_retries / total_retry_actions |
| 11 | Action failure rate | failed_actions / eligible_at_risk_count |
| 12 | Blocked action count | Actions blocked by policy engine |
| 13 | Duplicate prevention count | Duplicate idempotency key matches |
| 14 | Human review count | Cases flagged for manual review |
| 15 | Customer contact count | send_reminder + request_auth + escalate actions |
| 16 | Estimated intervention cost | Sum of action costs (retry=₹5, reminder=₹2, auth=₹3, escalate=₹10, review=₹25) |
| 17 | Net simulated recovery | simulated_recovered_value − intervention_cost |
| 18 | False-positive interventions | Actions where ground_truth_recoverable = False |
| 19 | Results by failure category | Per-category count, recovered, value |
| 20 | Results by strategy | Cross-strategy comparison table |

**Precision** = TP / (TP + FP) — of predicted recoverable, how many were actually recoverable  
**Recall** = TP / (TP + FN) — of actually recoverable, how many were identified  
**False-positive rate** = FP / (FP + TN) — rate of intervening on non-recoverable cases

These metrics require ground-truth labels. Only valid when using synthetic data with labels.

---

## API Documentation

- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
- OpenAPI JSON: http://localhost:8000/api/openapi.json

Key endpoints:

```
GET  /api/v1/dashboard              Dashboard metrics
GET  /api/v1/transactions           Transaction list (filterable)
GET  /api/v1/transactions/{id}      Transaction detail
GET  /api/v1/transactions/{id}/audit  Audit timeline
POST /api/v1/imports/upload         Upload CSV
POST /api/v1/imports/generate-synthetic  Generate synthetic data
POST /api/v1/recovery/process/{id}  Process single transaction
POST /api/v1/recovery/process-batch Run batch recovery
GET  /api/v1/recovery/queue         Recovery case queue
POST /api/v1/recovery/{id}/approve  Approve recommendation
POST /api/v1/recovery/{id}/reject   Reject recommendation
POST /api/v1/evaluation/run         Run 3-strategy evaluation
GET  /api/v1/evaluation/compare     Strategy comparison
GET  /api/v1/audit                  Audit trail
GET  /api/v1/policy                 Policy configuration
PUT  /api/v1/policy                 Update policy
GET  /api/v1/settings               App configuration (no secrets)
GET  /health                        Health check
```

---

## Running Tests

```powershell
cd backend

# All tests
python -m pytest tests/ -v

# Unit tests only (fast, no DB)
python -m pytest tests/test_csv_import.py tests/test_policy_engine.py tests/test_risk_scoring.py tests/test_ai_provider.py -v

# Integration tests
python -m pytest tests/test_api_endpoints.py tests/test_evaluation.py -v

# With coverage
python -m pytest tests/ --cov=app --cov-report=term-missing
```

**Current status: 126/126 tests pass.**

---

## Docker Deployment

### Development (SQLite)
```bash
docker-compose -f docker-compose.dev.yml up --build
```

### Production (PostgreSQL)
```bash
cp .env.example .env
# Edit .env: set POSTGRES_PASSWORD, SECRET_KEY
docker-compose up --build -d
```

Services:
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/api/docs

---

## AWS Deployment Guide

### Recommended Architecture

```
Internet → ALB (HTTPS) → ECS Fargate
                           ├── Frontend Task (nginx + React build)
                           └── Backend Task (FastAPI + uvicorn)
                                     ↓
                              RDS PostgreSQL
                                     ↓
                           Secrets Manager (API keys)
                                     ↓
                             CloudWatch (logs)
```

### Steps

1. **Build and push images to ECR**
   ```bash
   aws ecr create-repository --repository-name recoverai-backend
   aws ecr create-repository --repository-name recoverai-frontend
   docker build -t recoverai-backend ./backend
   docker tag recoverai-backend:latest ACCOUNT.dkr.ecr.REGION.amazonaws.com/recoverai-backend
   docker push ACCOUNT.dkr.ecr.REGION.amazonaws.com/recoverai-backend
   ```

2. **Create RDS PostgreSQL** (db.t3.small minimum)

3. **Store secrets in AWS Secrets Manager**
   - `recoverai/postgres-password`
   - `recoverai/secret-key`
   - `recoverai/openrouter-api-key` (if using LLM)
   - `recoverai/razorpay-test-key` (if using Razorpay)

4. **Create ECS Fargate task definitions** — mount secrets as environment variables

5. **Application Load Balancer** — HTTPS on port 443, redirect HTTP → HTTPS

6. **CloudWatch** — configure log groups for structured JSON logs

7. **Run migrations** using an ECS one-off task:
   ```bash
   alembic upgrade head
   ```

**Do not deploy to production without:**
- HTTPS
- Strong `SECRET_KEY`
- Rotating database passwords
- VPC with private subnets for RDS

---

## Razorpay Test Mode

To enable Razorpay test-mode adapter:

1. Create a Razorpay account and get test credentials from the dashboard
2. Set in `.env`:
   ```
   PAYMENT_PROVIDER=razorpay_test
   RAZORPAY_KEY_ID=rzp_test_YOUR_KEY_ID
   RAZORPAY_KEY_SECRET=YOUR_KEY_SECRET
   ```
3. Restart the backend

**Important limitations:**
- Razorpay test mode does not support retrying existing failed payments via API
- The adapter falls back to simulation for unsupported operations
- Test credentials only — never use live credentials
- Keys are never exposed through the frontend

---

## Demo Workflow (60 seconds)

```powershell
# With backend running:
.\scripts\run_demo.ps1
```

Or manually:
1. Open http://localhost:5173
2. Click **Import & Batches** → **Generate Dataset** (count=100, seed=42)
3. Click **Recovery Agent** → select the batch → **Process Batch**
4. View **Dashboard** — metrics now populated from real DB data
5. Click any transaction → **Run Recovery Agent** → view audit timeline
6. Click **Evaluation** → **Run Evaluation** → compare 3 strategies
7. Export report as CSV

---

## Known Limitations

1. **No real payments** — all recovery is simulated by design
2. **LLM evaluation** — AI-assisted strategy uses the same deterministic logic in batch evaluation; the LLM is called per-transaction during live processing but not during evaluation runs
3. **Authentication** — no user authentication is implemented (out of scope for this demonstration)
4. **Email/SMS** — no actual communication is sent; drafts are generated but not dispatched
5. **Promise-to-pay tracking** — data model exists, UI tracking is via the recovery case state
6. **SQLite concurrent writes** — SQLite handles the demo well but use PostgreSQL for production
7. **Alembic migrations** — for local dev, tables are created directly via `init_db()`; run `alembic upgrade head` for migration-tracked deployments

---

## Security Considerations

- All secrets in environment variables, never in code
- CSV formula injection prevention on import and export
- Parameterized queries via SQLAlchemy ORM (no raw SQL)
- File size and type validation on upload
- CORS configured to explicit origins
- Rate limiting on all API endpoints
- Audit trail is append-only (no update/delete in application code)
- LLM prompts treat all external content as untrusted
- Payment credentials never exposed to frontend
- Simulation clearly distinguished from test-mode and live payments

### Production hardening checklist
- [ ] Change `SECRET_KEY` to a secure random value
- [ ] Enable HTTPS (TLS) via ALB or Caddy
- [ ] Set `APP_ENV=production` and `DEBUG=false`
- [ ] Use PostgreSQL with connection pooling
- [ ] Enable database SSL
- [ ] Configure CloudWatch alarms
- [ ] Rotate secrets regularly via Secrets Manager
- [ ] Add authentication (JWT or session-based)
- [ ] Review and restrict CORS origins

---

## Project Structure

```
AI-Powered Revenue Recovery Agent/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/    # REST API endpoints
│   │   ├── agent/               # Recovery agent + AI provider
│   │   ├── core/                # Config, database, logging, exceptions
│   │   ├── evaluation/          # Batch evaluation engine
│   │   ├── integrations/        # Payment provider adapters
│   │   ├── models/              # SQLAlchemy models (15 tables)
│   │   ├── policies/            # Deterministic policy engine
│   │   ├── schemas/             # Pydantic schemas
│   │   └── services/            # CSV import, risk scoring, synthetic data, audit
│   ├── tests/                   # 126 pytest tests
│   ├── alembic/                 # DB migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/          # Reusable UI components
│   │   ├── pages/               # 10 application pages
│   │   ├── services/            # API client
│   │   └── types/               # TypeScript types
│   ├── package.json
│   └── Dockerfile
├── data/samples/                # Sample CSV
├── scripts/                     # Startup and demo scripts
├── docker-compose.yml           # Production (PostgreSQL)
├── docker-compose.dev.yml       # Development (SQLite)
└── .env.example
```

---

*RecoverAI — Razorpay AI Buildathon 2024 · Built with FastAPI, React, and deterministic policy-first AI*
