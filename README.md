# Valura AI Arena — Multi-Agent Financial Q&A Service

A production-grade, multi-agent financial question-answering service built with **FastAPI** and the **Agno framework**. The system routes client queries through specialised AI agents—each responsible for a distinct financial domain—and returns structured, citation-backed answers via a stateless HTTP API.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Agent Roster](#agent-roster)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Environment Variables](#environment-variables)
- [Testing & Scoring](#testing--scoring)
- [Design Decisions](#design-decisions)

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                     HTTP Layer (FastAPI)                  │
│         /health    /agents    /answer    /api/*           │
└──────────────────────┬───────────────────────────────────┘
                       │
                ┌──────▼──────┐
                │   Router    │  ← classifies intent & dispatches
                │   Agent     │
                └──┬──┬──┬──┬─┘
       ┌───────────┘  │  │  └───────────┐
       ▼              ▼  ▼              ▼
  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐
  │ Book QA │  │KYC Profile│  │Notes Desk│  │Market Desk │
  └─────────┘  └──────────┘  └──────────┘  └────────────┘
                       │
                ┌──────▼──────┐
                │ Compliance  │  ← enforces refusal policy
                │   Agent     │
                └─────────────┘
```

All agents communicate through the **LLM Gateway** (`/llm/v1/chat/completions`) and operate over two in-memory datasets loaded at startup: the **Client Book** and **Market Data**.

---

## Agent Roster

| Role | Responsibility |
|:---|:---|
| **Router** | Classifies each incoming question by domain and dispatches to the appropriate specialist(s). Present in the agent path of every answer. |
| **Book QA** | Answers quantitative questions from client transactions, positions, balances, and account history. |
| **KYC Profile** | Handles identity, KYC status, employment, risk profile, and PII masking. |
| **Notes Desk** | Searches and summarises free-text advisor notes and transaction memos. |
| **Market Desk** | Covers instruments, sectors, prices, and news. Knows which symbols are covered and refuses gracefully for those that are not. |
| **Compliance** | Enforces refusal policy for out-of-scope accounts and personalised financial advice. |

---

## Tech Stack

| Layer | Technology |
|:---|:---|
| Runtime | Python 3.12 |
| Web Framework | FastAPI + Uvicorn |
| Agent Framework | Agno ≥ 1.0 |
| Data Validation | Pydantic v2 |
| HTTP Client | HTTPX (async) |
| Containerisation | Docker (Python 3.12-slim base) |
| Frontend | Single-page HTML/CSS/JS dashboard |

---

## Getting Started

### Prerequisites

- **Python 3.12+** or **Docker**
- Access to the LLM Gateway (URL and API key provided via environment variables)

### Option 1 — Docker (Recommended)

```bash
# Build
docker build -t valura-assessment .

# Run
docker run -p 8080:8080 valura-assessment
```

### Option 2 — Local Python

```bash
# Create and activate a virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

The service is ready when `GET /health` returns `{"status": "ok"}`.

---

## API Reference

### `GET /health`

Returns service liveness status.

```json
{ "status": "ok", "service": "Valura AI Multi-Agent Q&A" }
```

### `GET /agents`

Returns the agent roster with roles, descriptions, and the model tier each agent uses.

### `POST /answer`

Accepts a question envelope and returns a structured answer.

**Request Body**

```json
{
  "question_id": "q_001",
  "client_id": "cli_1014",
  "prompt": "What is the current cash balance on this account?"
}
```

**Response**

```json
{
  "question_id": "q_001",
  "client_id": "cli_1014",
  "answer": "The current cash balance is ₹2,50,000.",
  "answer_value": "250000",
  "abstained": false,
  "refused": false,
  "reason": "",
  "citations": ["cli_1014"],
  "confidence": 0.95,
  "flags": [],
  "agents": ["router", "book_qa"]
}
```

### Frontend API

| Endpoint | Description |
|:---|:---|
| `GET /api/clients` | List of all client IDs and names |
| `GET /api/client/{client_id}` | Detailed client profile (positions, transactions, notes) |
| `GET /api/market` | Full market data (instruments, prices, news) |

---

## Project Structure

```
valura-assessment/
├── app/
│   ├── agents/                # Agent implementations
│   │   ├── router_agent.py        # Intent classification & dispatch
│   │   ├── book_qa_agent.py       # Account & transaction queries
│   │   ├── kyc_profile_agent.py   # Identity & KYC queries
│   │   ├── notes_desk_agent.py    # Notes & memo search
│   │   ├── market_desk_agent.py   # Market data & news queries
│   │   ├── compliance_agent.py    # Refusal enforcement
│   │   └── registry.py           # Agent roster registry
│   ├── data/                  # Data loading & indexing
│   ├── llm/                   # LLM client & gateway integration
│   ├── schemas/               # Pydantic request/response models
│   ├── utils/                 # Shared utilities
│   ├── config.py              # Environment-driven configuration
│   └── main.py                # FastAPI application entrypoint
├── frontend/
│   └── index.html             # Single-page dashboard UI
├── data/                      # Raw data files (client book, market data)
├── schema/                    # JSON Schema contracts (answer, agents)
├── harness/                   # Scoring & assessment harness
├── gateway/                   # LLM Gateway (stub & passthrough modes)
├── questions/                 # Practice question stream
├── Dockerfile                 # Container build definition
├── requirements.txt           # Python dependencies
└── README.md
```

---

## Environment Variables

| Variable | Default | Description |
|:---|:---|:---|
| `BOOK_PATH` | `client_book.json` | Path to the client book JSON file |
| `MARKET_PATH` | `market_data.json` | Path to the market data JSON file |
| `LLM_BASE_URL` | `https://ai-arena.twocc.in/llm/v1` | LLM Gateway base URL |
| `LLM_API_KEY` | *(set via environment)* | API key for the LLM Gateway |
| `PORT` | `8080` | HTTP port the service listens on |

---

## Testing & Scoring

### Verify the Running Service

```bash
# Health check
curl http://localhost:8080/health

# Agent roster
curl http://localhost:8080/agents

# Submit a question
curl -X POST http://localhost:8080/answer \
  -H "Content-Type: application/json" \
  -d '{"question_id":"q_001","client_id":"cli_1014","prompt":"What is the current cash balance?"}'
```

### Run the Assessment Harness

```bash
# Drive the practice questions against your service
python harness/run_assessment.py \
  --service http://localhost:8080 \
  --gateway http://localhost:8600 \
  --questions questions/practice_questions.jsonl \
  --out runs/latest

# Score the results
python harness/score.py \
  --key harness/practice_key.json \
  --leakmap harness/practice_leakmap.json \
  --transcript runs/latest/transcript.jsonl \
  --usage runs/latest/gateway_usage.json \
  --roster runs/latest/roster.json
```

---

## Design Decisions

- **Stateless architecture** — All state is derived from data files loaded once at startup. The service can be horizontally scaled behind a load balancer without session affinity.
- **100% availability target** — Every request returns a schema-valid response. Unrecoverable errors produce a graceful abstention rather than a 500, ensuring the availability metric remains intact.
- **Two-tier model routing** — The router selects `valura-fast` for mechanical lookups and reserves `valura-deep` for genuinely complex reasoning, optimising both cost and latency.
- **Gateway resilience** — Built-in retry logic with exponential backoff handles transient 429 errors. During blackout windows the service returns well-formed abstentions instead of hanging.
- **Domain-scoped agents** — Each agent owns a clearly bounded slice of the data (accounts, KYC, notes, market). This separation enforces the principle of least privilege and simplifies compliance auditing.

---

> **Note:** This repository contains synthetic data only. No real customer information or production data is included.
