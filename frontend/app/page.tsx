"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { NFL_TEAMS } from "@/lib/teams";

import { ConsensusVsIntelligencePanel } from "@/components/consensus-vs-intelligence-panel";
import { LandingSpotsCard } from "@/components/landing-spots-card";
import { LiveDraftBoard } from "@/components/live-draft-board";
import { PickIntelligencePanel } from "@/components/pick-intelligence-panel";
import { PickConsensusCard } from "@/components/pick-consensus-card";
import { PlayerProbabilityPanel } from "@/components/player-probability-panel";
import { SourceAccuracyTable } from "@/components/source-accuracy-table";
import { TeamNeedProfile } from "@/components/team-need-profile";
import {
  BacktestResult,
  PickConsensusResponse,
  PlayerLandingSpotsResponse,
  getDraftOrder,
  getLiveDraftBoard,
  LiveDraftBoardResponse,
  getPickConsensus,
  getPlayerLandingSpots,
  runBacktest
} from "@/lib/api";
import {
  ConsensusVsMlResponse,
  IntelligenceModelMetadataResponse,
  PickPlayerProbsResponse,
  PositionProbabilityResponse,
  TeamNeedsResponse,
  getCompareWithConsensus,
  getModelMetadata,
  getPickPlayerProbs,
  getPickPositionProbs,
  getTeamNeeds
} from "@/lib/intelligence-api";

type OverallPredictionRow = {
  pick: number;
  player: string;
  probability: number;
  weighted_probability: number;
  sampleSize: number;
  uniqueSources: number;
  lowConfidence: boolean;
};

type MovementRow = {
  overallPick: number;
  team: string;
  prevName: string | null;
  nextName: string | null;
};

type DashboardPhase = "pre" | "live" | "post";
const DAY2_LAST_OVERALL = 102;
const FULL_DRAFT_PICKS = 257;

function normalizeNameKey(name: string | null | undefined): string {
  return String(name ?? "")
    .toLowerCase()
    .replace(/[^a-z0-9 ]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function coverageCellTone(sampleSize: number, maxSampleSize: number): string {
  if (maxSampleSize <= 0 || sampleSize <= 0) return "bg-slate-800 text-slate-300";
  const ratio = sampleSize / maxSampleSize;
  if (ratio >= 0.75) return "bg-emerald-500/80 text-emerald-50";
  if (ratio >= 0.5) return "bg-cyan-500/75 text-cyan-50";
  if (ratio >= 0.25) return "bg-amber-500/75 text-amber-50";
  return "bg-rose-500/75 text-rose-50";
}

type LiveAccuracySnapshot = {
  picksEvaluated: number;
  consensusTop1Rate: number;
  consensusTop8Rate: number;
  mlTop1Rate: number;
  mlTop5Rate: number;
};

/** First consensus candidate at this pick not already used above (no repeat names down the board). */
function buildDedupedOverallRows(
  overallResults: PromiseSettledResult<PickConsensusResponse>[]
): OverallPredictionRow[] {
  const used = new Set<string>();
  const rows: OverallPredictionRow[] = [];
  for (let idx = 0; idx < overallResults.length; idx++) {
    const result = overallResults[idx];
    if (result.status !== "fulfilled") continue;
    const payload = result.value;
    const candidates = payload.top_players;
    if (!candidates.length) continue;
    const chosen = candidates.find((p) => !used.has(p.player_name)) ?? candidates[0];
    used.add(chosen.player_name);
    const c = payload.consensus_confidence;
    rows.push({
      pick: idx + 1,
      player: chosen.player_name,
      probability: chosen.probability,
      weighted_probability: chosen.weighted_probability,
      sampleSize: c?.sample_size ?? 0,
      uniqueSources: c?.unique_sources ?? 0,
      lowConfidence: c?.low_confidence ?? true,
    });
  }
  return rows;
}

export default function DashboardPage() {
  const defaultYear = new Date().getUTCFullYear();
  const [draftYear, setDraftYear] = useState(defaultYear);
  const [team, setTeam] = useState("TEN");
  const [pick, setPick] = useState(1);
  const [loading, setLoading] = useState(false);
  const [overallPage, setOverallPage] = useState(1);
  const [pickData, setPickData] = useState<PickConsensusResponse | null>(null);
  const [landingData, setLandingData] = useState<PlayerLandingSpotsResponse | null>(null);
  const [backtestData, setBacktestData] = useState<BacktestResult[]>([]);
  const [teamNeeds, setTeamNeeds] = useState<TeamNeedsResponse | null>(null);
  const [positionProbs, setPositionProbs] = useState<PositionProbabilityResponse | null>(null);
  const [playerProbs, setPlayerProbs] = useState<PickPlayerProbsResponse | null>(null);
  const [comparison, setComparison] = useState<ConsensusVsMlResponse | null>(null);
  const [metadata, setMetadata] = useState<IntelligenceModelMetadataResponse | null>(null);
  const [overallPredictions, setOverallPredictions] = useState<OverallPredictionRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [landingFocusPlayer, setLandingFocusPlayer] = useState<string | null>(null);
  const [landingFocusPick, setLandingFocusPick] = useState<number | null>(null);
  const [landingFocusData, setLandingFocusData] = useState<PlayerLandingSpotsResponse | null>(null);
  const [landingFocusError, setLandingFocusError] = useState<string | null>(null);
  const [landingFocusLoading, setLandingFocusLoading] = useState(false);
  const [trackLiveDraft, setTrackLiveDraft] = useState(false);
  const [draftOrder, setDraftOrder] = useState<Awaited<ReturnType<typeof getDraftOrder>> | null>(null);
  const [liveBoard, setLiveBoard] = useState<LiveDraftBoardResponse | null>(null);
  const [liveCenterData, setLiveCenterData] = useState<PickConsensusResponse | null>(null);
  const [liveMlPlayers, setLiveMlPlayers] = useState<PickPlayerProbsResponse | null>(null);
  const [liveMlComparison, setLiveMlComparison] = useState<ConsensusVsMlResponse | null>(null);
  const [liveAccuracy, setLiveAccuracy] = useState<LiveAccuracySnapshot | null>(null);
  const [movementFeed, setMovementFeed] = useState<MovementRow[]>([]);
  const [phaseOverride, setPhaseOverride] = useState<DashboardPhase | "auto">("auto");
  const teamYearKeyRef = useRef<string | null>(null);
  const prevBoardRef = useRef<LiveDraftBoardResponse | null>(null);

  const focusPickInDashboard = (overallPick: number, playerName: string) => {
    setPick(overallPick);
    setLandingFocusPlayer(playerName);
    setLandingFocusPick(overallPick);
    const draftOrderTeam = draftOrder?.picks.find((p) => p.overall_pick === overallPick)?.team_abbreviation;
    if (draftOrderTeam) {
      setTeam(String(draftOrderTeam).toUpperCase());
    }
  };

  useEffect(() => {
    if (!landingFocusPlayer) {
      setLandingFocusData(null);
      setLandingFocusError(null);
      setLandingFocusLoading(false);
      return;
    }
    let cancelled = false;
    setLandingFocusData(null);
    setLandingFocusLoading(true);
    setLandingFocusError(null);
    void getPlayerLandingSpots(draftYear, landingFocusPlayer, {
      contextOverallPick: landingFocusPick ?? 1,
    })
      .then((d) => {
        if (!cancelled) setLandingFocusData(d);
      })
      .catch((e) => {
        if (!cancelled) {
          setLandingFocusData(null);
          setLandingFocusError(e instanceof Error ? e.message : "Failed to load landing spots");
        }
      })
      .finally(() => {
        if (!cancelled) setLandingFocusLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [landingFocusPlayer, landingFocusPick, draftYear]);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const key = `${draftYear}:${team}`;
        let pickForApis = pick;
        if (teamYearKeyRef.current !== key) {
          teamYearKeyRef.current = key;
          try {
            const ord = await getDraftOrder(draftYear, { team, maxOverall: FULL_DRAFT_PICKS });
            setDraftOrder(ord);
            const next = ord.next_overall_pick;
            if (next != null) {
              pickForApis = next;
              setPick(next);
            } else {
              const fp = ord.picks?.find(
                (p) => String(p.team_abbreviation ?? "").toUpperCase() === team
              )?.overall_pick;
              if (fp != null) {
                pickForApis = fp;
                setPick(fp);
              }
            }
          } catch {
            /* keep current pick if draft order missing */
          }
        } else if (!draftOrder) {
          try {
            const ord = await getDraftOrder(draftYear, { team, maxOverall: FULL_DRAFT_PICKS });
            setDraftOrder(ord);
          } catch {
            /* draft order is optional for non-live usage */
          }
        }

        const ladderTopN = 50;
        const boardOpts = { topN: ladderTopN, boardAware: trackLiveDraft };
        const ladderPickLimit = DAY2_LAST_OVERALL;
        const overallPromises = Array.from({ length: ladderPickLimit }, (_, idx) =>
          getPickConsensus(draftYear, idx + 1, boardOpts)
        );
        const overallResults = await Promise.allSettled(overallPromises);
        const rolledUp = buildDedupedOverallRows(overallResults);
        setOverallPredictions(rolledUp);
        const primaryPlayer = rolledUp[0]?.player ?? rolledUp[1]?.player ?? "";
        const landingPromise = primaryPlayer
          ? getPlayerLandingSpots(draftYear, primaryPlayer, { contextOverallPick: 1 })
          : Promise.resolve<PlayerLandingSpotsResponse>({
              draft_year: draftYear,
              player_name: "",
              top_landing_spots: [],
              updated_at: new Date().toISOString(),
              landing_confidence: null,
            });

        const results = await Promise.allSettled([
          getPickConsensus(draftYear, pickForApis, { boardAware: trackLiveDraft }),
          landingPromise,
          runBacktest(Math.max(2018, draftYear - 1)),
          getTeamNeeds(team, draftYear),
          getPickPositionProbs(team, pickForApis, draftYear),
          getPickPlayerProbs(team, pickForApis, draftYear, [], { boardAware: trackLiveDraft }),
          getCompareWithConsensus(team, pickForApis, draftYear, { boardAware: trackLiveDraft }),
          getModelMetadata(),
          trackLiveDraft
            ? getLiveDraftBoard(draftYear, { sync: true, maxOverall: FULL_DRAFT_PICKS })
            : Promise.resolve(null),
        ]);
        const [
          pickResult,
          landingResult,
          backtestResult,
          needsResult,
          posProbsResult,
          pickPlayersResult,
          cmpResult,
          mdResult,
          liveBoardResult
        ] = results;
        const failures = results.filter((r) => r.status === "rejected").length;
        if (failures > 0) {
          setError(`${failures} dashboard data sources failed to load. Showing partial results.`);
        } else {
          setError(null);
        }
        if (pickResult.status === "fulfilled") setPickData(pickResult.value);
        if (landingResult.status === "fulfilled") setLandingData(landingResult.value);
        if (backtestResult.status === "fulfilled") {
          setBacktestData(backtestResult.value.sort((a, b) => b.weighted_accuracy_score - a.weighted_accuracy_score));
        }
        if (needsResult.status === "fulfilled") setTeamNeeds(needsResult.value);
        if (posProbsResult.status === "fulfilled") setPositionProbs(posProbsResult.value);
        if (pickPlayersResult.status === "fulfilled") setPlayerProbs(pickPlayersResult.value);
        if (cmpResult.status === "fulfilled") setComparison(cmpResult.value);
        if (mdResult.status === "fulfilled") setMetadata(mdResult.value);
        if (liveBoardResult.status === "fulfilled" && liveBoardResult.value) {
          const nextBoard = liveBoardResult.value;
          const prev = prevBoardRef.current;
          if (prev) {
            const moved: MovementRow[] = [];
            for (const row of nextBoard.picks) {
              const prevRow = prev.picks.find((p) => p.overall_pick === row.overall_pick);
              if (!prevRow) continue;
              if ((prevRow.consensus_top1_name ?? null) !== (row.consensus_top1_name ?? null)) {
                moved.push({
                  overallPick: row.overall_pick,
                  team: row.team_abbreviation ?? "—",
                  prevName: prevRow.consensus_top1_name ?? null,
                  nextName: row.consensus_top1_name ?? null,
                });
              }
            }
            setMovementFeed(moved.slice(0, 8));
          }
          prevBoardRef.current = nextBoard;
          setLiveBoard(nextBoard);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown dashboard error");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [draftYear, team, pick, trackLiveDraft, draftOrder]);

  useEffect(() => {
    setOverallPage(1);
    setLandingFocusPlayer(null);
    setLandingFocusPick(null);
  }, [draftYear]);

  useEffect(() => {
    setLandingFocusPlayer(null);
    setLandingFocusPick(null);
  }, [team]);

  useEffect(() => {
    if (!trackLiveDraft) {
      setLiveCenterData(null);
      setLiveMlPlayers(null);
      setLiveMlComparison(null);
      return;
    }
    let cancelled = false;
    const syncPickFromOrder = async () => {
      try {
        const ord = await getDraftOrder(draftYear, { team, maxOverall: FULL_DRAFT_PICKS });
        if (cancelled) return;
        const next = ord.next_overall_pick;
        if (next != null) {
          setPick((prev) => (prev !== next ? next : prev));
        }
      } catch {
        /* ignore transient API errors while polling */
      }
    };
    void syncPickFromOrder();
    const id = setInterval(() => void syncPickFromOrder(), 45_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [draftYear, team, trackLiveDraft]);

  useEffect(() => {
    if (!trackLiveDraft || !liveBoard) {
      return;
    }
    const completed = liveBoard.picks.filter((p) => Boolean(p.actual_player_name));
    const latestOverall = completed.length ? Math.max(...completed.map((p) => p.overall_pick)) : 0;
    const maxBoardOverall =
      liveBoard.picks.length > 0 ? Math.max(...liveBoard.picks.map((p) => p.overall_pick)) : FULL_DRAFT_PICKS;
    const onClockOverall = Math.min(maxBoardOverall, latestOverall + 1);
    let cancelled = false;
    const loadOnClockConsensus = async () => {
      try {
        const consensus = await getPickConsensus(draftYear, onClockOverall, { topN: 8, boardAware: true });
        if (!cancelled) {
          setLiveCenterData(consensus);
        }
      } catch {
        if (!cancelled) {
          setLiveCenterData(null);
        }
      }
    };
    void loadOnClockConsensus();
    return () => {
      cancelled = true;
    };
  }, [trackLiveDraft, liveBoard, draftYear]);

  useEffect(() => {
    if (!trackLiveDraft || !liveBoard || !draftOrder) {
      setLiveAccuracy(null);
      return;
    }
    const completed = liveBoard.picks.filter((p) => Boolean(p.actual_player_name));
    const latestOverall = completed.length ? Math.max(...completed.map((p) => p.overall_pick)) : 0;
    const maxBoardOverall =
      liveBoard.picks.length > 0 ? Math.max(...liveBoard.picks.map((p) => p.overall_pick)) : FULL_DRAFT_PICKS;
    const onClockOverall = Math.min(maxBoardOverall, latestOverall + 1);
    const onClock = draftOrder.picks.find((p) => p.overall_pick === onClockOverall);
    if (!onClock?.team_abbreviation) {
      setLiveMlPlayers(null);
      setLiveMlComparison(null);
      return;
    }
    let cancelled = false;
    const loadLiveMl = async () => {
      try {
        const [players, comparison] = await Promise.all([
          getPickPlayerProbs(onClock.team_abbreviation, onClockOverall, draftYear, [], { boardAware: true }),
          getCompareWithConsensus(onClock.team_abbreviation, onClockOverall, draftYear, { boardAware: true }),
        ]);
        if (!cancelled) {
          setLiveMlPlayers(players);
          setLiveMlComparison(comparison);
        }
      } catch {
        if (!cancelled) {
          setLiveMlPlayers(null);
          setLiveMlComparison(null);
        }
      }
    };
    void loadLiveMl();
    return () => {
      cancelled = true;
    };
  }, [trackLiveDraft, liveBoard, draftOrder, draftYear]);

  useEffect(() => {
    if (!trackLiveDraft || !liveBoard) {
      setLiveAccuracy(null);
      return;
    }
    const completedRows = liveBoard.picks.filter((p) => Boolean(p.actual_player_name) && Boolean(p.team_abbreviation));
    if (!completedRows.length) {
      setLiveAccuracy(null);
      return;
    }
    let cancelled = false;
    const loadAccuracy = async () => {
      try {
        const comparisons = await Promise.all(
          completedRows.map((row) =>
            getCompareWithConsensus(String(row.team_abbreviation), row.overall_pick, draftYear, { boardAware: true })
          )
        );
        if (cancelled) return;
        let consensusTop1Hits = 0;
        let consensusTop8Hits = 0;
        let mlTop1Hits = 0;
        let mlTop5Hits = 0;
        for (let i = 0; i < completedRows.length; i++) {
          const row = completedRows[i];
          const cmp = comparisons[i];
          const actual = normalizeNameKey(row.actual_player_name);
          if (!actual) continue;
          if (row.consensus_rank_of_actual === 1) consensusTop1Hits += 1;
          if (row.consensus_rank_of_actual !== null && row.consensus_rank_of_actual > 0) consensusTop8Hits += 1;
          const mlNames = (cmp.ml_top_players ?? []).map((p) => normalizeNameKey(String(p.player_name ?? "")));
          if (mlNames[0] === actual) mlTop1Hits += 1;
          if (mlNames.slice(0, 5).includes(actual)) mlTop5Hits += 1;
        }
        const n = completedRows.length;
        setLiveAccuracy({
          picksEvaluated: n,
          consensusTop1Rate: n ? consensusTop1Hits / n : 0,
          consensusTop8Rate: n ? consensusTop8Hits / n : 0,
          mlTop1Rate: n ? mlTop1Hits / n : 0,
          mlTop5Rate: n ? mlTop5Hits / n : 0,
        });
      } catch {
        if (!cancelled) {
          setLiveAccuracy(null);
        }
      }
    };
    void loadAccuracy();
    return () => {
      cancelled = true;
    };
  }, [trackLiveDraft, liveBoard, draftYear]);

  const modelTimestamp = metadata?.models?.[0]?.training_timestamp ?? null;
  const picksPerPage = 8;
  const overallPageCount = Math.max(1, Math.ceil(overallPredictions.length / picksPerPage));
  const currentOverallRows = overallPredictions.slice((overallPage - 1) * picksPerPage, overallPage * picksPerPage);
  const maxCoverageSample = useMemo(
    () => overallPredictions.reduce((mx, row) => Math.max(mx, row.sampleSize), 0),
    [overallPredictions]
  );
  const completedRows = liveBoard?.picks.filter((p) => Boolean(p.actual_player_name)) ?? [];
  const latestCompletedOverall = completedRows.length ? Math.max(...completedRows.map((p) => p.overall_pick)) : 0;
  const currentOverall = latestCompletedOverall + 1;
  const onClockRow = draftOrder?.picks.find((p) => p.overall_pick === currentOverall) ?? null;
  const upcomingRows = (draftOrder?.picks ?? []).filter((p) => p.overall_pick >= currentOverall).slice(0, 4);
  const latestCompletedRound = completedRows.length ? Math.max(...completedRows.map((p) => p.round_number)) : 0;
  const latestRoundRows = liveBoard?.picks.filter(
    (p) => p.round_number === latestCompletedRound && Boolean(p.actual_player_name)
  ) ?? [];
  const latestRoundConsensusHits =
    latestRoundRows.length > 0
      ? latestRoundRows.filter((p) => p.consensus_rank_of_actual === 1).length / latestRoundRows.length
      : 0;
  const biggestReachRow = useMemo(() => {
    const rows = latestRoundRows.filter((p) => p.consensus_rank_of_actual !== null);
    return rows.find((p) => p.consensus_rank_of_actual === 0) ?? rows.find((p) => (p.consensus_rank_of_actual ?? 99) >= 5) ?? null;
  }, [latestRoundRows]);
  const bestValueRow = useMemo(() => {
    const rows = latestRoundRows.filter((p) => (p.consensus_rank_of_actual ?? 0) > 0);
    return rows.sort((a, b) => (a.consensus_rank_of_actual ?? 99) - (b.consensus_rank_of_actual ?? 99))[0] ?? null;
  }, [latestRoundRows]);
  const topPositions = Object.entries(positionProbs?.position_probabilities ?? {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 2);
  const draftedNameSet = new Set(
    (liveBoard?.picks ?? [])
      .filter((p) => Boolean(p.actual_player_name))
      .map((p) => normalizeNameKey(p.actual_player_name))
      .filter((n) => n.length > 0)
  );
  const scenarioBasePlayersRaw =
    liveMlPlayers?.ranked_players?.length ? liveMlPlayers.ranked_players : playerProbs?.ranked_players ?? [];
  const scenarioBasePlayers = scenarioBasePlayersRaw.filter(
    (p) => !draftedNameSet.has(normalizeNameKey(p.player_name))
  );
  const scenarioCards = topPositions.map(([position, probability]) => {
    const candidate = scenarioBasePlayers.find((p) => p.position === position) ?? scenarioBasePlayers[0];
    return { position, probability, candidate };
  });
  const inferredPhase: DashboardPhase =
    latestCompletedOverall === 0 ? "pre" : latestCompletedOverall >= FULL_DRAFT_PICKS ? "post" : "live";
  const dashboardPhase: DashboardPhase = phaseOverride === "auto" ? inferredPhase : phaseOverride;
  const showLiveCommandCenter = dashboardPhase === "live" && trackLiveDraft;
  const showOverallLadder = dashboardPhase !== "live";
  const showBacktest = dashboardPhase !== "live";
  const showDraftIntelligence = dashboardPhase !== "live";
  const transitionClass = "transition-all duration-300 ease-out";
  const expandedClass = "opacity-100 translate-y-0 max-h-[200rem]";
  const collapsedClass = "opacity-0 -translate-y-1 max-h-0 overflow-hidden pointer-events-none";

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-cyan-800/40 bg-cyan-950/20 p-4 sm:p-5">
        <h2 className="text-lg font-semibold text-cyan-100 sm:text-xl">New here? How to use DraftDay</h2>
        <p className="mt-2 text-sm text-cyan-50/90">
          This site helps you understand who might be drafted next and why. It combines crowd mock-draft consensus
          with an internal model, then shows team context so you can compare ideas quickly.
        </p>
        <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-cyan-50/90">
          <li>
            Pick a <span className="font-semibold">Year</span>, <span className="font-semibold">Team</span>, and{" "}
            <span className="font-semibold">Pick</span> in the controls below.
          </li>
          <li>
            Read <span className="font-semibold">Top Players For Pick</span> to see the leading consensus options.
          </li>
          <li>
            Check <span className="font-semibold">Likely landing spots</span> to see where a player is most often
            projected to go.
          </li>
          <li>
            Use <span className="font-semibold">Draft Intelligence</span> to compare team needs, model probabilities,
            and consensus-vs-model disagreements.
          </li>
          <li>
            If the draft is active, turn on <span className="font-semibold">Track NFL.com live draft</span> so already
            drafted players are removed from recommendations.
          </li>
        </ol>
      </section>
      <header>
        <h1 className="text-2xl font-bold sm:text-3xl">DraftDay Dashboard</h1>
        <p className="mt-2 text-slate-300">
          Use the controls to view consensus, ML, and organizational context for the current draft class.
        </p>
        <div className="mt-4 flex flex-wrap items-end gap-3 rounded-lg border border-slate-800 bg-slate-900/70 p-3">
          <label className="text-sm">
            <span className="block">Year</span>
            <input
              type="number"
              value={draftYear}
              onChange={(e) => setDraftYear(Number(e.target.value))}
              className="mt-1 w-24 rounded border border-slate-700 bg-slate-950 px-2 py-1"
            />
          </label>
          <label className="text-sm">
            <span className="block">Team</span>
            <select
              value={team}
              onChange={(e) => setTeam(e.target.value.toUpperCase())}
              className="mt-1 w-24 rounded border border-slate-700 bg-slate-950 px-2 py-1"
            >
              {NFL_TEAMS.map((abbr) => (
                <option key={abbr} value={abbr}>
                  {abbr}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="block">Pick</span>
            <input
              type="number"
              value={pick}
              onChange={(e) => setPick(Number(e.target.value))}
              className="mt-1 w-20 rounded border border-slate-700 bg-slate-950 px-2 py-1"
            />
          </label>
          {loading ? <span className="text-sm text-slate-400">Refreshing...</span> : null}
          <Link
            href={`/teams/${team}/draft-view`}
            className="w-full rounded border border-slate-600 px-3 py-1 text-center text-sm font-medium hover:bg-slate-800 sm:w-auto"
          >
            Open Team/Coach View
          </Link>
          <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-200">
            <input
              type="checkbox"
              checked={trackLiveDraft}
              onChange={(e) => setTrackLiveDraft(e.target.checked)}
              className="rounded border-slate-600"
            />
            Track NFL.com live draft
          </label>
          <label className="text-sm">
            <span className="block">Phase</span>
            <select
              value={phaseOverride}
              onChange={(e) => setPhaseOverride(e.target.value as DashboardPhase | "auto")}
              className="mt-1 rounded border border-slate-700 bg-slate-950 px-2 py-1"
            >
              <option value="auto">Auto ({inferredPhase})</option>
              <option value="pre">Pre-draft</option>
              <option value="live">Live</option>
              <option value="post">Post-round</option>
            </select>
          </label>
        </div>
        {trackLiveDraft ? (
          <p className="mt-2 text-xs text-cyan-200/90">
            Board-aware mode: consensus and the player probability model ignore prospects already drafted per the
            NFL tracker, so rankings reflect who is still on the board at each slot.
          </p>
        ) : null}
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
          <span className="rounded-full border border-emerald-700/50 bg-emerald-950/30 px-2 py-1 text-emerald-200">
            Position Model: {positionProbs?.model_version ?? "untrained"}
          </span>
          <span className="rounded-full border border-indigo-700/50 bg-indigo-950/30 px-2 py-1 text-indigo-200">
            Player Model: {playerProbs?.model_version ?? "untrained"}
          </span>
          <span className="rounded-full border border-slate-700 bg-slate-900 px-2 py-1 text-slate-300">
            Last Model Train: {modelTimestamp ? new Date(modelTimestamp).toLocaleString() : "unknown"}
          </span>
          <span className="rounded-full border border-slate-700 bg-slate-900 px-2 py-1 text-slate-300">
            Consensus Updated: {pickData?.updated_at ? new Date(pickData.updated_at).toLocaleString() : "unknown"}
          </span>
        </div>
      </header>

      {error ? <div className="rounded border border-red-600 bg-red-950/40 p-3">{error}</div> : null}

      <section
        className={`rounded-xl border border-amber-700/40 bg-amber-950/20 p-4 ${transitionClass} ${
          showLiveCommandCenter ? expandedClass : collapsedClass
        }`}
        aria-hidden={!showLiveCommandCenter}
      >
          <h2 className="text-xl font-semibold text-amber-100">Live Draft Command Center</h2>
          <p className="mt-1 text-sm text-amber-100/90">
            Real-time summary of what has happened, who is on the clock, and what consensus/ML think happens next.
          </p>
          <div className="mt-3 grid gap-3 md:grid-cols-4">
            <div className="rounded border border-amber-800/50 bg-slate-950/50 p-3">
              <div className="text-xs uppercase text-slate-400">Current Pick</div>
              <div className="mt-1 text-2xl font-bold text-amber-100">#{currentOverall}</div>
              <div className="text-xs text-slate-300">
                On clock: <span className="font-semibold">{onClockRow?.team_abbreviation ?? "—"}</span>
              </div>
            </div>
            <div className="rounded border border-amber-800/50 bg-slate-950/50 p-3">
              <div className="text-xs uppercase text-slate-400">Latest Completed Round</div>
              <div className="mt-1 text-2xl font-bold text-amber-100">{latestCompletedRound || "—"}</div>
              <div className="text-xs text-slate-300">How far through the draft we are (completed picks: {latestCompletedOverall}).</div>
            </div>
            <div className="rounded border border-amber-800/50 bg-slate-950/50 p-3">
              <div className="text-xs uppercase text-slate-400">Consensus Hit Rate</div>
              <div className="mt-1 text-2xl font-bold text-amber-100">
                {(latestRoundConsensusHits * 100).toFixed(0)}%
              </div>
              <div className="text-xs text-slate-300">Share of this round where the actual pick matched consensus #1.</div>
            </div>
            <div className="rounded border border-amber-800/50 bg-slate-950/50 p-3">
              <div className="text-xs uppercase text-slate-400">Next Teams</div>
              <div className="mt-1 text-sm text-slate-200">
                {upcomingRows.map((r) => `${r.overall_pick}:${r.team_abbreviation}`).join(" · ") || "—"}
              </div>
              <div className="mt-1 text-xs text-slate-400">Immediate upcoming slots based on current order.</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {upcomingRows.slice(0, 3).map((r) => (
                  <Link
                    key={`${r.overall_pick}-${r.team_abbreviation}`}
                    href={`/teams/${r.team_abbreviation}/draft-view`}
                    className="rounded border border-slate-600 px-2 py-0.5 text-xs text-cyan-200 hover:bg-slate-800"
                  >
                    {r.team_abbreviation} view
                  </Link>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-3 rounded border border-emerald-800/50 bg-emerald-950/20 p-3">
            <h3 className="text-sm font-semibold text-emerald-100">Overall Model Accuracy So Far</h3>
            <p className="mt-1 text-xs text-emerald-100/80">
              Running scorecard on completed picks only. Higher percentages mean better live draft fit.
            </p>
            {liveAccuracy ? (
              <div className="mt-2 grid gap-2 text-xs text-slate-200 md:grid-cols-5">
                <div className="rounded border border-slate-700 bg-slate-950/40 p-2">
                  Picks evaluated
                  <div className="mt-1 text-lg font-bold text-emerald-200">{liveAccuracy.picksEvaluated}</div>
                </div>
                <div className="rounded border border-slate-700 bg-slate-950/40 p-2">
                  Consensus top-1
                  <div className="mt-1 text-lg font-bold text-cyan-200">
                    {(liveAccuracy.consensusTop1Rate * 100).toFixed(0)}%
                  </div>
                </div>
                <div className="rounded border border-slate-700 bg-slate-950/40 p-2">
                  Consensus top-8
                  <div className="mt-1 text-lg font-bold text-cyan-200">
                    {(liveAccuracy.consensusTop8Rate * 100).toFixed(0)}%
                  </div>
                </div>
                <div className="rounded border border-slate-700 bg-slate-950/40 p-2">
                  ML top-1
                  <div className="mt-1 text-lg font-bold text-indigo-200">{(liveAccuracy.mlTop1Rate * 100).toFixed(0)}%</div>
                </div>
                <div className="rounded border border-slate-700 bg-slate-950/40 p-2">
                  ML top-5
                  <div className="mt-1 text-lg font-bold text-indigo-200">{(liveAccuracy.mlTop5Rate * 100).toFixed(0)}%</div>
                </div>
              </div>
            ) : (
              <p className="mt-2 text-xs text-slate-300">
                Waiting for enough completed picks and comparison payloads to compute live accuracy.
              </p>
            )}
          </div>

          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <div className="rounded border border-slate-800 bg-slate-900/60 p-3">
              <h3 className="text-sm font-semibold text-slate-100">Next Pick Center</h3>
              <p className="mt-1 text-xs text-slate-400">
                Board-aware consensus candidates for the current on-clock slot (already drafted players removed).
              </p>
              <div className="mt-2 space-y-1 text-sm">
                {(liveCenterData?.top_players ?? []).slice(0, 5).map((p, idx) => (
                  <div key={`${p.player_name}-${idx}`} className="flex items-center justify-between text-slate-200">
                    <span>
                      {idx + 1}. {p.player_name}
                    </span>
                    <span className="font-mono text-cyan-200">{(p.weighted_probability * 100).toFixed(1)}%</span>
                  </div>
                ))}
                {!(liveCenterData?.top_players?.length) ? (
                  <div className="text-xs text-slate-400">No on-clock board-aware consensus available yet.</div>
                ) : null}
              </div>
            </div>
            <div className="rounded border border-slate-800 bg-slate-900/60 p-3">
              <h3 className="text-sm font-semibold text-slate-100">What Changed Since Last Refresh</h3>
              <p className="mt-1 text-xs text-slate-400">
                Tracks where the top consensus candidate shifted between refreshes.
              </p>
              <div className="mt-2 space-y-1 text-xs text-slate-300">
                {movementFeed.length ? (
                  movementFeed.map((m) => (
                    <div key={`${m.overallPick}-${m.team}`}>
                      Pick {m.overallPick} ({m.team}): {m.prevName ?? "—"} →{" "}
                      <span className="text-cyan-200">{m.nextName ?? "—"}</span>
                    </div>
                  ))
                ) : (
                  <div>No top-consensus movement detected in tracked picks.</div>
                )}
              </div>
            </div>
          </div>

          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <div className="rounded border border-indigo-800/60 bg-indigo-950/20 p-3">
              <h3 className="text-sm font-semibold text-indigo-100">On-Clock ML Top 5</h3>
              <p className="mt-1 text-xs text-indigo-100/80">
                ML model ranking for the same on-clock slot shown above.
              </p>
              <div className="mt-2 space-y-1 text-xs text-slate-200">
                {(liveMlPlayers?.ranked_players ?? []).slice(0, 5).map((p, idx) => (
                  <div key={`${p.player_name}-${idx}`} className="flex items-center justify-between">
                    <span>
                      {idx + 1}. {p.player_name} ({p.position})
                    </span>
                    <span className="font-mono text-indigo-200">{(p.probability * 100).toFixed(1)}%</span>
                  </div>
                ))}
                {!(liveMlPlayers?.ranked_players?.length) ? (
                  <div className="text-slate-400">ML probabilities unavailable for on-clock slot.</div>
                ) : null}
              </div>
            </div>
            <div className="rounded border border-indigo-800/60 bg-indigo-950/20 p-3">
              <h3 className="text-sm font-semibold text-indigo-100">Consensus vs ML (On Clock)</h3>
              <p className="mt-1 text-xs text-indigo-100/80">
                Quick agreement check between crowd consensus and the ML model for this pick.
              </p>
              <div className="mt-2 space-y-1 text-xs text-slate-300">
                <div>
                  Overlap:{" "}
                  <span className="text-indigo-200">
                    {(liveMlComparison?.overlap ?? []).length
                      ? (liveMlComparison?.overlap ?? []).join(", ")
                      : "none"}
                  </span>
                </div>
                <div>
                  Disagreement score:{" "}
                  <span className="font-mono text-indigo-200">
                    {liveMlComparison ? liveMlComparison.disagreement_score.toFixed(2) : "—"}
                  </span>
                </div>
                <div>
                  Consensus #1:{" "}
                  <span className="text-cyan-200">
                    {String(liveMlComparison?.consensus_top_players?.[0]?.player_name ?? "—")}
                  </span>
                </div>
                <div>
                  ML #1:{" "}
                  <span className="text-indigo-200">
                    {String(liveMlComparison?.ml_top_players?.[0]?.player_name ?? "—")}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <div className="rounded border border-slate-800 bg-slate-900/60 p-3">
              <h3 className="text-sm font-semibold text-slate-100">Scenario Cards</h3>
              <p className="mt-1 text-xs text-slate-400">
                If the on-clock team prioritizes a top position need, this is the most likely candidate.
              </p>
              <div className="mt-2 space-y-2 text-xs text-slate-300">
                {scenarioCards.map((s) => (
                  <div key={s.position} className="rounded border border-slate-700 bg-slate-950/50 p-2">
                    If {onClockRow?.team_abbreviation ?? team} prioritizes {s.position} (
                    {(s.probability * 100).toFixed(0)}%), likely target:{" "}
                    <span className="text-cyan-200">{s.candidate?.player_name ?? "TBD"}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded border border-slate-800 bg-slate-900/60 p-3">
              <h3 className="text-sm font-semibold text-slate-100">Round Recap</h3>
              <p className="mt-1 text-xs text-slate-400">
                Early value/reach summary for picks already completed in the latest round.
              </p>
              <div className="mt-2 text-xs text-slate-300">
                {latestCompletedRound ? (
                  <>
                    <div>Round {latestCompletedRound} picks logged: {latestRoundRows.length}</div>
                    <div>
                      Best value:{" "}
                      <span className="text-emerald-200">
                        {bestValueRow?.actual_player_name ?? "N/A"}
                        {bestValueRow?.consensus_rank_of_actual
                          ? ` (consensus #${bestValueRow.consensus_rank_of_actual})`
                          : ""}
                      </span>
                    </div>
                    <div>
                      Biggest reach:{" "}
                      <span className="text-amber-200">
                        {biggestReachRow?.actual_player_name ?? "N/A"}
                        {biggestReachRow?.consensus_rank_of_actual === 0 ? " (outside top 8)" : ""}
                      </span>
                    </div>
                  </>
                ) : (
                  <div>Waiting for first official picks to generate recap cards.</div>
                )}
              </div>
            </div>
          </div>
        </section>

      <LiveDraftBoard draftYear={draftYear} enabled={trackLiveDraft} />

      <section
        className={`rounded-xl border border-slate-800 bg-slate-900/60 p-4 ${transitionClass} ${
          showOverallLadder ? expandedClass : collapsedClass
        }`}
        aria-hidden={!showOverallLadder}
      >
        <h2 className="text-xl font-semibold">
          {trackLiveDraft ? `Board-Aware Next-Up Ladder (${draftYear})` : `Overall Draft Predictions (${draftYear})`}
        </h2>
        <p className="mt-1 text-sm text-slate-300">
          {trackLiveDraft
            ? "Live mode emphasizes still-available players and near-term picks; this ladder remains useful for the upcoming block of selections."
            : "Top consensus player by pick through Day 2 (picks 1-102). Each row uses the best available pick at that slot that has not already appeared above, so the same player cannot be listed for two different picks."}
        </p>
        <p className="mt-1 text-xs text-slate-500">
          Click a row to load smoothed landing-spot odds for that player in the panel on the right.
        </p>
        <div className="mt-3 rounded border border-slate-800 bg-slate-950/50 p-3">
          <div className="flex flex-col items-start gap-2 sm:flex-row sm:items-center sm:justify-between">
            <h3 className="text-sm font-semibold text-slate-100">Day 2 Consensus Coverage Heatmap</h3>
            <span className="text-xs text-slate-400">darker/greener = more mock rows at that pick</span>
          </div>
          <div className="mt-2 grid grid-cols-12 gap-1 md:grid-cols-17">
            {overallPredictions.map((row) => (
              <button
                key={`coverage-${row.pick}`}
                type="button"
                title={`Pick ${row.pick}: n=${row.sampleSize}, top ${row.player}`}
                onClick={() => focusPickInDashboard(row.pick, row.player)}
                className={`rounded px-1.5 py-1 text-[10px] font-semibold ${coverageCellTone(
                  row.sampleSize,
                  maxCoverageSample
                )}`}
              >
                {row.pick}
              </button>
            ))}
          </div>
        </div>
        <div className="mt-3 flex items-center gap-2">
          <button
            type="button"
            onClick={() => setOverallPage((p) => Math.max(1, p - 1))}
            className="rounded border border-slate-600 px-2 py-1 text-xs hover:bg-slate-800"
          >
            Prev
          </button>
          <span className="text-xs text-slate-300">
            Page {overallPage} / {overallPageCount}
          </span>
          <button
            type="button"
            onClick={() => setOverallPage((p) => Math.min(overallPageCount, p + 1))}
            className="rounded border border-slate-600 px-2 py-1 text-xs hover:bg-slate-800"
          >
            Next
          </button>
        </div>
        <div className="mt-3 grid gap-2 md:grid-cols-2">
          {currentOverallRows.map((row) => (
            <button
              key={row.pick}
              type="button"
              onClick={() => focusPickInDashboard(row.pick, row.player)}
              className={`rounded border bg-slate-950/70 px-3 py-2 text-left text-sm transition hover:border-cyan-700/60 hover:bg-slate-900 ${
                landingFocusPlayer === row.player
                  ? "border-cyan-600 ring-1 ring-cyan-600/40"
                  : "border-slate-700"
              }`}
            >
              Pick {row.pick}: <span className="font-semibold">{row.player}</span>{" "}
              <span className="text-slate-400">
                (smoothed p={row.probability.toFixed(2)}, w={row.weighted_probability.toFixed(2)}
                {row.lowConfidence ? ` · n=${row.sampleSize} src=${row.uniqueSources}` : ""})
              </span>
            </button>
          ))}
        </div>
      </section>

      <section
        className={`rounded-xl border border-slate-800 bg-slate-900/60 p-4 ${transitionClass} ${
          showOverallLadder ? collapsedClass : expandedClass
        }`}
        aria-hidden={showOverallLadder}
      >
        <h2 className="text-xl font-semibold">Live Mode Focus</h2>
        <p className="mt-1 text-sm text-slate-300">
          The overall long-range ladder is hidden during live mode to prioritize on-the-clock outcomes and board movement.
        </p>
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        <PickConsensusCard
          data={pickData?.top_players ?? []}
          confidence={pickData?.consensus_confidence ?? null}
        />
        <div className="relative">
          {landingFocusLoading ? (
            <div className="absolute inset-0 z-10 flex items-center justify-center rounded-xl bg-slate-950/70 text-sm text-slate-300">
              Loading landing spots…
            </div>
          ) : null}
          {landingFocusError ? (
            <div className="mb-2 rounded border border-amber-800 bg-amber-950/40 p-2 text-xs text-amber-100">
              {landingFocusError}
            </div>
          ) : null}
          <LandingSpotsCard
            title={
              landingFocusPlayer
                ? `Landing spots — ${landingFocusPlayer}`
                : "Likely landing spots — #1 overall consensus"
            }
            data={
              landingFocusPlayer
                ? (landingFocusData?.top_landing_spots ?? [])
                : (landingData?.top_landing_spots ?? [])
            }
            confidence={
              landingFocusPlayer
                ? (landingFocusData?.landing_confidence ?? null)
                : (landingData?.landing_confidence ?? null)
            }
            onClearSelection={
              landingFocusPlayer
                ? () => {
                    setLandingFocusPlayer(null);
                    setLandingFocusPick(null);
                  }
                : undefined
            }
            slotContextPick={
              (landingFocusPlayer ? landingFocusData : landingData)?.context_overall_pick ?? null
            }
            slotContextRowCount={
              (landingFocusPlayer ? landingFocusData : landingData)?.mock_rows_at_context_pick ?? null
            }
            resolvedLookupName={
              (landingFocusPlayer ? landingFocusData : landingData)?.resolved_lookup_name ?? null
            }
            draftCycleTotalPickRows={
              (landingFocusPlayer ? landingFocusData : landingData)?.draft_cycle_total_pick_rows ?? null
            }
            draftCycleMockArticles={
              (landingFocusPlayer ? landingFocusData : landingData)?.draft_cycle_mock_articles ?? null
            }
          />
        </div>
      </div>

      <section
        className={`space-y-4 rounded-xl border border-indigo-700/30 bg-indigo-950/10 p-4 ${transitionClass} ${
          showDraftIntelligence ? expandedClass : collapsedClass
        }`}
        aria-hidden={!showDraftIntelligence}
      >
        <h2 className="text-2xl font-bold text-indigo-200">Draft Intelligence</h2>
        <div className="grid gap-4 md:grid-cols-2">
          <TeamNeedProfile
            team={teamNeeds?.team ?? team}
            topNeeds={teamNeeds?.top_need_positions ?? []}
            needs={teamNeeds?.needs ?? []}
          />
          <PickIntelligencePanel
            team={positionProbs?.team ?? team}
            pick={positionProbs?.overall_pick ?? pick}
            modelVersion={positionProbs?.model_version ?? "untrained"}
            probabilities={positionProbs?.position_probabilities ?? {}}
            explanation={positionProbs?.explanation_summary ?? {}}
          />
        </div>
        <PlayerProbabilityPanel
          modelVersion={playerProbs?.model_version ?? "player-heuristic-fallback-v1"}
          players={playerProbs?.ranked_players ?? []}
        />
        <ConsensusVsIntelligencePanel comparison={comparison} metadata={metadata} />
      </section>

      <section
        className={`rounded-xl border border-indigo-700/30 bg-indigo-950/10 p-4 ${transitionClass} ${
          showDraftIntelligence ? collapsedClass : expandedClass
        }`}
        aria-hidden={showDraftIntelligence}
      >
        <h2 className="text-2xl font-bold text-indigo-200">Draft Intelligence</h2>
        <p className="mt-2 text-sm text-indigo-100/80">
          Collapsed in live mode. Use Team View for deep team-specific intelligence while picks are being made.
        </p>
      </section>

      <div className={`${transitionClass} ${showBacktest ? expandedClass : collapsedClass}`} aria-hidden={!showBacktest}>
        <SourceAccuracyTable rows={backtestData} />
      </div>

      <section
        className={`rounded-xl border border-slate-800 bg-slate-900/60 p-4 ${transitionClass} ${
          showBacktest ? collapsedClass : expandedClass
        }`}
        aria-hidden={showBacktest}
      >
        <h2 className="text-lg font-semibold">Source Backtests</h2>
        <p className="mt-1 text-sm text-slate-300">
          Hidden in live mode to reduce noise. Switch phase to Pre-draft/Post-round to review source performance.
        </p>
      </section>
    </div>
  );
}
