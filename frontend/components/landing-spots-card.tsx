import { useMemo } from "react";
import { Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { LandingConfidence, PlayerLandingSpot } from "@/lib/api";

type Props = {
  data: PlayerLandingSpot[];
  confidence?: LandingConfidence | null;
  title?: string;
  onClearSelection?: () => void;
  /** Overall pick used for slot-level mock depth (all prospects at that pick). */
  slotContextPick?: number | null;
  slotContextRowCount?: number | null;
  resolvedLookupName?: string | null;
  draftCycleTotalPickRows?: number | null;
  draftCycleMockArticles?: number | null;
};

export function LandingSpotsCard({
  data,
  confidence,
  title,
  onClearSelection,
  slotContextPick,
  slotContextRowCount,
  resolvedLookupName,
  draftCycleTotalPickRows,
  draftCycleMockArticles,
}: Props) {
  const pOther = confidence?.other_bucket_probability ?? 0;

  /** Dirichlet-smoothed shares look similar across players (~fixed "other" wedge); chart uses raw mock counts when available. */
  const useEmpirical =
    data.length > 0 &&
    data.every((d) => d.raw_probability != null && Number.isFinite(d.raw_probability)) &&
    (confidence?.sample_size ?? 0) >= 1;

  const chartData = useMemo(() => {
    if (useEmpirical) {
      const slices = data.map((d) => ({
        team: d.team,
        probability: d.raw_probability as number,
      }));
      const sum = slices.reduce((a, s) => a + s.probability, 0);
      if (sum < 0.98 && sum > 0.001) {
        slices.push({
          team: "Other teams (in mocks, below top slots shown)",
          probability: Math.max(0, 1 - sum),
        });
      }
      return slices;
    }
    const rows = data.map((d) => ({ team: d.team, probability: d.probability }));
    if (pOther > 0.0005) {
      rows.push({ team: "Smoothed: other teams (prior)", probability: pOther });
    }
    return rows;
  }, [data, pOther, useEmpirical]);

  const hasSingle = data.length === 1;
  const heading = title ?? "Likely Landing Spots";
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-2">
        <h2 className="text-lg font-semibold">{heading}</h2>
        {onClearSelection ? (
          <button
            type="button"
            onClick={onClearSelection}
            className="shrink-0 rounded border border-slate-600 px-2 py-0.5 text-xs text-slate-300 hover:bg-slate-800"
          >
            Use #1 overall
          </button>
        ) : null}
      </div>
      {confidence ? (
        <p className="mb-2 text-xs text-slate-400">
          {useEmpirical ? (
            <>
              <span className="text-slate-300">Chart:</span> empirical share of mock rows naming this prospect
              (each row = one team assignment). n={confidence.sample_size},{" "}
              {confidence.unique_sources ?? 0} sources / {confidence.unique_articles ?? 0} articles,{" "}
              {confidence.unique_teams} team(s) in data
            </>
          ) : (
            <>
              Smoothed team shares (α={confidence.smoothing_alpha}), n={confidence.sample_size} mock rows naming this
              prospect, {confidence.unique_sources ?? 0} sources / {confidence.unique_articles ?? 0} articles,{" "}
              {confidence.unique_teams} distinct teams, implicit pool K≈{confidence.category_count}
            </>
          )}
          {confidence.low_confidence ? " — " : "."}
          {confidence.low_confidence ? (
            <span className="text-amber-200">thin landing data</span>
          ) : null}
          {useEmpirical && pOther > 0.02 ? (
            <span className="block pt-1 text-slate-500">
              (Dirichlet &quot;other&quot; mass from the API is {Math.round(pOther * 100)}% — omitted from the pie so
              the chart matches how often each listed team actually appears in those rows.)
            </span>
          ) : null}
        </p>
      ) : null}
      {draftCycleMockArticles != null && draftCycleTotalPickRows != null ? (
        <p className="mb-2 text-xs text-slate-500">
          Draft class in DB:{" "}
          <span className="font-mono text-slate-300">{draftCycleMockArticles}</span> mock article(s),{" "}
          <span className="font-mono text-slate-300">{draftCycleTotalPickRows}</span> total pick rows (all prospects).
        </p>
      ) : null}
      {confidence &&
      confidence.sample_size <= 2 &&
      draftCycleTotalPickRows != null &&
      draftCycleTotalPickRows > confidence.sample_size + 5 ? (
        <p className="mb-2 text-xs text-slate-500">
          This prospect matches only <span className="font-mono text-slate-300">{confidence.sample_size}</span> of
          those rows (by normalized name). The large &quot;other teams&quot; slice is{" "}
          <strong>Dirichlet smoothing</strong>, not a claim that mocks omit listed teams. Add mocks that slot this
          player, or fix spelling vs. stored names.
        </p>
      ) : null}
      {confidence &&
      confidence.sample_size <= 2 &&
      draftCycleMockArticles != null &&
      draftCycleMockArticles <= 1 &&
      draftCycleTotalPickRows != null &&
      draftCycleTotalPickRows < 24 ? (
        <p className="mb-2 text-xs text-amber-200/90">
          Few mock pick rows are loaded for this year (under a full round of picks). Ingest more boards (
          <span className="font-mono">POST /v1/ingestion/run/all</span>,{" "}
          <span className="font-mono">POST /v1/ingestion/parse-url</span>, or scripts under{" "}
          <span className="font-mono">scripts/</span>).
        </p>
      ) : null}
      {confidence &&
      confidence.sample_size <= 2 &&
      slotContextPick != null &&
      slotContextRowCount != null &&
      slotContextRowCount > confidence.sample_size &&
      (draftCycleTotalPickRows == null || draftCycleTotalPickRows <= confidence.sample_size + 5) ? (
        <p className="mb-2 text-xs text-slate-500">
          At pick <span className="font-mono text-slate-300">{slotContextPick}</span> there are{" "}
          <span className="font-mono text-slate-300">{slotContextRowCount}</span> mock rows (all players at that slot),
          but only <span className="font-mono text-slate-300">{confidence.sample_size}</span> name this prospect.
        </p>
      ) : null}
      {resolvedLookupName ? (
        <p className="mb-2 text-[10px] text-slate-600">
          Matched mock rows as <span className="font-mono">{resolvedLookupName}</span>
        </p>
      ) : null}
      {hasSingle ? (
        <p className="mb-3 text-xs text-slate-400">
          Only one source currently predicts this player, so distribution is limited.
        </p>
      ) : null}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              dataKey="probability"
              nameKey="team"
              outerRadius={90}
              fill="#22d3ee"
            />
            <Tooltip formatter={(value: number) => `${(value * 100).toFixed(1)}%`} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-3 space-y-1 text-sm text-slate-300">
        {data.slice(0, 5).map((spot) => {
          const pct = useEmpirical
            ? ((spot.raw_probability ?? spot.probability) * 100).toFixed(0)
            : (spot.probability * 100).toFixed(0);
          return (
            <div key={spot.team} className="flex items-center justify-between">
              <span>{spot.team}</span>
              <span>{pct}%</span>
            </div>
          );
        })}
        {!useEmpirical && pOther > 0.0005 ? (
          <div className="flex items-center justify-between border-t border-slate-800 pt-1 text-slate-400">
            <span>Smoothed: other teams (prior)</span>
            <span>{(pOther * 100).toFixed(0)}%</span>
          </div>
        ) : null}
        {useEmpirical ? (() => {
          const sumTop = data.reduce((a, d) => a + (d.raw_probability ?? 0), 0);
          const rest = Math.max(0, 1 - sumTop);
          return rest > 0.015 ? (
            <div className="flex items-center justify-between border-t border-slate-800 pt-1 text-slate-400">
              <span>Other teams (in mocks, below top slots shown)</span>
              <span>{(rest * 100).toFixed(0)}%</span>
            </div>
          ) : null;
        })() : null}
      </div>
    </section>
  );
}
