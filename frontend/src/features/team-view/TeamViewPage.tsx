"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  TeamViewBacktestResponse,
  TeamViewDraftContextResponse,
  TeamViewHistoryResponse,
  TeamViewOrgProfileResponse,
  TeamViewPlayerProbsResponse,
  TeamViewPositionProbsResponse,
  TeamViewSummaryResponse,
  getTeamViewBacktest,
  getTeamViewDraftContext,
  getTeamViewHistory,
  getTeamViewOrgProfile,
  getTeamViewPlayerProbs,
  getTeamViewPositionProbs,
  getTeamViewSummary,
} from "@/lib/team-view-api";
import { DraftHistoryPanel } from "./DraftHistoryPanel";
import { ExplanationPanel } from "./ExplanationPanel";
import { NeedProfilePanel } from "./NeedProfilePanel";
import { OrgTendenciesPanel } from "./OrgTendenciesPanel";
import { PredictionPanel } from "./PredictionPanel";
import { TeamSnapshotCard } from "./TeamSnapshotCard";

export function TeamViewPage({ teamId }: { teamId: string }) {
  const team = teamId.toUpperCase();
  const [year, setYear] = useState(new Date().getUTCFullYear());
  const [pick, setPick] = useState(1);
  const [draftRound, setDraftRound] = useState(1);
  const [draftContext, setDraftContext] = useState<TeamViewDraftContextResponse | null>(null);
  const [org, setOrg] = useState<TeamViewOrgProfileResponse | null>(null);
  const [history, setHistory] = useState<TeamViewHistoryResponse | null>(null);
  const [position, setPosition] = useState<TeamViewPositionProbsResponse | null>(null);
  const [players, setPlayers] = useState<TeamViewPlayerProbsResponse | null>(null);
  const [summary, setSummary] = useState<TeamViewSummaryResponse | null>(null);
  const [backtest, setBacktest] = useState<TeamViewBacktestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [trackLiveBoard, setTrackLiveBoard] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const boardOpts = { boardAware: trackLiveBoard };
      const ctx = await getTeamViewDraftContext(team, year);
      setDraftContext(ctx);
      setDraftRound(ctx.latest_completed_round);
      const pickForLoad =
        trackLiveBoard && ctx.team_next_overall_pick != null ? ctx.team_next_overall_pick : pick;
      if (pickForLoad !== pick) {
        setPick(pickForLoad);
      }
      const summarySeed = await getTeamViewSummary(team, year, pickForLoad, boardOpts);
      const results = await Promise.allSettled([
        getTeamViewOrgProfile(team, year),
        getTeamViewHistory(team, year, 5),
        getTeamViewPositionProbs(team, year, pickForLoad),
        getTeamViewPlayerProbs(team, year, pickForLoad, [], boardOpts),
        Promise.resolve(summarySeed),
        getTeamViewBacktest(),
      ]);
      const [orgResult, historyResult, positionResult, playerResult, summaryResult, backtestResult] = results;
      const failures = results.filter((r) => r.status === "rejected");
      if (failures.length > 0) {
        setError(`${failures.length} Team View data sources failed to load. Showing partial results.`);
      }
      if (orgResult.status === "fulfilled") setOrg(orgResult.value);
      if (historyResult.status === "fulfilled") setHistory(historyResult.value);
      if (positionResult.status === "fulfilled") setPosition(positionResult.value);
      if (playerResult.status === "fulfilled") setPlayers(playerResult.value);
      if (summaryResult.status === "fulfilled") setSummary(summaryResult.value);
      if (backtestResult.status === "fulfilled") setBacktest(backtestResult.value);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Team view failed to load");
    } finally {
      setLoading(false);
    }
  }, [team, year, pick, trackLiveBoard]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!trackLiveBoard) {
      return;
    }
    const id = setInterval(() => void load(), 45_000);
    return () => clearInterval(id);
  }, [trackLiveBoard, load]);

  const explanation = useMemo(() => {
    if (!summary) return "Loading integrated explanation...";
    return summary.integrated_explanation;
  }, [summary]);

  const components = useMemo(() => {
    const topPlayer = players?.ranked_players?.[0];
    if (!topPlayer) {
      return {
        need_component: 0,
        talent_component: 0,
        context_component: 0,
        organizational_component: 0,
      };
    }
    return {
      need_component: topPlayer.need_component,
      talent_component: topPlayer.talent_component,
      context_component: topPlayer.context_component,
      organizational_component: topPlayer.organizational_component,
    };
  }, [players]);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold sm:text-3xl">Team View: {team}</h1>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="rounded-full border border-amber-700/50 bg-amber-950/30 px-2 py-1 text-amber-200">
          Latest Completed Round: {draftRound}
        </span>
        {draftContext?.team_next_round != null ? (
          <span className="rounded-full border border-amber-700/50 bg-amber-950/30 px-2 py-1 text-amber-200">
            Team Next Round: {draftContext.team_next_round}
          </span>
        ) : null}
        <span className="rounded-full border border-slate-700 bg-slate-900 px-2 py-1 text-slate-300">
          GM: {String(position?.team_snapshot?.gm ?? "unknown")}
        </span>
        <span className="rounded-full border border-slate-700 bg-slate-900 px-2 py-1 text-slate-300">
          HC: {String(position?.team_snapshot?.head_coach ?? "unknown")}
        </span>
        <span className="rounded-full border border-emerald-700/50 bg-emerald-950/30 px-2 py-1 text-emerald-200">
          Position Model: {Object.keys(position?.org_adjusted_position_probabilities ?? {}).length > 0 ? "loaded" : "fallback"}
        </span>
        <span className="rounded-full border border-indigo-700/50 bg-indigo-950/30 px-2 py-1 text-indigo-200">
          Player Model: {players?.ranked_players?.length ? "loaded" : "fallback"}
        </span>
        <span className="rounded-full border border-cyan-700/50 bg-cyan-950/30 px-2 py-1 text-cyan-200">
          Regime Stability: {Number(org?.regime_stability_score ?? 0).toFixed(2)}
        </span>
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm">
          <span className="block">Year</span>
          <input
            className="mt-1 w-24 rounded border border-slate-700 bg-slate-900 px-2 py-1"
            type="number"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
          />
        </label>
        <label className="text-sm">
          <span className="block">Pick</span>
          <input
            className="mt-1 w-20 rounded border border-slate-700 bg-slate-900 px-2 py-1"
            type="number"
            value={pick}
            onChange={(e) => setPick(Number(e.target.value))}
          />
        </label>
        <button
          className="rounded bg-indigo-700 px-3 py-1 text-sm font-semibold hover:bg-indigo-600"
          onClick={() => void load()}
          type="button"
        >
          Refresh
        </button>
        <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-200">
          <input
            type="checkbox"
            checked={trackLiveBoard}
            onChange={(e) => setTrackLiveBoard(e.target.checked)}
            className="rounded border-slate-600"
          />
          Live board (refresh predictions as picks are recorded)
        </label>
      </div>
      {trackLiveBoard ? (
        <p className="text-xs text-cyan-200/90">
          Player probabilities and summary consensus exclude everyone already drafted before this pick number. This page
          rechecks every 45 seconds while the box is checked (sync live picks from your usual NFL tracker workflow so the
          list stays accurate).
        </p>
      ) : null}
      {loading ? <div className="rounded border border-slate-700 bg-slate-900/50 p-3 text-sm">Loading Team View data...</div> : null}
      {error ? <div className="rounded border border-red-700 bg-red-950/40 p-3">{error}</div> : null}
      <div className="grid gap-4 md:grid-cols-2">
        <TeamSnapshotCard
          teamName={String(position?.team_snapshot?.team_name ?? team)}
          gm={((position?.team_snapshot?.gm as string | null) ?? (org?.gm_profile?.name as string | null) ?? null)}
          hc={((position?.team_snapshot?.head_coach as string | null) ?? (org?.hc_profile?.name as string | null) ?? null)}
          currentPicks={((position?.team_snapshot?.current_draft_picks as number[] | undefined) ?? [])}
          topNeeds={(position?.team_snapshot?.top_needs as Array<{ position: string; overall_need_score: number }> | undefined) ?? []}
        />
        <NeedProfilePanel
          needs={((position?.team_snapshot?.top_needs as Array<{ position: string; overall_need_score: number }> | undefined) ?? [])}
        />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <OrgTendenciesPanel
          metrics={org?.historical_tendency_metrics ?? {}}
          regimeStability={org?.regime_stability_score ?? 0}
        />
        <PredictionPanel
          base={position?.base_ml_position_probabilities ?? {}}
          adjusted={position?.org_adjusted_position_probabilities ?? {}}
          delta={position?.delta_by_position ?? {}}
          players={players?.ranked_players ?? []}
        />
      </div>
      <ExplanationPanel text={explanation} components={components} />
      <DraftHistoryPanel rows={history?.recent_draft_history ?? []} />
      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <h2 className="text-lg font-semibold">Org Intelligence Backtest Snapshot</h2>
        {(backtest?.comparison ? Object.entries(backtest.comparison) : []).map(([model, metrics]) => (
          <div key={model} className="mt-2 text-sm text-slate-300">
            {model}: log_loss {Number(metrics.log_loss ?? 0).toFixed(3)}, top1{" "}
            {Number(metrics.top1_accuracy ?? 0).toFixed(3)}, top3 {Number(metrics.top3_accuracy ?? 0).toFixed(3)}
          </div>
        ))}
      </section>
    </div>
  );
}
