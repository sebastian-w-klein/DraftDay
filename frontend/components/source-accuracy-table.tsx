import { BacktestResult } from "@/lib/api";

type Props = {
  rows: BacktestResult[];
};

export function SourceAccuracyTable({ rows }: Props) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <h2 className="mb-4 text-lg font-semibold">Source Reliability Rankings</h2>
      <div className="overflow-x-auto">
        <table className="min-w-[40rem] w-full text-left text-sm">
          <thead className="text-slate-300">
            <tr>
              <th className="pb-2">Source</th>
              <th className="pb-2">Exact</th>
              <th className="pb-2">Player+Team</th>
              <th className="pb-2">Round 1 Hits</th>
              <th className="pb-2">Avg Distance</th>
              <th className="pb-2">Weighted Score</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.source_slug} className="border-t border-slate-800">
                <td className="py-2">{row.source_slug}</td>
                <td className="py-2">{row.exact_pick_hits}</td>
                <td className="py-2">{row.player_team_hits}</td>
                <td className="py-2">{row.round1_player_hits}</td>
                <td className="py-2">{row.avg_pick_distance.toFixed(2)}</td>
                <td className="py-2 font-semibold">{row.weighted_accuracy_score.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
