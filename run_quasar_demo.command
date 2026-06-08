#!/usr/bin/env bash
#
# run_quasar_demo.command - one-click local launcher for the GravitonForge
# Quasar demo. Double-click in Finder (or run from a terminal) to start the
# FastAPI backend and the Vite console together, open the browser, and shut
# both down cleanly when you quit (Ctrl-C or closing the window).
#
# LOCAL dev launcher: binds to localhost only, reads secrets from .env,
# nothing is exposed to the network.
#
# NOTE: uses plain `wait` (not `wait -n`) so it runs on macOS's stock bash 3.2.

set -uo pipefail   # NB: no `-e` - a non-fatal command must not trigger shutdown

# --- locate the repo (this script lives at the repo root) ---------------------
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

echo "GravitonForge Quasar - local demo launcher"
echo "Repo: $REPO_DIR"
echo

# --- .env check ---------------------------------------------------------------
if [[ ! -f .env ]]; then
  echo "WARNING: no .env file found. The narrator (LLM) and signing-authority"
  echo "keys will be unset; the demo still runs, but the narrator will report"
  echo "'not configured' and verdict signatures won't survive a restart."
  echo "Copy .env.example to .env and fill it in to enable those."
  echo
fi

# Load .env into this script's environment so both processes inherit it.
# Tolerant of comments, blank lines, and values containing spaces.
if [[ -f .env ]]; then
  set -a
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" || "$line" == \#* ]] && continue
    eval "export $line" 2>/dev/null || true
  done < .env
  set +a
fi

# --- backend venv + deps ------------------------------------------------------
if [[ ! -d .venv ]]; then
  echo "Creating Python virtual environment (.venv)..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "Ensuring backend dependencies are installed..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# --- console deps -------------------------------------------------------------
if [[ ! -d console/node_modules ]]; then
  echo "Installing console dependencies (first run only)..."
  (cd console && npm install)
fi

# --- CORS so the console (:5173) can call the API (:8000) ---------------------
export QUASAR_ENABLE_CORS="${QUASAR_ENABLE_CORS:-1}"
export QUASAR_CORS_ORIGIN="${QUASAR_CORS_ORIGIN:-http://localhost:5173}"

# --- start both processes -----------------------------------------------------
BACKEND_PID=""
CONSOLE_PID=""
cleanup() {
  echo
  echo "Shutting down..."
  [[ -n "$CONSOLE_PID" ]] && kill "$CONSOLE_PID" 2>/dev/null || true
  [[ -n "$BACKEND_PID" ]] && kill "$BACKEND_PID" 2>/dev/null || true
  # free the ports in case a child re-spawned
  lsof -ti:8000,5173 2>/dev/null | xargs kill 2>/dev/null || true
  echo "Stopped."
}
trap cleanup EXIT INT TERM

echo
echo "Starting backend (http://localhost:8000, docs at /docs)..."
uvicorn api.api_main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

echo "Starting console (http://localhost:5173)..."
( cd console && npm run dev -- --port 5173 ) &
CONSOLE_PID=$!

# --- wait for the API health endpoint, then open the browser ------------------
echo "Waiting for the backend to come up..."
for _ in $(seq 1 30); do
  if curl -sf http://localhost:8000/healthz >/dev/null 2>&1; then
    echo "Backend is up."
    break
  fi
  # if the backend died during startup, surface it instead of hanging
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "ERROR: backend process exited during startup. Scroll up for the traceback."
    exit 1
  fi
  sleep 1
done

echo "Opening http://localhost:5173 ..."
open http://localhost:5173 || true

echo
echo "Demo is running.  Backend :8000  |  Console :5173"
echo "Leave this window open. Press Ctrl-C (or close it) to stop everything."
echo

# Block until interrupted. Plain `wait` works on bash 3.2 (macOS stock).
# The trap above handles clean shutdown on Ctrl-C / window close.
wait
