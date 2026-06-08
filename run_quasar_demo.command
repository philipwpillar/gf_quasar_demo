#!/usr/bin/env bash
#
# run_quasar_demo.command — one-click local launcher for the GravitonForge
# Quasar demo. Double-click in Finder (or run from a terminal) to start the
# FastAPI backend and the Vite console together, open the browser, and shut
# both down cleanly when you quit (Ctrl-C or closing the window).
#
# This is a LOCAL dev launcher. It binds to localhost only and reads secrets
# from .env — nothing is exposed to the network.

set -euo pipefail

# --- locate the repo (this script lives at the repo root) ---------------------
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

echo "GravitonForge Quasar — local demo launcher"
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
# (Lines like KEY=value; comments and blanks ignored.)
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
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

# --- start both processes -----------------------------------------------------
# Backend on :8000, console on :5173. CORS must allow the console origin.
export QUASAR_ENABLE_CORS="${QUASAR_ENABLE_CORS:-1}"
export QUASAR_CORS_ORIGIN="${QUASAR_CORS_ORIGIN:-http://localhost:5173}"

PIDS=()
cleanup() {
  echo
  echo "Shutting down..."
  for pid in "${PIDS[@]:-}"; do
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  wait 2>/dev/null || true
  echo "Stopped."
}
trap cleanup EXIT INT TERM

echo
echo "Starting backend (http://localhost:8000, docs at /docs)..."
uvicorn api.api_main:app --host 127.0.0.1 --port 8000 &
PIDS+=($!)

echo "Starting console (http://localhost:5173)..."
(cd console && npm run dev -- --port 5173 >/dev/null 2>&1) &
PIDS+=($!)

# --- wait for the console, then open the browser ------------------------------
echo "Waiting for the console to come up..."
for _ in $(seq 1 30); do
  if curl -sf http://localhost:5173 >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "Opening http://localhost:5173 ..."
open http://localhost:5173 || true

echo
echo "Demo is running. Backend :8000  |  Console :5173"
echo "Leave this window open. Press Ctrl-C (or close it) to stop everything."
echo

# Keep the script alive until interrupted; if either process dies, exit.
wait
