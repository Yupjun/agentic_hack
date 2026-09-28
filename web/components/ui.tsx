import type { ReactNode } from "react";

// Panel: one question per panel; the title IS that question.
export function Panel({ title, kicker, right, children }: { title: string; kicker?: string; right?: ReactNode; children: ReactNode }) {
  return (
    <section className="sheet p-5">
      <div className="mb-4 flex items-baseline justify-between gap-4">
        <div>
          {kicker && <div className="kicker mb-1">{kicker}</div>}
          <h2 className="text-h2 font-semibold">{title}</h2>
        </div>
        {right}
      </div>
      {children}
    </section>
  );
}

// BigStat: tone band + brackets, label / number / sub-line. At most three facts.
export function BigStat({ label, value, sub, tone = "ink" }: { label: string; value: string; sub?: string; tone?: "ink" | "cobalt" | "tomato" | "green" }) {
  return (
    <div className={`sheet accent-corners tone-${tone} py-4 pl-5 pr-6`}>
      <div className="kicker">{label}</div>
      <div className="mt-1 text-stat font-semibold">{value}</div>
      {sub && <div className="mt-1 text-meta text-muted">{sub}</div>}
    </div>
  );
}

// Badge: letters, not icons. Tone carries the meaning.
export function Badge({ children, tone = "ink" }: { children: ReactNode; tone?: "ink" | "cobalt" | "tomato" | "green" | "muted" }) {
  const c = { ink: "border-ink text-ink", cobalt: "border-cobalt text-cobalt", tomato: "border-tomato text-tomato", green: "border-green text-green", muted: "border-line text-muted" }[tone];
  return <span className={`inline-block border px-2 py-0.5 text-meta font-semibold uppercase tracking-wide ${c}`}>{children}</span>;
}

export function Row({ badge, title, meta, href }: { badge: ReactNode; title: ReactNode; meta: ReactNode; href?: string }) {
  const body = (
    <div className="flex items-start gap-3 border-b border-line px-1 py-3">
      <div className="w-28 shrink-0 pt-0.5">{badge}</div>
      <div className="min-w-0">
        <div className="text-body">{title}</div>
        <div className="mt-1 text-meta text-faint">{meta}</div>
      </div>
    </div>
  );
  return href ? <a href={href} className="block hover:bg-ground">{body}</a> : body;
}
