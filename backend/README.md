# HackMatch Backend

FastAPI backend for HackMatch: it signs up attendees, provisions an AgentMail inbox per attendee, generates candidate matches (embeddings + LLM scoring), and runs an agent-to-agent email negotiation loop before sending humans an intro.

## How it works (HLD)

```mermaid
flowchart LR
  FE[Frontend (localhost:3000)] -->|HTTP| API[FastAPI Backend]

  API --> DB[(SQLite via SQLAlchemy)]
  API --> AM[AgentMail API]
  API --> OA[OpenAI Embeddings]
  API --> AN[Anthropic LLM]
  API --> NIA[Nia API (optional)]

  AM -->|webhook: message.received| API
```

### Core ideas

- Every attendee gets an **AgentMail inbox** (`Attendee.inbox_id` + `Attendee.agent_email`).
- Matching is a two-step pipeline:
  1) retrieve candidates via **embedding cosine similarity** (OpenAI embeddings)
  2) filter/score via **LLM JSON evaluation** (Anthropic) and store a `Match`
- For good matches, the backend sends a **proposal email** from one attendee agent to the other.
- AgentMail webhooks drive the **negotiation loop** and (on approval) trigger a **human intro email** to both `contact_email`s.

## Data model (LLD)

```mermaid
erDiagram
  ATTENDEES {
    string id PK
    string name
    string contact_email
    string agent_email "unique"
    string inbox_id "unique"
    text project_idea
    text looking_for
    text embedding "json list[float]"
    float theme_alignment_score
    string nia_source_id "nullable"
    bool is_persona
    datetime created_at
  }

  MATCHES {
    string id PK
    string attendee_a_id FK
    string attendee_b_id FK
    string proposer_attendee_id FK
    string pair_key "unique, canonical a:b"
    string status "proposed|confirmed|rejected|met"
    float synergy_score
    float theme_alignment_score
    float theme_alignment_a_score
    float theme_alignment_b_score
    text overlap_reasons "json list[str]"
    text potential_collaboration
    text relevant_external_context
    text agent_conversation "json list[entries]"
    datetime created_at
    datetime confirmed_at "nullable"
  }

  ATTENDEES ||--o{ MATCHES : "attendee_a_id"
  ATTENDEES ||--o{ MATCHES : "attendee_b_id"
  ATTENDEES ||--o{ MATCHES : "proposer_attendee_id"
```

## Key flows (LLD)

### Signup

`POST /signup` provisions an inbox, stores the attendee row, optionally registers a webhook, and optionally indexes the attendee in Nia.

```mermaid
sequenceDiagram
  autonumber
  participant C as Client
  participant API as FastAPI
  participant AM as AgentMail
  participant OA as OpenAI
  participant DB as SQLite
  participant NIA as Nia (optional)

  C->>API: POST /signup {name, contact_email, project_idea, looking_for}
  API->>AM: create inbox (username hint + optional domain)
  API->>OA: embed(project_idea + looking_for)
  API->>DB: INSERT attendees(...)
  API->>AM: register webhook (if WEBHOOK_BASE_URL set)
  API->>AM: send welcome email to contact_email
  API-->>C: {attendee_id, agent_email}
  API->>NIA: index_text(profile summary) (best-effort)
  API->>DB: UPDATE attendees.nia_source_id (best-effort)
```

### Matching refresh

`POST /attendees/{id}/refresh` computes up to 5 embedding-nearest candidates, calls an LLM JSON scorer, persists matches (deduped via `pair_key`), then emails proposals for newly created matches.

```mermaid
sequenceDiagram
  autonumber
  participant C as Client
  participant API as FastAPI
  participant DB as SQLite
  participant AN as Anthropic
  participant NIA as Nia (optional)
  participant AM as AgentMail

  C->>API: POST /attendees/{id}/refresh
  API->>DB: Load attendee + other attendees + existing matches
  loop top-k candidates
    API->>AN: score_synergy JSON (optionally with Nia snippets)
    API->>NIA: search(...) (optional, when sources exist)
    API->>DB: INSERT matches(...) (if synergy_score >= 6)
  end
  API->>DB: UPDATE attendees.theme_alignment_score
  loop new matches
    API->>AM: send proposal email (purpose=match_proposal)
    API->>DB: append entry in matches.agent_conversation
  end
  API-->>C: {ok:true, matches_found:n}
```

### Agent negotiation loop (via AgentMail webhook)

Agent-to-agent emails are tagged with a `---HACKMATCH-META---` block containing `purpose` + `match_id` (see `utils/email_format.py`).

```mermaid
sequenceDiagram
  autonumber
  participant AM as AgentMail
  participant API as FastAPI
  participant DB as SQLite
  participant AN as Anthropic

  AM->>API: POST /webhook/agentmail (message.received)
  API->>DB: Load recipient attendee by inbox_id
  API->>DB: Load sender attendee by agent_email
  API->>DB: Load match + participants by match_id

  alt purpose = match_proposal
    API->>AN: evaluate_proposal JSON (approve/reject/negotiate)
    API->>AM: send match_response email (meta.decision + optional questions)
    API->>DB: append conversation entries + commit
  else purpose = match_response
    alt decision = negotiate
      API->>AM: send match_followup email (bounded rounds)
      API->>DB: append conversation entries + commit
    else decision = approve
      API->>AM: send human intro email to both contact emails
      API->>DB: mark match confirmed + confirmed_at + commit
    else decision = reject
      API->>DB: mark match rejected + commit
    end
  else purpose = match_followup
    API->>AN: evaluate_followup JSON (approve/reject)
    API->>AM: send match_response email
    API->>DB: append conversation entries + commit
  end
```

## API surface

- `GET /health` → `{ "ok": true }`
- `POST /signup` → creates attendee + AgentMail inbox
- `GET /attendees/{attendee_id}` → attendee details
- `POST /attendees/{attendee_id}/refresh` → computes new matches + sends proposals
- `GET /attendees/{attendee_id}/matches` → list of matches (sorted by synergy score)
- `GET /attendees/{attendee_id}/activity` → email activity derived from `Match.agent_conversation`
- `POST /matches/{match_id}/met` → mark a match as met
- `POST /webhook/agentmail` → AgentMail webhook receiver (async background processing)

## Local development

### 1) Install and run

From `backend/`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

If running from repo root, use:

```bash
uvicorn backend.main:app --reload --port 8000
```

### 2) Configure env

Copy `backend/.env.example` → `backend/.env`.

Required for core flows:

- `AGENTMAIL_API_KEY` (provision inboxes + send email + webhooks)
- `OPENAI_API_KEY` (embeddings)
- `ANTHROPIC_API_KEY` (LLM reasoning)

Optional:

- `NIA_API_KEY` (+ `NIA_API_URL`) to index/search context for richer match scoring
- `DATABASE_URL` (defaults to `sqlite:///./hackmatch.db`)
- `WEBHOOK_BASE_URL` (public URL that AgentMail can hit for webhooks)
- `AGENT_DOMAIN` (non-default AgentMail domain; defaults to `agentmail.to`)

## Webhook setup (AgentMail)

To receive `message.received` events locally, you need a public URL that forwards to the backend.

- Set `WEBHOOK_BASE_URL` to your tunnel base (e.g. ngrok)
- The backend registers webhooks pointing to: `WEBHOOK_BASE_URL + /webhook/agentmail`
- Re-register existing attendees/inboxes via:

```bash
python repair_agentmail_webhooks.py
```

## Nia context bootstrap (optional)

This repo can index a few shared sources (event description + external docs) and store the resulting source IDs in `backend/.nia_sources.json`. The matching service reads this file best-effort.

```bash
python setup_nia_context.py
```

## Seeding demo attendees

Creates (or updates) a set of seeded attendee profiles and ensures webhooks + Nia indexing best-effort.

```bash
python seed_demo_profiles.py
```

## Seeding persona attendees (via API)

Signs up a larger set of canned “persona” attendees by calling the running backend (`BACKEND_BASE_URL`, default `http://localhost:8000`) and then marks those rows as `is_persona=true`.

```bash
python seed_personas.py
```

## Notes / gotchas

- CORS is currently configured to allow `http://localhost:3000` only (`backend/main.py`).
- `backend/routes/webhooks.py` currently ignores human-to-agent emails (non-agent senders) and only processes agent-to-agent negotiation emails.
