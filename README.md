# 🛡️ AI-OpsPilot

> **AI-powered IT Operations Platform** – Log ingestion · Anomaly detection · LLM incident analysis · RAG runbook retrieval · Guided remediation

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Streamlit Frontend  (dashboard.py)                             │
│  ↕ httpx  →  FastAPI /api/v1                                    │
├─────────────────────────────────────────────────────────────────┤
│  FastAPI Backend                                                 │
│  ├── Log Parser          ─→ structured log dicts                │
│  ├── Anomaly Detector    ─→ Isolation Forest (scikit-learn)     │
│  ├── Event Correlator    ─→ rule-based incident creation        │
│  ├── LLM Analyzer        ─→ Ollama (llama3) + RAG              │
│  ├── RAG Retriever       ─→ ChromaDB + sentence-transformers    │
│  ├── Remediation         ─→ suggestion + approval + execution   │
│  └── LangGraph Workflow  ─→ ingest→detect→correlate→analyse     │
├─────────────────────────────────────────────────────────────────┤
│  PostgreSQL  │  ChromaDB (vector store)  │  Ollama (LLM)        │
└─────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer      | Technology                      | Responsibility                              |
|------------|---------------------------------|---------------------------------------------|
| Frontend   | Streamlit, Plotly               | Dashboard, incident investigation, approvals |
| Backend    | FastAPI, Pydantic v2            | API endpoints, validation, business logic    |
| AI/ML      | scikit-learn, Ollama            | Anomaly detection, incident analysis         |
| RAG        | Sentence Transformers, ChromaDB | Retrieve relevant troubleshooting runbooks   |
| Workflow   | LangGraph, LangChain            | Multi-stage investigation pipeline           |
| Database   | PostgreSQL, SQLAlchemy, Alembic | Persistent application records & migrations  |
| Testing    | Pytest, HTTPX                   | Unit, async, and API integration tests       |
| Deployment | Docker Compose, GitHub Actions  | Local services and CI testing                |

---

## Quick Start

### Prerequisites
- Docker Desktop (or Docker + Docker Compose)
- [Ollama](https://ollama.com) running locally with the `llama3` model

```bash
# Pull llama3 model (one-time)
ollama pull llama3
```

### 1. Clone & configure

```bash
git clone https://github.com/prachipadole/ai-opspilot.git
cd ai-opspilot
cp .env.example .env          # edit as needed
```

### 2. Start all services

```bash
docker compose up --build
```

| Service    | URL                        |
|------------|----------------------------|
| Dashboard  | http://localhost:8501       |
| API docs   | http://localhost:8000/docs  |
| ReDoc      | http://localhost:8000/redoc |
| ChromaDB   | http://localhost:8001       |

### 3. Index runbooks into ChromaDB

```bash
# In a separate terminal (backend must be running)
curl -X POST http://localhost:8000/api/v1/analysis \
  -H "Content-Type: application/json" \
  -d '{"incident_id": "<any-valid-uuid>"}'
```

Or via the Python REPL:
```python
from backend.app.services.retriever import get_retriever
get_retriever().index_runbooks("knowledge_base/sample_runbooks")
```

---

## Running Locally (without Docker)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start PostgreSQL & ChromaDB (docker compose services only)
docker compose up db chromadb -d

# 3. Run backend
uvicorn backend.app.main:app --reload --port 8000

# 4. Run frontend (separate terminal)
streamlit run frontend/dashboard.py
```

---

## Running Tests

```bash
# Unit tests only (no backend needed)
pytest tests/ -v -k "not TestAPI"

# All tests (requires running backend)
pytest tests/ -v
```

---

## Project Structure

```
ai-opspilot/
├── frontend/
│   ├── dashboard.py            # Streamlit dashboard (6 pages)
│   └── api_client.py           # Typed HTTP client
├── backend/app/
│   ├── main.py                 # FastAPI app + lifespan
│   ├── config.py               # Pydantic settings
│   ├── database.py             # Async SQLAlchemy engine
│   ├── models/models.py        # ORM models
│   ├── schemas/schemas.py      # Pydantic schemas
│   ├── repositories/           # Async CRUD repositories
│   ├── services/
│   │   ├── log_parser.py       # Multi-format log parser
│   │   ├── anomaly_detector.py # Isolation Forest
│   │   ├── event_correlator.py # Rule-based correlation
│   │   ├── retriever.py        # ChromaDB RAG
│   │   ├── llm_analyzer.py     # Ollama + RAG analysis
│   │   └── remediation_simulator.py
│   ├── api/routes/             # FastAPI routers
│   └── workflows/
│       └── investigation_workflow.py  # LangGraph pipeline
├── database/
│   ├── init.sql                # PostgreSQL bootstrap
│   └── migrations/env.py       # Alembic environment
├── knowledge_base/sample_runbooks/   # Markdown runbooks (indexed by RAG)
├── sample_data/sample_logs.json
├── tests/test_all.py
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## Key API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/v1/health` | Health check |
| `POST` | `/api/v1/logs/ingest` | Ingest log batch |
| `GET`  | `/api/v1/logs/recent` | Recent log stream |
| `POST` | `/api/v1/incidents` | Create incident |
| `GET`  | `/api/v1/incidents` | List incidents |
| `POST` | `/api/v1/incidents/{id}/investigate` | Run LangGraph investigation |
| `GET`  | `/api/v1/anomalies` | List anomalies |
| `POST` | `/api/v1/anomalies/{id}/acknowledge` | Acknowledge anomaly |
| `POST` | `/api/v1/analysis` | Trigger LLM analysis |
| `GET`  | `/api/v1/remediation/actions` | Action catalogue |
| `POST` | `/api/v1/remediation/suggest/{id}` | AI-suggested remediations |
| `POST` | `/api/v1/remediation/{id}/approve` | Approve remediation |
| `POST` | `/api/v1/remediation/{id}/execute` | Execute (dry-run safe) |

---

## Environment Variables

See [`.env.example`](.env.example) for the full list. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `llama3` | Ollama model to use |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server |
| `DATABASE_URL` | `postgresql+asyncpg://...` | Async PostgreSQL URL |
| `ANOMALY_CONTAMINATION` | `0.05` | IsolationForest contamination ratio |

---

## License
MIT
