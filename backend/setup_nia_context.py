import asyncio
import json
from pathlib import Path

from services.nia_service import index_text, index_url


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = BASE_DIR / ".nia_sources.json"

OPENCLAW_EVENT_DESCRIPTION = """
OpenClaw Hackathon
Eragon × Nozomio × AgentMail
188 King St, Suite 402, San Francisco, CA 94107

Agenda highlights:
- 10:00 AM doors open, check-in, coffee, mingle, team formations
- 10:30 AM welcome and intros from Eragon, Nozomio, and AgentMail
- 10:45 AM kickoff, theme reveal, rules, judging criteria, and prizes
- 11:00 AM hacking begins
- 1:00 PM lunch break
- 3:30 PM midpoint check-in
- 5:00 PM final hacking sprint
- 6:00 PM submissions close and code freeze
- 6:15 PM demos begin
- 8:00 PM judging deliberation
- 8:30 PM awards announced
- 9:00 PM wrap-up, photos, networking
- 10:00 PM doors close

Theme:
"Build agents that act in the world"
"Give your agent a brain. Give it a voice."

Every team must integrate at least one of Nozomio or AgentMail as a core component.

Nozomio (Nia API):
- Context augmentation for agents
- Persistent, up-to-date knowledge from codebases, docs, papers, and the web

AgentMail:
- Email infrastructure for agents
- Programmable inboxes
- Two-way threading
- Semantic search
- Real-time webhooks

Sample build ideas using AgentMail:
- Customer support agent that reads, triages, and auto-replies to inbound emails
- Scheduling agent that handles back-and-forth email negotiation
- Invoice processing agent that extracts structured data from attachments
- OTP and verification agent that automates account sign-up flows

Sample build ideas using Nozomio:
- Coding agent with persistent memory of a codebase
- Research agent that indexes docs and papers with full context
- Onboarding agent that ingests an internal wiki and answers employee questions
- PR review agent that understands code history and architectural decisions

Judging criteria:
- Integration depth: is Nozomio or AgentMail central to the build?
- Technical execution: robustness, decision-making quality, UX, and performance
- Problem and impact: is the problem real and worth solving?
- Creativity and originality: unique angle, unexpected use case, or novel tool combination

Judges:
- Josh, Eragon Founder
- Nick, Eragon Founding Engineer
- Dave, Eragon COO
- Michael, AgentMail Co-Founder
- Arlan, Nozomio Founder
"""

YC_W26_BATCH_INFO = """
YC Winter 2026 context summary:

- Y Combinator's Winter 2026 batch took place from January to March 2026 in San Francisco.
- Demo Day for the Winter 2026 batch was scheduled for March 24, 2026.
- YC encouraged investors and builders to track companies through Launch YC and the Startup Directory as new startups launched throughout the batch.

For HackMatch, treat YC W26 as secondary context rather than the primary frame.
The main purpose of this source is to provide broader startup and product analogs
for agent infrastructure, workflow automation, developer tools, vertical AI, and
AI-native business software. Matching should prioritize OpenClaw's theme
"agents that act in the world" over generic startup similarity.
"""


async def main() -> None:
    if OUTPUT_PATH.exists():
        try:
            source_map = json.loads(OUTPUT_PATH.read_text())
        except json.JSONDecodeError:
            source_map = {}
    else:
        source_map = {}

    async def ensure_text(key: str, name: str, content: str) -> None:
        if source_map.get(key):
            print(f"Skipping {key}; already indexed as {source_map[key]}")
            return
        print(f"Indexing {key}...")
        source_map[key] = await index_text(content, name=name)
        OUTPUT_PATH.write_text(json.dumps(source_map, indent=2))
        print(f"Indexed {key} -> {source_map[key]}")

    async def ensure_url(key: str, url: str, name: str | None = None) -> None:
        if source_map.get(key):
            print(f"Skipping {key}; already indexed as {source_map[key]}")
            return
        print(f"Indexing {key} from {url}...")
        source_map[key] = await index_url(url, name=name)
        OUTPUT_PATH.write_text(json.dumps(source_map, indent=2))
        print(f"Indexed {key} -> {source_map[key]}")

    await ensure_text("event_doc", "openclaw_event_doc", OPENCLAW_EVENT_DESCRIPTION.strip())
    await ensure_text("yc_w26", "yc_w26_batch_info", YC_W26_BATCH_INFO.strip())
    await ensure_url("agentmail_docs", "https://docs.agentmail.to", name="AgentMail Docs")
    await ensure_url("nia_docs", "https://docs.trynia.ai", name="Nia Docs")

    OUTPUT_PATH.write_text(json.dumps(source_map, indent=2))
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
