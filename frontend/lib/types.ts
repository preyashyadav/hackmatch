export interface Attendee {
  id: string;
  name: string;
  contact_email: string;
  agent_email: string;
  project_idea: string;
  looking_for: string;
  theme_alignment_score: number;
  created_at: string;
}

export interface OtherAttendee {
  id: string;
  name: string;
  contact_email: string;
  project_idea: string;
  looking_for: string;
}

export type MatchStatus = "proposed" | "confirmed" | "rejected" | "met";

export interface Match {
  match_id: string;
  status: MatchStatus;
  other_attendee: OtherAttendee;
  synergy_score: number;
  theme_alignment_score: number;
  overlap_reasons: string[];
  potential_collaboration: string;
  relevant_external_context: string;
  created_at: string;
  confirmed_at: string | null;
}

export interface ActivityMeta {
  purpose: string;
  decision?: string;
}

export interface ActivityItem {
  conversation_id: string;
  match_id: string;
  from_email: string;
  to_email: string;
  from_name: string;
  to_name: string;
  direction: "outgoing" | "incoming";
  preview: string;
  full_body: string;
  timestamp: string;
  meta: ActivityMeta;
}

export interface SignupResponse {
  attendee_id: string;
  agent_email: string;
}

export interface SignupPayload {
  name: string;
  contact_email: string;
  project_idea: string;
  looking_for: string;
}
