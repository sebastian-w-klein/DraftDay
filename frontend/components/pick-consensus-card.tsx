import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { ConsensusConfidence, PickProbability } from "@/lib/api";

type Props = {
  data: PickProbability[];
  confidence?: ConsensusConfidence | null;
};

export function PickConsensusCard({ data, confidence }: Props) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <h2 className="mb-4 text-lg font-semibold">Top Players For Pick</h2>
      {confidence ? (
        <div className="mb-3 flex flex-wrap gap-2 text-xs text-slate-400">
          <span>
            Smoothed estimates (Dirichlet α={confidence.smoothing_alpha}) — not raw vote shares.
          </span>
          {confidence.low_confidence ? (
            <span className="rounded bg-amber-500/20 px-2 py-0.5 text-amber-200">Low source coverage</span>
          ) : null}
          <span>
            n={confidence.sample_size} sources={confidence.unique_sources} other≈
            {(confidence.other_bucket_probability * 100).toFixed(1)}%
          </span>
        </div>
      ) : null}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <XAxis dataKey="player_name" tick={{ fill: "#e2e8f0", fontSize: 11 }} />
            <YAxis tick={{ fill: "#e2e8f0", fontSize: 11 }} />
            <Tooltip />
            <Bar dataKey="weighted_probability" fill="#38bdf8" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
