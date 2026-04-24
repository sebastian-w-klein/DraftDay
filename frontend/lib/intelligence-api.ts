const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type TeamNeedItem = {
  position: string;
  short_term_need_score: number;
  long_term_need_score: number;
  overall_need_score: number;
  feature_summary: Record<string, number>;
};

export type TeamNeedsResponse = {
  team: string;
  year: number;
  needs: TeamNeedItem[];
  top_need_positions: string[];
  feature_summary: TeamNeedItem[];
};

export type PositionProbabilityResponse = {
  team: string;
  year: number;
  overall_pick: number;
  model_version: string;
  position_probabilities: Record<string, number>;
  need_profile: Array<Record<string, string | number>>;
  explanation_summary: Record<string, string | number>;
};

export type PickPlayerCandidateInput = {
  player_id?: number;
  player_name: string;
  position: string;
  prospect_score: number;
  superstar_potential_score: number;
  consensus_rank?: number;
  best_available_rank?: number;
  best_rank_in_position?: number;
};

export type RankedPlayerProbability = {
  player_name: string;
  position: string;
  probability: number;
  need_component: number;
  talent_component: number;
  context_component: number;
  superstar_override_score: number;
};

export type PickPlayerProbsResponse = {
  team: string;
  pick: number;
  year: number;
  model_version: string;
  ranked_players: RankedPlayerProbability[];
  explanation_summary: Record<string, string | number>;
};

export type ConsensusVsMlResponse = {
  team: string;
  pick: number;
  year: number;
  consensus_top_players: Array<Record<string, string | number>>;
  ml_top_players: Array<Record<string, string | number>>;
  overlap: string[];
  disagreement_score: number;
  divergence_explanation: Record<string, string | number>;
};

export type ModelMetadataItem = {
  model_family: string;
  model_version: string;
  train_window: number[];
  validation_window: Array<number | null>;
  test_window: Array<number | null>;
  metrics: Record<string, string | number>;
  feature_groups: string[];
  training_timestamp: string;
};

export type IntelligenceModelMetadataResponse = {
  models: ModelMetadataItem[];
};

export async function getTeamNeeds(team: string, year: number): Promise<TeamNeedsResponse> {
  const response = await fetch(
    `${API_BASE}/api/v1/intelligence/team-needs?team=${encodeURIComponent(team)}&year=${year}`,
    { cache: "no-store" }
  );
  if (!response.ok) {
    throw new Error(`Team needs request failed: ${response.status}`);
  }
  return response.json();
}

export async function getPickPositionProbs(
  team: string,
  pick: number,
  year: number
): Promise<PositionProbabilityResponse> {
  const response = await fetch(
    `${API_BASE}/api/v1/intelligence/pick-position-probs?team=${encodeURIComponent(team)}&pick=${pick}&year=${year}`,
    { cache: "no-store" }
  );
  if (!response.ok) {
    throw new Error(`Position probability request failed: ${response.status}`);
  }
  return response.json();
}

export async function getPickPlayerProbs(
  team: string,
  pick: number,
  year: number,
  candidate_players: PickPlayerCandidateInput[] = [],
  options?: { boardAware?: boolean }
): Promise<PickPlayerProbsResponse> {
  const response = await fetch(`${API_BASE}/api/v1/intelligence/pick-player-probs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      team,
      pick,
      year,
      candidate_players,
      board_aware: Boolean(options?.boardAware),
    }),
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`Player probability request failed: ${response.status}`);
  }
  return response.json();
}

export async function getCompareWithConsensus(
  team: string,
  pick: number,
  year: number,
  options?: { boardAware?: boolean }
): Promise<ConsensusVsMlResponse> {
  const params = new URLSearchParams({
    team,
    pick: String(pick),
    year: String(year),
  });
  if (options?.boardAware) {
    params.set("board_aware", "true");
  }
  const response = await fetch(
    `${API_BASE}/api/v1/intelligence/compare-with-consensus?${params.toString()}`,
    { cache: "no-store" }
  );
  if (!response.ok) {
    throw new Error(`Consensus comparison request failed: ${response.status}`);
  }
  return response.json();
}

export async function getModelMetadata(): Promise<IntelligenceModelMetadataResponse> {
  const response = await fetch(`${API_BASE}/api/v1/intelligence/model-metadata`, {
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`Model metadata request failed: ${response.status}`);
  }
  return response.json();
}
