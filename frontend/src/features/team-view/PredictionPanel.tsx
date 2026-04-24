type Props = {
  base: Record<string, number>;
  adjusted: Record<string, number>;
  delta: Record<string, number>;
  players: Array<{
    player_name: string;
    position: string;
    base_probability: number;
    org_adjusted_probability: number;
    organizational_component: number;
  }>;
};

export function PredictionPanel({ base, adjusted, delta, players }: Props) {
  const keys = Object.keys(adjusted).slice(0, 8);
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <h2 className="text-lg font-semibold">Prediction Panel</h2>
      <div className="mt-2 text-sm font-semibold">Position Probabilities</div>
      {keys.map((k) => (
        <div key={k} className="mt-2 grid grid-cols-4 gap-2 text-xs text-slate-300">
          <div>{k}</div>
          <div>Base: {(base[k] ?? 0).toFixed(3)}</div>
          <div>Adj: {(adjusted[k] ?? 0).toFixed(3)}</div>
          <div>Delta: {(delta[k] ?? 0).toFixed(3)}</div>
        </div>
      ))}
      <div className="mt-4 text-sm font-semibold">Player Probabilities</div>
      {players.slice(0, 6).map((p) => (
        <div key={`${p.player_name}-${p.position}`} className="mt-2 grid grid-cols-5 gap-2 text-xs text-slate-300">
          <div className="col-span-2">
            {p.player_name} ({p.position})
          </div>
          <div>Base: {p.base_probability.toFixed(3)}</div>
          <div>Adj: {p.org_adjusted_probability.toFixed(3)}</div>
          <div>Org: {p.organizational_component.toFixed(2)}</div>
        </div>
      ))}
    </section>
  );
}
