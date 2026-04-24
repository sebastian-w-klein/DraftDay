type Row = Record<string, unknown>;

export function DraftHistoryPanel({ rows }: { rows: Row[] }) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <h2 className="text-lg font-semibold">Historical Behavior</h2>
      {rows.slice(0, 12).map((row, idx) => (
        <div key={idx} className="mt-2 text-sm text-slate-300">
          {String(row.year)} | Pick {String(row.overall_pick)} | Pos {String(row.position)}
        </div>
      ))}
    </section>
  );
}
