const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type TeamViewOrgProfileResponse = {
  team: string;
  year: number;
  gm_profile: Record<string, unknown> | null;
  hc_profile: Record<string, unknown> | null;
  regime_stability_score: number;
  historical_tendency_metrics: Record<string, number>;
  favored_positions_groups: Record<string, string[]>;
};

export type TeamViewHistoryResponse = {
  team: string;
  year: number;
  lookback_years: number;
  recent_draft_history: Array<Record<string, unknown>>;
  early_round_picks: Array<Record<string, unknown>>;
  position_distributions: Record<string, number>;
  need_alignment_summary: Record<string, number>;
};

export type TeamViewPositionProbsResponse = {
  team: string;
  year: number;
  pick: number;
  base_ml_position_probabilities: Record<string, number>;
  org_adjusted_position_probabilities: Record<string, number>;
  delta_by_position: Record<string, number>;
  team_snapshot: Record<string, unknown>;
};

export type TeamViewPlayerCandidateInput = {
  player_id?: number;
  player_name: string;
  position: string;
  prospect_score: number;
  superstar_potential_score: number;
  consensus_rank?: number;
  best_available_rank?: number;
  best_rank_in_position?: number;
};

export type TeamViewPlayerProbsResponse = {
  team: string;
  year: number;
  pick: number;
  ranked_players: Array<{
    player_name: string;
    position: string;
    base_probability: number;
    org_adjusted_probability: number;
    need_component: number;
    talent_component: number;
    context_component: number;
    organizational_component: number;
  }>;
  integrated_explanation: string;
};

export type TeamViewSummaryResponse = {
  team: string;
  year: number;
  pick: number;
  team_snapshot: Record<string, unknown>;
  org_summary: Record<string, unknown>;
  consensus_top_players: Array<Record<string, string | number>>;
  ml_top_players: Array<Record<string, string | number>>;
  org_adjusted_top_players: Array<Record<string, string | number>>;
  top_position_predictions: Record<string, number>;
  integrated_explanation: string;
};

export type TeamViewBacktestResponse = {
  train_window: number[];
  eval_window: number[];
  comparison: Record<string, Record<string, number>>;
};

export type TeamViewDraftContextResponse = {
  team: string;
  year: number;
  latest_completed_round: number;
  team_next_overall_pick: number | null;
  team_next_round: number | null;
};

export async function getTeamViewOrgProfile(team: string, year: number): Promise<TeamViewOrgProfileResponse> {
  const response = await fetch(
    `${API_BASE}/api/v1/team-view/org-profile?team=${encodeURIComponent(team)}&year=${year}`,
    { cache: "no-store" }
  );
  if (!response.ok) throw new Error(`Org profile request failed: ${response.status}`);
  return response.json();
}

export async function getTeamViewHistory(
  team: string,
  year: number,
  lookbackYears = 5
): Promise<TeamViewHistoryResponse> {
  const response = await fetch(
    `${API_BASE}/api/v1/team-view/history?team=${encodeURIComponent(team)}&year=${year}&lookback_years=${lookbackYears}`,
    { cache: "no-store" }
  );
  if (!response.ok) throw new Error(`Team history request failed: ${response.status}`);
  return response.json();
}

export async function getTeamViewPositionProbs(
  team: string,
  year: number,
  pick: number
): Promise<TeamViewPositionProbsResponse> {
  const response = await fetch(
    `${API_BASE}/api/v1/team-view/position-probs?team=${encodeURIComponent(team)}&year=${year}&pick=${pick}`,
    { cache: "no-store" }
  );
  if (!response.ok) throw new Error(`Team view position probs request failed: ${response.status}`);
  return response.json();
}

export async function getTeamViewPlayerProbs(
  team: string,
  year: number,
  pick: number,
  candidate_players: TeamViewPlayerCandidateInput[] = [],
  options?: { boardAware?: boolean }
): Promise<TeamViewPlayerProbsResponse> {
  const response = await fetch(`${API_BASE}/api/v1/team-view/player-probs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      team,
      year,
      pick,
      candidate_players,
      board_aware: Boolean(options?.boardAware),
    }),
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`Team view player probs request failed: ${response.status}`);
  return response.json();
}

export async function getTeamViewSummary(
  team: string,
  year: number,
  pick: number,
  options?: { boardAware?: boolean }
): Promise<TeamViewSummaryResponse> {
  const params = new URLSearchParams({
    team,
    year: String(year),
    pick: String(pick),
  });
  if (options?.boardAware) {
    params.set("board_aware", "true");
  }
  const response = await fetch(`${API_BASE}/api/v1/team-view/summary?${params.toString()}`, {
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`Team view summary request failed: ${response.status}`);
  return response.json();
}

export async function getTeamViewBacktest(): Promise<TeamViewBacktestResponse> {
  const response = await fetch(`${API_BASE}/api/v1/team-view/backtest`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Team view backtest request failed: ${response.status}`);
  return response.json();
}

export async function getTeamViewDraftContext(team: string, year: number): Promise<TeamViewDraftContextResponse> {
  const response = await fetch(
    `${API_BASE}/api/v1/team-view/draft-context?team=${encodeURIComponent(team)}&year=${year}`,
    { cache: "no-store" }
  );
  if (!response.ok) throw new Error(`Team view draft context request failed: ${response.status}`);
  return response.json();
}
