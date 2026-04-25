import type { Attendee, Match, ActivityItem, SignupResponse, SignupPayload } from "./types";
import {
  mockAttendee,
  mockMatches,
  mockActivity,
  mockSignupResponse,
} from "./mockData";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  async signup(payload: SignupPayload): Promise<SignupResponse> {
    if (USE_MOCK) return mockSignupResponse;
    return apiFetch<SignupResponse>("/signup", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async getAttendee(id: string): Promise<Attendee> {
    if (USE_MOCK) return mockAttendee;
    return apiFetch<Attendee>(`/attendees/${id}`);
  },

  async getMatches(id: string): Promise<Match[]> {
    if (USE_MOCK) return mockMatches;
    return apiFetch<Match[]>(`/attendees/${id}/matches`);
  },

  async getActivity(id: string): Promise<ActivityItem[]> {
    if (USE_MOCK) return mockActivity;
    return apiFetch<ActivityItem[]>(`/attendees/${id}/activity`);
  },

  async markMet(matchId: string, met: boolean): Promise<void> {
    if (USE_MOCK) return;
    await apiFetch(`/matches/${matchId}/met`, {
      method: "POST",
      body: JSON.stringify({ met }),
    });
  },

  async refresh(attendeeId: string): Promise<{ ok: boolean; matches_found: number }> {
    if (USE_MOCK) return { ok: true, matches_found: 2 };
    return apiFetch(`/attendees/${attendeeId}/refresh`, { method: "POST" });
  },
};
