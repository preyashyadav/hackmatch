import { Attendee, Match, ActivityItem, SignupResponse } from "./types";

export const mockAttendee: Attendee = {
  id: "att_demo_001",
  name: "Sarah Chen",
  contact_email: "sarah.chen@example.com",
  agent_email: "sarah-x7q@hackmatch.agentmail.to",
  project_idea:
    "B2B fintech infrastructure for agent-to-agent payments. Building rails so AI agents can transact autonomously with proper governance and audit trails.",
  looking_for:
    "ML infra engineers, anyone working on stablecoin rails or agent identity, B2B fintech founders",
  theme_alignment_score: 8.5,
  created_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
};

export const mockMatches: Match[] = [
  {
    match_id: "match_001",
    status: "confirmed",
    other_attendee: {
      id: "att_demo_002",
      name: "Alex Kim",
      contact_email: "alex.kim@example.com",
      project_idea:
        "Stablecoin payment rails optimized for autonomous AI agents. Sub-second settlement, agent-native KYC.",
      looking_for: "Fintech founders, payment infra people",
    },
    synergy_score: 9.1,
    theme_alignment_score: 8.8,
    overlap_reasons: [
      "Agent-to-agent payments",
      "Stablecoin infrastructure",
      "Both targeting B2B",
    ],
    potential_collaboration:
      "Sarah's payment governance layer plugs directly into Alex's settlement rails. They could prototype an end-to-end agent payment demo together by Sunday.",
    relevant_external_context:
      "Sponge (YC W26) just launched in this exact space — both should look at how they're handling agent identity. Stripe also announced agent payment APIs last week.",
    created_at: new Date(Date.now() - 1000 * 60 * 25).toISOString(),
    confirmed_at: new Date(Date.now() - 1000 * 60 * 20).toISOString(),
  },
  {
    match_id: "match_002",
    status: "proposed",
    other_attendee: {
      id: "att_demo_003",
      name: "Priya Patel",
      contact_email: "priya@example.com",
      project_idea:
        "Code review agent that maintains memory of architectural decisions across a monorepo. Uses Nia under the hood.",
      looking_for:
        "Other devtools founders, frontend engineers, anyone using AI coding agents",
    },
    synergy_score: 7.2,
    theme_alignment_score: 9.0,
    overlap_reasons: [
      "Both building agent infrastructure",
      "Both YC-track companies",
    ],
    potential_collaboration:
      "Less direct overlap, but Priya's experience with Nia indexing patterns could help Sarah think about agent memory for transactions.",
    relevant_external_context:
      "Canary (YC W26) is in the same code review space — Priya should connect with them.",
    created_at: new Date(Date.now() - 1000 * 60 * 10).toISOString(),
    confirmed_at: null,
  },
  {
    match_id: "match_003",
    status: "rejected",
    other_attendee: {
      id: "att_demo_004",
      name: "Marcus Webb",
      contact_email: "marcus@example.com",
      project_idea: "AI-powered cattle health monitoring for ranches",
      looking_for: "Agritech investors, hardware engineers",
    },
    synergy_score: 4.1,
    theme_alignment_score: 6.5,
    overlap_reasons: ["Both YC-track"],
    potential_collaboration: "Limited direct technical overlap.",
    relevant_external_context:
      "GrazeMate (YC W26) is in similar space — Marcus should connect with them, not Sarah.",
    created_at: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    confirmed_at: null,
  },
];

export const mockActivity: ActivityItem[] = [
  {
    conversation_id: "conv_001",
    match_id: "match_002",
    from_email: "priya-k4p@hackmatch.agentmail.to",
    to_email: "sarah-x7q@hackmatch.agentmail.to",
    from_name: "Priya's agent",
    to_name: "Sarah's agent",
    direction: "incoming",
    preview:
      "My human Priya is interested but wants to know more about your governance layer specifically...",
    full_body:
      "Hi Sarah's agent — my human Priya is interested but wants to know more about your governance layer specifically. Is it permissioned or permissionless? She's coming from a code review agent background and her main concern is auditability of automated actions.",
    timestamp: new Date(Date.now() - 1000 * 30).toISOString(),
    meta: { purpose: "match_response", decision: "approve" },
  },
  {
    conversation_id: "conv_002",
    match_id: "match_002",
    from_email: "sarah-x7q@hackmatch.agentmail.to",
    to_email: "priya-k4p@hackmatch.agentmail.to",
    from_name: "Sarah's agent",
    to_name: "Priya's agent",
    direction: "outgoing",
    preview:
      "My human Sarah is building agent-to-agent payment infrastructure. I think she'd benefit from meeting Priya because...",
    full_body:
      "Hi Priya's agent — my human Sarah is building agent-to-agent payment infrastructure. I think she'd benefit from meeting Priya because both of you are building agent infrastructure tools, and Priya's experience with Nia indexing could inform how Sarah handles transaction memory. Synergy score: 7.2/10. Approve?",
    timestamp: new Date(Date.now() - 1000 * 60 * 2).toISOString(),
    meta: { purpose: "match_proposal" },
  },
  {
    conversation_id: "conv_003",
    match_id: "match_001",
    from_email: "alex-z9m@hackmatch.agentmail.to",
    to_email: "sarah-x7q@hackmatch.agentmail.to",
    from_name: "Alex's agent",
    to_name: "Sarah's agent",
    direction: "incoming",
    preview:
      "Approved. Alex would love to meet Sarah — they're working on highly complementary problems...",
    full_body:
      "Approved. Alex would love to meet Sarah — they're working on highly complementary problems. Alex is building stablecoin settlement rails for agents and Sarah's governance layer is exactly what Alex's customers will need. Suggesting they meet between 2-4pm at the lounge area. Decision: APPROVE.",
    timestamp: new Date(Date.now() - 1000 * 60 * 22).toISOString(),
    meta: { purpose: "match_response", decision: "approve" },
  },
  {
    conversation_id: "conv_004",
    match_id: "match_001",
    from_email: "sarah-x7q@hackmatch.agentmail.to",
    to_email: "alex-z9m@hackmatch.agentmail.to",
    from_name: "Sarah's agent",
    to_name: "Alex's agent",
    direction: "outgoing",
    preview:
      "My human Sarah is building agent-to-agent payment infrastructure. Strong overlap with what Alex is doing...",
    full_body:
      "Hi Alex's agent — my human Sarah is building agent-to-agent payment infrastructure. Strong overlap with what Alex is doing on stablecoin rails. Synergy score: 9.1/10. Both targeting B2B agent commerce. Reasons to meet: complementary tech stack, both YC-track, shared customer profile. Approve?",
    timestamp: new Date(Date.now() - 1000 * 60 * 25).toISOString(),
    meta: { purpose: "match_proposal" },
  },
];

export const mockSignupResponse: SignupResponse = {
  attendee_id: "att_demo_001",
  agent_email: "sarah-x7q@hackmatch.agentmail.to",
};
