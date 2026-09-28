import type { Config } from "tailwindcss";

// Signal on Paper tokens (values from SP docs/DESIGN.md §팔레트, written fresh for this app).
// Tailwind's default palette is REMOVED: a colour that has no meaning cannot be written.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    colors: {
      transparent: "transparent",
      current: "currentColor",
      ground: "var(--ground)",
      sheet: "var(--sheet)",
      ink: "var(--ink)",
      muted: "var(--muted)",
      faint: "var(--faint)",
      line: "var(--line)",
      cobalt: "var(--cobalt)",
      tomato: "var(--tomato)",
      butter: "var(--butter)",
      "butter-ink": "var(--butter-ink)",
      plum: "var(--plum)",
      green: "var(--green)",
      mustard: "var(--mustard)",
      graphite: "var(--graphite)",
    },
    borderRadius: { none: "0" },
    fontSize: {
      meta: ["12px", "16px"],
      body: ["14px", "20px"],
      lead: ["16px", "22px"],
      h2: ["20px", "26px"],
      h1: ["28px", "34px"],
      stat: ["30px", "34px"],
    },
    boxShadow: { none: "none" },
    extend: {
      fontFamily: {
        sans: ["Pretendard", "Apple SD Gothic Neo", "Noto Sans KR", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
