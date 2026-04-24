import { TeamNeedItem } from "@/lib/intelligence-api";

type Props = {
  team: string;
  topNeeds: string[];
  needs: TeamNeedItem[];
};

export function TeamNeedProfile({ team, topNeeds, needs }: Props) {
  return (
    <section className="rounded-xl border border-indigo-800/40 bg-slate-900/60 p-4">
      <h2 className="mb-3 text-lg font-semibold">Team Need Profile ({team})</h2>
      <div className="mb-3 text-sm text-slate-300">Top needs: {topNeeds.join(", ") || "N/A"}</div>
      <div className="space-y-2">
        {needs.slice(0, 8).map((need) => (
          <div key={need.position} className="grid grid-cols-4 gap-2 text-sm">
            <div className="font-medium">{need.position}</div>
            <div>ST: {need.short_term_need_score.toFixed(2)}</div>
            <div>LT: {need.long_term_need_score.toFixed(2)}</div>
            <div className="font-semibold text-cyan-300">Overall: {need.overall_need_score.toFixed(2)}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
