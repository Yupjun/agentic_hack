import "./globals.css";
import type { ReactNode } from "react";

export const metadata = { title: "Cargo Planner — order & transport planning agent" };

const NAV = [
  ["/", "Overview"],
  ["/builder", "Plan Builder"],
  ["/scenarios", "Scenarios"],
  ["/agent", "Agent"],
  ["/runs", "Plans"],
  ["/live", "Live feeds"],
];

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko">
      <body className="font-sans">
        <header className="border-b-2 border-ink bg-sheet">
          <div className="mx-auto flex max-w-[1400px] items-center gap-8 px-6 py-3">
            <a href="/" className="text-lead font-semibold">Cargo Planner<span className="text-cobalt">.</span></a>
            <nav className="flex gap-1">
              {NAV.map(([href, label]) => (
                <a key={href} href={href} className="px-3 py-1 text-body hover:bg-ground">{label}</a>
              ))}
            </nav>
            <div className="ml-auto text-meta text-faint">NeMo Agent Toolkit · NeMo Guardrails · Nemotron 3 · cuOpt/HiGHS</div>
          </div>
        </header>
        <main className="mx-auto max-w-[1400px] px-6 py-6">{children}</main>
      </body>
    </html>
  );
}
