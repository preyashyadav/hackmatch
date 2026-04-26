# HackMatch Backend

FastAPI backend for HackMatch, a multi-agent networking system for hackathons.

## What it does

- signs up attendees
- provisions an AgentMail inbox per attendee
- computes candidate matches with embeddings + LLM reasoning
- augments match context with Nia
- runs agent-to-agent intro proposals over email
- exposes attendee activity and match status
- supports an OpenClaw Telegram concierge through the same backend APIs

## Main endpoints

- `POST /signup`
- `GET /attendees/{id}`
- `GET /attendees/{id}/matches`
- `GET /attendees/{id}/activity`
- `POST /attendees/{id}/refresh`
- `POST /matches/{id}/met`
- `POST /webhook/agentmail`
- `GET /health`

## Local run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Environment

Copy `.env.example` to `.env` and fill in:

- `AGENTMAIL_API_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `NIA_API_KEY` if using Nia indexing/search
- `WEBHOOK_BASE_URL` for AgentMail webhooks
- `TELEGRAM_BOT_TOKEN` if using the OpenClaw concierge

## Useful scripts

- `python setup_nia_context.py`
- `python repair_agentmail_webhooks.py`
- `python seed_personas.py`
- `python seed_demo_profiles.py`
