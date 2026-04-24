import { ConsensusVsMlResponse, IntelligenceModelMetadataResponse } from "@/lib/intelligence-api";

type Props = {
  comparison: ConsensusVsMlResponse | null;
  metadata: IntelligenceModelMetadataResponse | null;
};

export function ConsensusVsIntelligencePanel({ comparison, metadata }: Props) {
  return (
    <section className="rounded-xl border border-indigo-800/40 bg-slate-900/60 p-4">
      <h2 className="mb-2 text-lg font-semibold">Consensus vs Intelligence</h2>
      <div className="mb-3 text-sm text-slate-300">
        Disagreement score: {(comparison?.disagreement_score ?? 0).toFixed(2)}
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <div>
          <div className="mb-1 text-sm font-semibold">Consensus Top</div>
          {(comparison?.consensus_top_players ?? []).slice(0, 5).map((item, idx) => (
            <div key={`c-${idx}`} className="text-sm text-slate-300">
              {String(item.player_name)} ({(Number(item.weighted_probability ?? 0) * 100).toFixed(1)}%)
            </div>
          ))}
        </div>
        <div>
          <div className="mb-1 text-sm font-semibold">ML Top</div>
          {(comparison?.ml_top_players ?? []).slice(0, 5).map((item, idx) => (
            <div key={`m-${idx}`} className="text-sm text-slate-300">
              {String(item.player_name)} ({(Number(item.probability ?? 0) * 100).toFixed(1)}%)
            </div>
          ))}
        </div>
      </div>
      <div className="mt-3 text-sm text-slate-300">
        Overlap: {(comparison?.overlap ?? []).join(", ") || "none"}
      </div>
      <div className="mt-3 rounded bg-slate-950/40 p-3 text-xs text-slate-300">
        <div className="font-semibold">Divergence Explanation</div>
        {Object.entries(comparison?.divergence_explanation ?? {}).map(([k, v]) => (
          <div key={k}>
            {k}: {String(v)}
          </div>
        ))}
      </div>
      <div className="mt-3 rounded bg-slate-950/40 p-3 text-xs text-slate-300">
        <div className="font-semibold">Model Metadata</div>
        {(metadata?.models ?? []).map((model) => (
          <div key={model.model_family}>
            {model.model_family}: {model.model_version}
          </div>
        ))}
      </div>
    </section>
  );
}
