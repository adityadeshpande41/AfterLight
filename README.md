# AfterLight

**Operational risk intelligence for bars, nightclubs, and live-event venues.**

AfterLight turns messy incident reports into a documented risk improvement record. Venue managers capture what happened; AI agents analyze patterns, search approved playbooks, and draft corrective action plans; human risk managers review and approve before anything reaches the venue.

🔗 **Live Demo:** [afterlight-te7r.onrender.com](https://afterlight-te7r.onrender.com)

---

## What It Does

AfterLight has two products in one platform:

### AfterLight Venue (for venue managers)
- Report incidents in natural language (AI extracts structured records)
- Upload evidence: photos, footage, statements, documents
- Track corrective actions and complete them with proof
- Monitor a deterministic Savings Score that improves as gaps close
- Ask the AI copilot: "What's missing?" "Why did my score change?"

### AfterLight Console (for internal risk team)
- View a portfolio of venues with scores and trends
- Run multi-agent AI analysis on incidents
- Review and approve AI-drafted mitigation plans
- Generate underwriting posture drafts with cited sources
- Inspect agent execution traces for transparency

---

## Who It's For

| User | Problem | AfterLight Solution |
|------|---------|-------------------|
| **Venue Manager** | Incidents happen fast, documentation is inconsistent, insurance costs rise | Structured capture, AI-assisted reporting, clear action tracking |
| **Risk Manager** | Manually reviewing incident reports across multiple venues is slow | AI agents pre-analyze cases, draft plans with citations, surface what needs attention |
| **Underwriter** | Assessing venue operational risk requires sifting through scattered records | Structured posture drafts grounded in documented operational data |

---

## Architecture

```
┌──────────────────┐         ┌────────────────────────────────────┐
│  React Frontend  │  HTTPS  │         FastAPI Backend             │
│  (Static Site)   │────────▶│                                    │
│                  │         │  15 API endpoints                  │
│  TypeScript      │◀────────│  Pydantic v2 schemas               │
│  Tailwind CSS    │         │  SQLAlchemy 2.0 async              │
│  React Query     │         │  LangGraph workflows               │
│  Recharts        │         │  OpenAI (gpt-4o-mini)              │
└──────────────────┘         └──────────┬───────────────────┬─────┘
                                        │                   │
                             ┌──────────▼──────────┐  ┌─────▼──────┐
                             │  PostgreSQL 16       │  │  OpenAI    │
                             │  + pgvector          │  │  API       │
                             │                      │  │            │
                             │  8 tables            │  │  Chat      │
                             │  Vector embeddings   │  │  Extraction│
                             │  RAG retrieval       │  │  Agents    │
                             └─────────────────────┘  └────────────┘
```

### Multi-Agent Workflows (LangGraph)

```
INCIDENT CASE WORKFLOW:

  load_data
      │
      ├──── evidence_agent (deterministic)     ──┐  parallel
      └──── pattern_agent (LLM + SQL tools)    ──┘
                    │
            playbook_agent (LLM + RAG tools)
                    │
            mitigation_agent (LLM structured output)
                    │
                validator (deterministic)
                    │
              valid? ─── no ──▶ retry with feedback (max 1)
                │
              END → human review queue
```

**Agents have tools.** They don't follow a script. The Pattern Agent decides what SQL queries to run. The Playbook Agent decides what topics to search. The LLM reasons about what information it needs.

**Tools available to agents:**
- `query_incidents_by_venue(venue_id, days)`
- `query_incidents_by_location(venue_id, keyword)`
- `query_incidents_by_time_window(venue_id, start_hour, end_hour)`
- `get_action_completion_stats(venue_id)`
- `search_playbooks(query, top_k)` — pgvector cosine similarity

---

## Core Principles

1. **Source of truth is Postgres** — canonical facts are persisted before AI work begins
2. **Deterministic scoring** — the Savings Score is calculated by a versioned Python formula, never by an LLM
3. **Human-in-the-loop** — AI drafts, humans decide. No plan reaches a venue without risk manager approval
4. **LLMs are bounded** — structured extraction, classification, grounded drafting only. Never invent facts
5. **Citations required** — every agent finding and action plan item cites its source (playbook section, incident record, or evidence item)
6. **Guardrails** — off-topic detection, prompt injection blocking, legal/medical refusal, output safety checks

---

## Scoring Formula

```python
RiskIndex = min(100,
    baseline_exposure              # venue size
    + incident_severity_recency    # recent severe incidents weigh more
    + evidence_gap                 # (100 - completeness%) × 0.25
    + open_action_gap              # open_ratio × 20
    + repeat_pattern_risk          # +10 if pattern detected
    - verified_control_credit      # -4 per completed action (max -20)
)

SavingsScore = max(0, 100 - RiskIndex)
```

Recalculates automatically when actions are completed or evidence is uploaded. Every snapshot stores factor-level breakdown.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS v4, shadcn/ui, Recharts, React Query, wouter |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), Alembic |
| Database | PostgreSQL 16 + pgvector |
| AI/ML | OpenAI (gpt-4o-mini, text-embedding-3-small), LangGraph |
| Object Storage | S3-compatible (MinIO locally, AWS S3 production) |
| Deployment | Render (Docker backend, Static frontend, Managed Postgres) |

---

## Local Development

### Prerequisites
- Docker (for Postgres + Redis + MinIO)
- Node.js 20+ and pnpm
- Python 3.11+
- OpenAI API key

### Setup

```bash
# Clone
git clone https://github.com/adityadeshpande41/AfterLight.git
cd AfterLight

# Start infrastructure
docker compose up -d

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env  # Add your OpenAI key
alembic upgrade head
python seed.py
python seed_playbooks.py

# Frontend
cd ../frontend
pnpm install
pnpm dev
```

Backend runs on `localhost:8000`, frontend on `localhost:5173`.

---

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/health | Health check |
| GET | /api/venues | List venues with scores |
| GET | /api/venues/:id/incidents | Venue incidents |
| GET | /api/venues/:id/score/history | Score trend |
| GET | /api/venues/:id/actions | Corrective actions |
| GET | /api/venues/:id/evidence | Evidence items |
| POST | /api/venues/:id/incidents | Create incident |
| POST | /api/extract | AI incident extraction |
| PATCH | /api/actions/:id | Update action status |
| POST | /api/uploads/request-url | Presigned S3 upload URL |
| POST | /api/chat | Risk Copilot |
| POST | /api/workflows/incidents/:id/analyze | Run AI analysis |
| POST | /api/underwriting/venues/:id/generate | Generate underwriting draft |
| POST | /api/decisions | Approve/reject plans |
| GET | /api/playbooks | List playbook content |
| GET | /api/agent-runs | Workflow audit trail |

Full OpenAPI docs at `/api/docs`.

---

## Project Structure

```
AfterLight/
├── frontend/                    React + Vite app
│   ├── src/
│   │   ├── pages/              Venue.tsx, Console.tsx, Public.tsx
│   │   ├── components/         AppShell, shadcn/ui
│   │   ├── hooks/              use-demo, use-workflow, use-api
│   │   └── lib/                api.ts (typed API client)
│   └── public/
├── backend/                    FastAPI + Python
│   ├── app/
│   │   ├── api/                Route modules (15 endpoints)
│   │   ├── models/             SQLAlchemy ORM (8 tables)
│   │   ├── schemas/            Pydantic request/response
│   │   ├── services/           Scoring, copilot, embeddings, storage
│   │   └── workflows/          LangGraph orchestration
│   │       ├── incident_case.py    Main workflow graph
│   │       ├── underwriting.py     Underwriting workflow
│   │       ├── agents/             Individual agent nodes
│   │       ├── tools/              SQL + RAG callable tools
│   │       └── tracing.py          Execution trace recording
│   ├── migrations/             Alembic
│   ├── seed.py                 Demo data
│   └── seed_playbooks.py       Playbook embeddings
├── docker-compose.yml          Postgres + Redis + MinIO
└── render.yaml                 Production deployment config
```

---

## License

Private repository. All rights reserved.
