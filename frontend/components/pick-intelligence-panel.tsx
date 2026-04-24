import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type Props = {
  team: string;
  pick: number;
  modelVersion: string;
  probabilities: Record<string, number>;
  explanation: Record<string, string | number>;
};

export function PickIntelligencePanel({ team, pick, modelVersion, probabilities, explanation }: Props) {
  const data = Object.entries(probabilities).map(([position, probability]) => ({
    position,
    probability
  }));
  return (
    <section className="rounded-xl border border-indigo-800/40 bg-slate-900/60 p-4">
      <h2 className="mb-1 text-lg font-semibold">Pick Intelligence Panel</h2>
      <div className="mb-3 text-sm text-slate-300">
        {team} at pick {pick} | model: {modelVersion}
      </div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <XAxis dataKey="position" tick={{ fill: "#e2e8f0", fontSize: 11 }} />
            <YAxis tick={{ fill: "#e2e8f0", fontSize: 11 }} />
            <Tooltip />
            <Bar dataKey="probability" fill="#818cf8" />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-3 rounded bg-slate-950/40 p-3 text-sm">
        <div className="font-semibold">Explanation Summary</div>
        {Object.entries(explanation).map(([k, v]) => (
          <div key={k} className="text-slate-300">
            {k}: {String(v)}
          </div>
        ))}
      </div>
    </section>
  );
}
