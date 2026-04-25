"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { Attendee, Match, ActivityItem, SignupPayload } from "@/lib/types";
import { api } from "@/lib/api";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  if (diff < 60_000) return `${Math.floor(diff / 1000)}s ago`;
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  return `${Math.floor(diff / 3_600_000)}h ago`;
}

function scoreColor(score: number) {
  if (score >= 8) return "text-emerald-400";
  if (score >= 6) return "text-amber-400";
  return "text-red-400";
}

function statusConfig(status: string) {
  switch (status) {
    case "confirmed":
      return { label: "Confirmed", bg: "bg-emerald-500/15", text: "text-emerald-400", border: "border-emerald-500/30" };
    case "proposed":
      return { label: "Pending", bg: "bg-amber-500/15", text: "text-amber-400", border: "border-amber-500/30" };
    case "rejected":
      return { label: "Rejected", bg: "bg-red-500/15", text: "text-red-400", border: "border-red-500/30" };
    case "met":
      return { label: "Met ✓", bg: "bg-sky-500/15", text: "text-sky-400", border: "border-sky-500/30" };
    default:
      return { label: status, bg: "bg-slate-700/40", text: "text-slate-400", border: "border-slate-600/30" };
  }
}

// ─── Signup ───────────────────────────────────────────────────────────────────

function SignupPage({ onDone }: { onDone: (id: string) => void }) {
  const [form, setForm] = useState<SignupPayload>({
    name: "",
    contact_email: "",
    project_idea: "",
    looking_for: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function set(k: keyof SignupPayload) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setForm((f) => ({ ...f, [k]: e.target.value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await api.signup(form);
      localStorage.setItem("hackmatch_attendee_id", res.attendee_id);
      onDone(res.attendee_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Signup failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-16">
      {/* Logo / header */}
      <div className="mb-10 text-center">
        <div className="inline-flex items-center gap-2 mb-3">
          <span className="text-3xl">🤝</span>
          <span className="text-3xl font-bold tracking-tight text-white">HackMatch</span>
        </div>
        <p className="text-slate-400 text-sm max-w-sm">
          Tell your AI agent what you&apos;re building. It&apos;ll find the right people and make the intro.
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-8 space-y-5 shadow-2xl"
      >
        <div className="space-y-1">
          <label className="block text-xs font-medium text-slate-400 uppercase tracking-wider">
            Your name
          </label>
          <input
            required
            value={form.name}
            onChange={set("name")}
            placeholder="Sarah Chen"
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
          />
        </div>

        <div className="space-y-1">
          <label className="block text-xs font-medium text-slate-400 uppercase tracking-wider">
            Your email
          </label>
          <input
            required
            type="email"
            value={form.contact_email}
            onChange={set("contact_email")}
            placeholder="sarah@example.com"
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
          />
        </div>

        <div className="space-y-1">
          <label className="block text-xs font-medium text-slate-400 uppercase tracking-wider">
            What are you building?
          </label>
          <textarea
            required
            rows={3}
            value={form.project_idea}
            onChange={set("project_idea")}
            placeholder="B2B fintech rails for agent-to-agent payments..."
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition resize-none"
          />
        </div>

        <div className="space-y-1">
          <label className="block text-xs font-medium text-slate-400 uppercase tracking-wider">
            Who are you looking for?
          </label>
          <textarea
            required
            rows={2}
            value={form.looking_for}
            onChange={set("looking_for")}
            placeholder="ML infra engineers, stablecoin founders..."
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition resize-none"
          />
        </div>

        {error && (
          <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-2">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-lg py-2.5 text-sm transition-colors"
        >
          {loading ? "Creating your agent…" : "Find my matches →"}
        </button>
      </form>

      <p className="mt-6 text-xs text-slate-600">
        OpenClaw Hackathon · Eragon × Nozomio × AgentMail
      </p>
    </div>
  );
}

// ─── Match Card ───────────────────────────────────────────────────────────────

function MatchCard({
  match,
  onMarkMet,
}: {
  match: Match;
  onMarkMet: (id: string) => Promise<void>;
}) {
  const [expanded, setExpanded] = useState(false);
  const [marking, setMarking] = useState(false);
  const s = statusConfig(match.status);

  async function handleMarkMet() {
    setMarking(true);
    await onMarkMet(match.match_id);
    setMarking(false);
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 hover:border-slate-700 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold text-white text-sm">{match.other_attendee.name}</h3>
            <span
              className={`text-[11px] font-medium px-2 py-0.5 rounded-full border ${s.bg} ${s.text} ${s.border}`}
            >
              {s.label}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">{match.other_attendee.contact_email}</p>
        </div>
        <div className="text-right shrink-0">
          <span className={`text-2xl font-bold ${scoreColor(match.synergy_score)}`}>
            {match.synergy_score.toFixed(1)}
          </span>
          <p className="text-[10px] text-slate-500 -mt-0.5">synergy</p>
        </div>
      </div>

      {/* Project idea */}
      <p className="text-sm text-slate-300 leading-relaxed">{match.other_attendee.project_idea}</p>

      {/* Overlap reasons */}
      {match.overlap_reasons.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {match.overlap_reasons.map((r) => (
            <span
              key={r}
              className="text-[11px] bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 px-2 py-0.5 rounded-full"
            >
              {r}
            </span>
          ))}
        </div>
      )}

      {/* Expandable details */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
      >
        {expanded ? "▲ Less detail" : "▼ More detail"}
      </button>

      {expanded && (
        <div className="space-y-3 pt-1 border-t border-slate-800">
          <div>
            <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider mb-1">
              Potential collaboration
            </p>
            <p className="text-sm text-slate-300">{match.potential_collaboration}</p>
          </div>
          {match.relevant_external_context && (
            <div>
              <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider mb-1">
                External context
              </p>
              <p className="text-sm text-slate-400 italic">{match.relevant_external_context}</p>
            </div>
          )}
          <div>
            <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider mb-1">
              Looking for
            </p>
            <p className="text-sm text-slate-400">{match.other_attendee.looking_for}</p>
          </div>
        </div>
      )}

      {/* Mark as met */}
      {match.status === "confirmed" && (
        <button
          onClick={handleMarkMet}
          disabled={marking}
          className="w-full mt-1 text-sm text-emerald-400 border border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500/20 rounded-lg py-1.5 transition-colors disabled:opacity-50"
        >
          {marking ? "Marking…" : "✓ Mark as met"}
        </button>
      )}
    </div>
  );
}

// ─── Activity Feed ────────────────────────────────────────────────────────────

function ActivityFeed({ items }: { items: ActivityItem[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-40 text-slate-600 text-sm">
        <span className="text-2xl mb-2">📭</span>
        No agent activity yet
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {items.map((item) => {
        const isExpanded = expanded === item.conversation_id;
        const isIncoming = item.direction === "incoming";

        return (
          <button
            key={item.conversation_id}
            onClick={() => setExpanded(isExpanded ? null : item.conversation_id)}
            className="w-full text-left"
          >
            <div
              className={`rounded-xl border px-4 py-3 transition-colors ${
                isIncoming
                  ? "bg-slate-800/60 border-slate-700/60 hover:border-slate-600"
                  : "bg-indigo-950/40 border-indigo-900/40 hover:border-indigo-800/60"
              }`}
            >
              <div className="flex items-start gap-3">
                {/* Direction arrow */}
                <span
                  className={`shrink-0 mt-0.5 text-sm ${
                    isIncoming ? "text-sky-400" : "text-indigo-400"
                  }`}
                >
                  {isIncoming ? "↙" : "↗"}
                </span>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <p className="text-xs text-slate-400">
                      <span className="text-white font-medium">{item.from_name}</span>
                      {" → "}
                      <span>{item.to_name}</span>
                    </p>
                    <span className="text-[10px] text-slate-600 shrink-0">
                      {timeAgo(item.timestamp)}
                    </span>
                  </div>

                  <p className="text-xs text-slate-400 mt-1 truncate">
                    {isExpanded ? item.full_body : item.preview}
                  </p>

                  {/* Meta badges */}
                  <div className="flex gap-1.5 mt-2 flex-wrap">
                    {item.meta.purpose && (
                      <span className="text-[10px] bg-slate-700/60 text-slate-400 px-1.5 py-0.5 rounded">
                        {item.meta.purpose}
                      </span>
                    )}
                    {item.meta.decision && (
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded ${
                          item.meta.decision === "approve"
                            ? "bg-emerald-500/20 text-emerald-400"
                            : "bg-red-500/20 text-red-400"
                        }`}
                      >
                        {item.meta.decision}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

function Dashboard({
  attendeeId,
  onSignout,
}: {
  attendeeId: string;
  onSignout: () => void;
}) {
  const [attendee, setAttendee] = useState<Attendee | null>(null);
  const [matches, setMatches] = useState<Match[]>([]);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshMsg, setRefreshMsg] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadData = useCallback(async () => {
    const [att, mat] = await Promise.all([
      api.getAttendee(attendeeId),
      api.getMatches(attendeeId),
    ]);
    setAttendee(att);
    setMatches(mat);
  }, [attendeeId]);

  const loadActivity = useCallback(async () => {
    try {
      const act = await api.getActivity(attendeeId);
      setActivity(act);
    } catch {
      // silently ignore poll errors
    }
  }, [attendeeId]);

  useEffect(() => {
    loadData();
    loadActivity();
    pollRef.current = setInterval(loadActivity, 2000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [loadData, loadActivity]);

  async function handleRefresh() {
    setRefreshing(true);
    setRefreshMsg("");
    try {
      const res = await api.refresh(attendeeId);
      const msg = `Found ${res.matches_found} match${res.matches_found !== 1 ? "es" : ""}`;
      setRefreshMsg(msg);
      setTimeout(() => setRefreshMsg(""), 4000);
      await loadData();
    } catch {
      setRefreshMsg("Refresh failed");
      setTimeout(() => setRefreshMsg(""), 4000);
    } finally {
      setRefreshing(false);
    }
  }

  async function handleMarkMet(matchId: string) {
    await api.markMet(matchId, true);
    await loadData();
  }

  const confirmedMatches = matches.filter((m) => m.status === "confirmed");
  const proposedMatches = matches.filter((m) => m.status === "proposed");
  const otherMatches = matches.filter((m) => m.status !== "confirmed" && m.status !== "proposed");

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-slate-950/90 backdrop-blur border-b border-slate-800 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="text-xl">🤝</span>
            <span className="font-bold text-white tracking-tight">HackMatch</span>
            {attendee && (
              <>
                <span className="text-slate-700">·</span>
                <span className="text-sm text-slate-300">{attendee.name}</span>
                <span className="text-[11px] font-mono bg-slate-800 border border-slate-700 text-slate-400 px-2 py-0.5 rounded-full hidden sm:inline">
                  {attendee.agent_email}
                </span>
              </>
            )}
          </div>
          <div className="flex items-center gap-3">
            {refreshMsg && (
              <span className="text-xs text-emerald-400 hidden sm:inline">{refreshMsg}</span>
            )}
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="text-sm bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white px-4 py-1.5 rounded-lg transition-colors font-medium"
            >
              {refreshing ? "Finding…" : "Find matches"}
            </button>
            <button
              onClick={onSignout}
              className="text-xs text-slate-600 hover:text-slate-400 transition-colors"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      {/* Body */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-8 grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Left: matches */}
        <div className="lg:col-span-2 space-y-6">
          {/* Profile card */}
          {attendee && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">
                    Your pitch
                  </p>
                  <p className="text-sm text-slate-300">{attendee.project_idea}</p>
                  <p className="text-xs text-slate-500 mt-2">
                    <span className="font-medium text-slate-400">Looking for:</span>{" "}
                    {attendee.looking_for}
                  </p>
                </div>
                {attendee.theme_alignment_score > 0 && (
                  <div className="shrink-0 text-center">
                    <span className={`text-2xl font-bold ${scoreColor(attendee.theme_alignment_score)}`}>
                      {attendee.theme_alignment_score.toFixed(1)}
                    </span>
                    <p className="text-[10px] text-slate-500 -mt-0.5">theme fit</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Confirmed */}
          {confirmedMatches.length > 0 && (
            <section>
              <h2 className="text-xs font-semibold text-emerald-400 uppercase tracking-widest mb-3">
                Confirmed intros ({confirmedMatches.length})
              </h2>
              <div className="grid sm:grid-cols-2 gap-4">
                {confirmedMatches.map((m) => (
                  <MatchCard key={m.match_id} match={m} onMarkMet={handleMarkMet} />
                ))}
              </div>
            </section>
          )}

          {/* Proposed */}
          {proposedMatches.length > 0 && (
            <section>
              <h2 className="text-xs font-semibold text-amber-400 uppercase tracking-widest mb-3">
                Pending ({proposedMatches.length})
              </h2>
              <div className="grid sm:grid-cols-2 gap-4">
                {proposedMatches.map((m) => (
                  <MatchCard key={m.match_id} match={m} onMarkMet={handleMarkMet} />
                ))}
              </div>
            </section>
          )}

          {/* Other */}
          {otherMatches.length > 0 && (
            <section>
              <h2 className="text-xs font-semibold text-slate-600 uppercase tracking-widest mb-3">
                Other ({otherMatches.length})
              </h2>
              <div className="grid sm:grid-cols-2 gap-4">
                {otherMatches.map((m) => (
                  <MatchCard key={m.match_id} match={m} onMarkMet={handleMarkMet} />
                ))}
              </div>
            </section>
          )}

          {matches.length === 0 && !refreshing && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-10 text-center text-slate-500">
              <p className="text-3xl mb-3">🔍</p>
              <p className="text-sm">No matches yet. Hit &ldquo;Find matches&rdquo; to start.</p>
            </div>
          )}
        </div>

        {/* Right: activity feed */}
        <div className="lg:col-span-1">
          <div className="sticky top-[73px]">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-widest">
                Agent activity
              </h2>
              <span className="flex items-center gap-1.5 text-[10px] text-slate-600">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                live
              </span>
            </div>
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 max-h-[calc(100vh-140px)] overflow-y-auto">
              <ActivityFeed items={activity} />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

// ─── Root ─────────────────────────────────────────────────────────────────────

export default function Home() {
  const [attendeeId, setAttendeeId] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem("hackmatch_attendee_id");
    if (saved) setAttendeeId(saved);
    setReady(true);
  }, []);

  function handleSignedUp(id: string) {
    setAttendeeId(id);
  }

  function handleSignout() {
    localStorage.removeItem("hackmatch_attendee_id");
    setAttendeeId(null);
  }

  if (!ready) return null;

  if (!attendeeId) {
    return <SignupPage onDone={handleSignedUp} />;
  }

  return <Dashboard attendeeId={attendeeId} onSignout={handleSignout} />;
}
