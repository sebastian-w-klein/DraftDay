import { getApiBaseUrl } from "./api-base";

export type PickProbability = {
  player_name: string;
  probability: number;
  weighted_probability: number;
  raw_probability?: number | null;
  raw_weighted_probability?: number | null;
};

export type ConsensusConfidence = {
  sample_size: number;
  unique_sources: number;
  unique_articles: number;
  smoothing_alpha: number;
  category_count: number;
  other_bucket_probability: number;
  low_confidence: boolean;
};

export type PickConsensusResponse = {
  draft_year: number;
  overall_pick: number;
  top_players: PickProbability[];
  updated_at: string;
  consensus_confidence?: ConsensusConfidence | null;
  board_aware?: boolean;
  mock_rows_excluded?: number | null;
};

export type PlayerLandingSpot = {
  team: string;
  probability: number;
  raw_probability?: number | null;
};

export type LandingConfidence = {
  sample_size: number;
  unique_teams: number;
  unique_sources: number;
  unique_articles: number;
  smoothing_alpha: number;
  category_count: number;
  other_bucket_probability: number;
  low_confidence: boolean;
};

export type PlayerLandingSpotsResponse = {
  draft_year: number;
  player_name: string;
  top_landing_spots: PlayerLandingSpot[];
  updated_at: string;
  landing_confidence?: LandingConfidence | null;
  resolved_lookup_name?: string | null;
  context_overall_pick?: number | null;
  mock_rows_at_context_pick?: number | null;
  draft_cycle_total_pick_rows?: number | null;
  draft_cycle_mock_articles?: number | null;
};

export type DraftOrderPick = {
  overall_pick: number;
  round_number: number;
  team_abbreviation: string;
  source_name: string;
};

export type DraftOrderResponse = {
  draft_year: number;
  picks: DraftOrderPick[];
  /** Present when ``team`` was passed to ``getDraftOrder`` */
  resolved_team?: string;
  /** Next round-1 overall for that team with no actual pick yet (trade-aware). */
  next_overall_pick?: number | null;
};

export type BacktestResult = {
  source_slug: string;
  exact_pick_hits: number;
  player_team_hits: number;
  round1_player_hits: number;
  avg_pick_distance: number;
  weighted_accuracy_score: number;
};

export async function getPickConsensus(
  draftYear: number,
  overallPick: number,
  options?: { topN?: number; boardAware?: boolean }
): Promise<PickConsensusResponse> {
  const API_BASE = getApiBaseUrl();
  const params = new URLSearchParams();
  if (options?.topN != null) {
    params.set("top_n", String(options.topN));
  }
  if (options?.boardAware) {
    params.set("board_aware", "true");
  }
  const q = params.toString();
  const response = await fetch(
    `${API_BASE}/v1/consensus/picks/${draftYear}/${overallPick}${q ? `?${q}` : ""}`,
    { cache: "no-store" }
  );
  if (!response.ok) {
    throw new Error(`Consensus request failed: ${response.status}`);
  }
  return response.json();
}

export async function getPlayerLandingSpots(
  draftYear: number,
  playerName: string,
  options?: { contextOverallPick?: number }
): Promise<PlayerLandingSpotsResponse> {
  const API_BASE = getApiBaseUrl();
  const params = new URLSearchParams();
  if (options?.contextOverallPick != null) {
    params.set("context_overall_pick", String(options.contextOverallPick));
  }
  const q = params.toString();
  const url = `${API_BASE}/v1/consensus/players/${draftYear}/${encodeURIComponent(playerName)}${
    q ? `?${q}` : ""
  }`;
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Landing spots request failed: ${response.status}`);
  }
  return response.json();
}

export async function getDraftOrder(
  draftYear: number,
  options?: { team?: string; maxOverall?: number }
): Promise<DraftOrderResponse> {
  const API_BASE = getApiBaseUrl();
  const params = new URLSearchParams();
  if (options?.team) {
    params.set("team", options.team);
  }
  if (options?.maxOverall != null) {
    params.set("max_overall", String(options.maxOverall));
  }
  const q = params.toString();
  const response = await fetch(`${API_BASE}/v1/draft-order/${draftYear}${q ? `?${q}` : ""}`, {
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`Draft order request failed: ${response.status}`);
  }
  return response.json();
}

export type LiveDraftPickRow = {
  overall_pick: number;
  round_number: number;
  team_abbreviation: string | null;
  actual_player_name: string | null;
  consensus_top1_name: string | null;
  consensus_top1_weighted_probability: number | null;
  consensus_rank_of_actual: number | null;
};

export type LiveDraftBoardResponse = {
  draft_year: number;
  source: string;
  synced_from_source: boolean;
  picks: LiveDraftPickRow[];
  updated_at: string;
};

export async function getLiveDraftBoard(
  draftYear: number,
  options?: { sync?: boolean; maxOverall?: number }
): Promise<LiveDraftBoardResponse> {
  const API_BASE = getApiBaseUrl();
  const params = new URLSearchParams();
  if (options?.sync) {
    params.set("sync", "true");
  }
  if (options?.maxOverall != null) {
    params.set("max_overall", String(options.maxOverall));
  }
  const q = params.toString();
  const url = `${API_BASE}/v1/live-draft/${draftYear}${q ? `?${q}` : ""}`;
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Live draft request failed: ${response.status}`);
  }
  return response.json();
}

export async function runBacktest(draftYear: number): Promise<BacktestResult[]> {
  const API_BASE = getApiBaseUrl();
  const response = await fetch(`${API_BASE}/v1/analytics/backtest/${draftYear}`, {
    method: "POST",
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`Backtest request failed: ${response.status}`);
  }
  return response.json();
}
