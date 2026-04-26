# HackMatch Presentation Gist

## One-line pitch

HackMatch is a multi-agent networking system for hackathons: every attendee gets a real AI agent with its own email inbox, those agents negotiate intros on the attendee's behalf, and attendees can also talk to a Telegram concierge to sign up, find matches, and coordinate meetings.

## Problem

Hackathons are chaotic.

- People do not know who they should meet.
- Valuable collaborators miss each other.
- Networking is manual, random, and hard to scale.
- Even when good matches exist, coordinating the intro takes time.

## Our solution

We built a system where:

- every attendee gets a personal AI agent
- that agent has a real email inbox
- agents proactively reach out to other agents when a strong match is found
- recipient agents can approve or reject intros
- once both sides align, the system sends a human intro email
- attendees can also use a Telegram concierge to sign up and manage the process conversationally

## What we built

### 1. Matchmaking backend

A FastAPI backend that:

- signs up attendees
- stores profiles and embeddings
- scores candidate matches
- triggers agent-to-agent email outreach
- tracks proposal, response, confirmed, rejected, and met states
- exposes APIs for signup, refresh, matches, activity, and mark-as-met

### 2. Multi-agent email workflow

Using AgentMail, each attendee gets:

- a real inbox
- webhook-driven incoming message handling
- automated proposal emails
- automated response emails
- automated human intro emails once both sides align

This is the core "agents acting in the world" part of the project.

### 3. Nia-augmented context retrieval

We integrated Nia as an external context layer so matching is not just based on profile text.

We index:

- attendee summaries
- OpenClaw event/theme context
- AgentMail docs
- Nia docs
- YC W26 summary context

Then we retrieve relevant context during scoring, so the match rationale can reference:

- the OpenClaw theme
- sample build patterns
- relevant infrastructure/tooling context
- adjacent startup directions

### 4. OpenClaw Telegram concierge

We created a project-local OpenClaw skill that lets a user:

- sign up over Telegram
- ask for matches
- refresh matches
- view their saved profile
- mark a match as met
- coordinate follow-up outreach conversationally

This means the system is usable through both:

- backend APIs
- a real chat interface

## User flow

1. A user messages the Telegram bot.
2. The concierge asks:
   - name
   - email
   - what they are building
   - who they want to meet
3. The backend creates an attendee and provisions an agent inbox.
4. Matching runs against other attendees.
5. If a match is strong enough, one agent emails the other.
6. The other agent reviews and replies.
7. If approved, both humans get introduced by email.
8. The user can later ask the Telegram concierge to refresh matches or coordinate a meeting.

## Architecture

### Core services

- **FastAPI** for backend APIs and webhook handling
- **SQLAlchemy + SQLite** for persistence
- **AgentMail SDK** for programmable agent inboxes
- **Anthropic** for reasoning and email-writing decisions
- **OpenAI embeddings** for semantic profile representation
- **Nia REST API** for richer context retrieval
- **OpenClaw** for the Telegram concierge runtime
- **Telegram** as the user-facing chat channel

### LLM/provider split

- **OpenAI**: embeddings only
- **Anthropic**: match reasoning, agent email proposals, approvals, human intros
- **Nia**: retrieval/context augmentation, not generation

## Why this is compelling

- It is not just a matching dashboard.
- It is an autonomous networking workflow.
- The agents do real work through real email.
- The system has memory and context through Nia.
- The user interface is conversational, not form-heavy.
- It directly fits the OpenClaw theme: **build agents that act in the world**.

## Key technical challenges we solved

- provisioning one inbox per attendee
- correctly routing proposal and response emails between agents
- handling webhook-driven agent conversations reliably
- preventing duplicate matches for the same attendee pair
- preserving the true proposer in a match
- surfacing human intro emails in attendee activity
- degrading gracefully when Nia is unavailable
- connecting the backend to a Telegram concierge through OpenClaw

## Demo-ready story

### Demo script

1. Message the Telegram bot: `Hi`
2. Complete signup in chat
3. Ask: `Find me matches`
4. Show top matches returned by the concierge
5. Show that an intro email has been sent or confirmed
6. Ask: `I want to meet Frank. Set up a meeting at 4pm at booth 2`
7. Show the follow-up email landing in a real inbox

### What this proves

- conversational signup works
- backend matching works
- agent-to-agent outreach works
- webhook-driven approval flow works
- human intro emails work
- meeting coordination works

## Current state

Phases 0 through 5 are complete in working form:

- Phase 0: backend scaffold
- Phase 1: signup + attendee storage
- Phase 2: semantic matching
- Phase 3: agent-to-agent proposal and intro workflow
- Phase 4: Nia-augmented contextual reasoning
- Phase 5: OpenClaw Telegram concierge

## Short summary for a slide

HackMatch is an AI networking layer for hackathons. It gives each attendee a real agent with a real inbox, uses semantic matching plus Nia context to identify high-value collaborators, lets agents negotiate intros over email, and exposes the whole system through a Telegram concierge built with OpenClaw.
