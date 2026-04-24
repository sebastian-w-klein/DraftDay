"use client";

import { useEffect, useState } from "react";
import { getLiveDraftBoard, type LiveDraftBoardResponse } from "@/lib/api";

const FULL_DRAFT_PICKS = 257;

function rankLabel(rank: number | null): string {
  if (rank === null) return "—";
  if (rank === 0) return "Not in top 8";
  if (rank === 1) return "Top consensus";
  return `#${rank} consensus`;
}

export function LiveDraftBoard({
  draftYear,
  enabled
}: {
  draftYear: number;
  enabled: boolean;
}) {
  const [data, setData] = useState<LiveDraftBoardResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!enabled) {
      setData(null);
      setErr(null);
      return;
    }
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setErr(null);
      try {
        const res = await getLiveDraftBoard(draftYear, { sync: true, maxOverall: FULL_DRAFT_PICKS });
        if (!cancelled) {
          setData(res);
        }
      } catch (e) {
        if (!cancelled) {
          setErr(e instanceof Error ? e.message : "Live draft failed");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };
    void load();
    const id = setInterval(() => void load(), 45_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [draftYear, enabled]);

  if (!enabled) {
    return null;
  }

  return (
    <section className="rounded-xl border border-cyan-800/40 bg-slate-900/60 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-xl font-semibold text-cyan-100">Live draft vs consensus</h2>
          <p className="mt-1 text-sm text-slate-300">
            Official picks from{" "}
            <a
              href="https://www.nfl.com/draft/tracker"
              className="text-cyan-300 underline hover:text-cyan-200"
              target="_blank"
              rel="noreferrer"
            >
              nfl.com/draft/tracker
            </a>{" "}
            (embedded payload), compared to your mock consensus. Player names use the same normalized keys as
            mocks.
          </p>
        </div>
        {loading ? <span className="text-xs text-slate-400">Syncing…</span> : null}
      </div>
      {err ? <div className="mt-2 rounded border border-red-700 bg-red-950/40 p-2 text-sm text-red-100">{err}</div> : null}
      {data ? (
        <p className="mt-2 text-xs text-slate-500">
          Last built: {new Date(data.updated_at).toLocaleString()}
          {data.synced_from_source ? " · refreshed from NFL.com" : " · database only"}
        </p>
      ) : null}
      {data && !err ? (
        <div className="mt-3 max-h-[28rem] overflow-auto rounded border border-slate-800">
          <table className="w-full min-w-[42rem] border-collapse text-left text-sm">
            <thead className="sticky top-0 bg-slate-950/95 text-xs uppercase text-slate-400">
              <tr>
                <th className="border-b border-slate-800 px-2 py-2">Pk</th>
                <th className="border-b border-slate-800 px-2 py-2">Tm</th>
                <th className="border-b border-slate-800 px-2 py-2">Actual</th>
                <th className="border-b border-slate-800 px-2 py-2">Consensus #1</th>
                <th className="border-b border-slate-800 px-2 py-2">w.p.</th>
                <th className="border-b border-slate-800 px-2 py-2">Match</th>
              </tr>
            </thead>
            <tbody>
              {data.picks.map((row) => (
                <tr key={row.overall_pick} className="border-b border-slate-800/80 hover:bg-slate-900/80">
                  <td className="px-2 py-1.5 font-mono text-slate-200">{row.overall_pick}</td>
                  <td className="px-2 py-1.5 text-slate-200">{row.team_abbreviation ?? "—"}</td>
                  <td className="px-2 py-1.5 text-slate-100">{row.actual_player_name ?? "—"}</td>
                  <td className="px-2 py-1.5 text-slate-300">{row.consensus_top1_name ?? "—"}</td>
                  <td className="px-2 py-1.5 text-slate-400">
                    {row.consensus_top1_weighted_probability != null
                      ? `${(row.consensus_top1_weighted_probability * 100).toFixed(1)}%`
                      : "—"}
                  </td>
                  <td className="px-2 py-1.5 text-xs text-cyan-200/90">{rankLabel(row.consensus_rank_of_actual)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
