# HackMatch

HackMatch is a hackathon matchmaking app where every attendee gets an email-native AI agent. Attendees sign up with what they’re building + what they’re looking for; the system suggests matches and runs an agent-to-agent intro negotiation over email before looping humans in.

## Architecture (HLD)

```mermaid
flowchart LR
  UI[Next.js Frontend] -->|HTTP| API[FastAPI Backend]

  API --> DB[(SQLite)]
  API --> AM[AgentMail]
  API --> OA[OpenAI Embeddings]
  API --> AN[Anthropic LLM]
  API --> NIA[Nia (optional)]

  AM -->|webhook: message.received| API
```

## Repo layout

- `frontend/` — Next.js UI (port `3000`)
- `backend/` — FastAPI API + matching + webhook receiver (port `8000`)
- `hackmatch.db` — default SQLite DB (local dev)

## Quickstart (local)

### 1) Backend

From repo root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000
```

Backend docs (endpoints + HLD/LLD diagrams): `backend/README.md`.

### 2) Frontend

From repo root (in a new terminal):

```bash
cd frontend
npm install
cp ../.env.local.example .env.local
npm run dev
```

Then open `http://localhost:3000`.

## Configuration

### Frontend env (`frontend/.env.local`)

- `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`)
- `NEXT_PUBLIC_USE_MOCK` (`true` to use local mocked API responses)

Example template: `.env.local.example`.

### Backend env (`backend/.env`)

Required for “real” flows (inboxes + matching + email negotiation):

- `AGENTMAIL_API_KEY`
- `OPENAI_API_KEY` (embeddings)
- `ANTHROPIC_API_KEY` (LLM JSON reasoning)

Optional:

- `NIA_API_KEY` (+ `NIA_API_URL`) for indexing/search augmentation
- `WEBHOOK_BASE_URL` for AgentMail webhook registration (public URL)
- `DATABASE_URL` (defaults to SQLite `sqlite:///./hackmatch.db`)
- `AGENT_DOMAIN` (custom AgentMail domain)

Example template: `backend/.env.example`.

## Common workflows

### Trigger matching for an attendee

Once you have an attendee id (returned from signup, or stored in the browser’s `localStorage` as `hackmatch_attendee_id`):

```bash
curl -sS -X POST http://localhost:8000/attendees/<attendee_id>/refresh
```

### Run the UI without the backend (mock mode)

Set `NEXT_PUBLIC_USE_MOCK=true` in `frontend/.env.local` to use local mocked responses (no backend required).

### Seed demo attendees (calls external APIs)

These scripts create/update canned attendees and will hit AgentMail/OpenAI/Anthropic (and Nia if configured):

```bash
cd backend
python seed_demo_profiles.py
python seed_personas.py
```

### Webhooks (AgentMail)

To receive real agent-to-agent emails locally you need a public tunnel and must set `WEBHOOK_BASE_URL` in `backend/.env`. Then you can repair/re-register webhooks for all existing inboxes:

```bash
cd backend
python repair_agentmail_webhooks.py
```

## Notes

- The backend CORS allowlist currently includes `http://localhost:3000` only.
- Mermaid diagrams render on GitHub; if your viewer doesn’t render Mermaid, use a Markdown viewer that supports it.
