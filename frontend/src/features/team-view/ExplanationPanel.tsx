type Props = {
  text: string;
  components: {
    need_component: number;
    talent_component: number;
    context_component: number;
    organizational_component: number;
  };
};

export function ExplanationPanel({ text, components }: Props) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <h2 className="text-lg font-semibold">Explanation Panel</h2>
      <p className="mt-2 text-sm text-slate-300">{text}</p>
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-300">
        <div>Need: {components.need_component.toFixed(2)}</div>
        <div>Talent: {components.talent_component.toFixed(2)}</div>
        <div>Context: {components.context_component.toFixed(2)}</div>
        <div>Organizational: {components.organizational_component.toFixed(2)}</div>
      </div>
    </section>
  );
}
