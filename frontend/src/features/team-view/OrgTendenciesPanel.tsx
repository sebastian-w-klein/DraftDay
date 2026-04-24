type Props = {
  metrics: Record<string, number>;
  regimeStability: number;
};

export function OrgTendenciesPanel({ metrics, regimeStability }: Props) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <h2 className="text-lg font-semibold">Organizational Tendencies</h2>
      <div className="mt-2 text-sm text-slate-300">Regime stability: {regimeStability.toFixed(2)}</div>
      {Object.entries(metrics).map(([k, v]) => (
        <div key={k} className="mt-1 text-sm text-slate-300">
          {k}: {v.toFixed(2)}
        </div>
      ))}
    </section>
  );
}
