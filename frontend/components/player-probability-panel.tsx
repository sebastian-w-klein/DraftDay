import { RankedPlayerProbability } from "@/lib/intelligence-api";

type Props = {
  modelVersion: string;
  players: RankedPlayerProbability[];
};

export function PlayerProbabilityPanel({ modelVersion, players }: Props) {
  return (
    <section className="rounded-xl border border-indigo-800/40 bg-slate-900/60 p-4">
      <h2 className="mb-1 text-lg font-semibold">ML Player Probabilities</h2>
      <div className="mb-3 text-sm text-slate-300">Model: {modelVersion}</div>
      <div className="space-y-2">
        {players.slice(0, 8).map((player) => (
          <div key={`${player.player_name}-${player.position}`} className="rounded bg-slate-950/40 p-3">
            <div className="flex items-center justify-between">
              <div className="font-medium">
                {player.player_name} ({player.position})
              </div>
              <div className="font-semibold text-cyan-300">{(player.probability * 100).toFixed(1)}%</div>
            </div>
            <div className="mt-1 grid grid-cols-2 gap-2 text-xs text-slate-300">
              <div>Need: {player.need_component.toFixed(2)}</div>
              <div>Talent: {player.talent_component.toFixed(2)}</div>
              <div>Context: {player.context_component.toFixed(2)}</div>
              <div className="text-amber-300">
                Superstar override: {player.superstar_override_score.toFixed(2)}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
