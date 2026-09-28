// Server-side fetch from the Python API. Fail noisily: a failed call throws with the status.
const API = process.env.CARGO_API_URL ?? "http://127.0.0.1:8091";

export async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${API}${path}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status} ${await r.text()}`);
  return (await r.json()) as T;
}

export const usd = (v: number | null | undefined) => (v == null ? "-" : `${Math.round(v).toLocaleString("en-US")}`);
export const pct = (v: number | null | undefined, d = 1) => (v == null ? "-" : `${(v * 100).toFixed(d)} %`);
export const days = (v: number | null | undefined) => (v == null ? "-" : `${v.toFixed(1)} d`);
