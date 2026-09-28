#!/usr/bin/env bash
# One command to bring the demo up from a fresh shell.
#   dev/run-all.sh            start API (:8091, guarded LLM gateway + data) and dashboard (:3200)
#   dev/run-all.sh --replay   also re-solve the S1 scenarios and compare with the committed results
#   dev/run-all.sh --stop     stop both
# The NVIDIA key is read from ~/.config/nvidia/env (never printed). Ports: 8091, 3200 only.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
ROOT=$(pwd)
PY="$ROOT/.venv/bin/python"

pid_on() { ss -ltnp 2>/dev/null | grep ":$1 " | grep -oE 'pid=[0-9]+' | head -1 | cut -d= -f2; }
stop_port() { local p; p=$(pid_on "$1"); if [ -n "$p" ]; then kill "$p" && echo "stopped :$1 (pid $p)"; fi; }

if [ "${1:-}" = "--stop" ]; then stop_port 3200; stop_port 8091; exit 0; fi

[ -x "$PY" ] || { echo "missing $PY (venv on <venv>, see README)"; exit 1; }
if [ -f "$HOME/.config/nvidia/env" ]; then set -a; . "$HOME/.config/nvidia/env"; set +a; fi
[ -n "${NVIDIA_API_KEY:-}" ] || echo "WARNING: NVIDIA_API_KEY not set — the agent cannot call Nemotron; pages still work"

mkdir -p logs
stop_port 8091
setsid "$PY" -W ignore -m api.app > logs/api.out 2>&1 < /dev/null &
for i in $(seq 1 30); do curl -sf http://127.0.0.1:8091/api/health >/dev/null && break; sleep 1; done
curl -sf http://127.0.0.1:8091/api/health >/dev/null || { echo "API did not start; see logs/api.out"; tail -20 logs/api.out; exit 1; }
echo "API     http://127.0.0.1:8091  ok"

cd web
[ -d node_modules ] || npm install --no-audit --no-fund
node scripts/verify-design.mjs || exit 1
[ -f .next/BUILD_ID ] || npx next build >/dev/null || { echo "web build failed"; exit 1; }
cd "$ROOT"
stop_port 3200
# setsid + all three streams redirected: the server must not hold the caller's stdout (first version
# kept a pipe open, so "dev/run-all.sh | tail" never returned although everything was up).
setsid bash -c "cd '$ROOT/web' && exec npx next start -p 3200 -H 127.0.0.1" > "$ROOT/logs/web.out" 2>&1 < /dev/null &
for i in $(seq 1 30); do [ "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3200/)" = "200" ] && break; sleep 1; done
code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3200/)
[ "$code" = "200" ] || { echo "web did not start (HTTP $code); see logs/web.out"; exit 1; }
echo "WEB     http://127.0.0.1:3200  ok   (from a laptop: ssh -L 3200:127.0.0.1:3200 <server>)"

if [ "${1:-}" = "--replay" ]; then
  "$PY" -W ignore -m eval.replay_check --family S1 || { echo "REPLAY differs from committed results"; exit 1; }
  echo "REPLAY  S1 scenarios reproduce the committed numbers"
fi
