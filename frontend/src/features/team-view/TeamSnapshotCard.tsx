type Props = {
  teamName: string;
  gm: string | null;
  hc: string | null;
  currentPicks: number[];
  topNeeds: Array<{ position: string; overall_need_score: number }>;
};

export function TeamSnapshotCard({ teamName, gm, hc, currentPicks, topNeeds }: Props) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <h2 className="text-lg font-semibold">Team Snapshot</h2>
      <div className="mt-2 text-sm text-slate-300">Team: {teamName}</div>
      <div className="text-sm text-slate-300">GM: {gm ?? "Unknown"}</div>
      <div className="text-sm text-slate-300">Head Coach: {hc ?? "Unknown"}</div>
      <div className="mt-2 text-sm text-slate-300">
        Current Picks: {currentPicks.length ? currentPicks.slice(0, 12).join(", ") : "Unavailable"}
      </div>
      <div className="mt-3">
        <div className="text-sm font-semibold">Top Needs</div>
        {topNeeds.slice(0, 5).map((n) => (
          <div key={n.position} className="text-sm text-slate-300">
            {n.position}: {n.overall_need_score.toFixed(2)}
          </div>
        ))}
      </div>
    </section>
  );
}
