type Need = { position: string; overall_need_score: number };

export function NeedProfilePanel({ needs }: { needs: Need[] }) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <h2 className="text-lg font-semibold">Need Profile</h2>
      {needs.slice(0, 8).map((need) => (
        <div key={need.position} className="mt-2 flex items-center justify-between text-sm">
          <span>{need.position}</span>
          <span className="font-semibold text-cyan-300">{need.overall_need_score.toFixed(2)}</span>
        </div>
      ))}
    </section>
  );
}
