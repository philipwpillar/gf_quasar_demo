# GravitonForge Quasar Fleet Console

Operator-facing React + Vite + TypeScript + Tailwind console for the Quasar demo.
Reads verdicts from the FastAPI gateway only — it does not compute clearance or
admission locally.

## Run locally

```bash
# Terminal 1 — API (from repo root, with venv active)
export QUASAR_ENABLE_CORS=1
export QUASAR_CORS_ORIGIN=http://localhost:5173
export QUASAR_ENABLE_DEV_HOOKS=1   # required for propagating-failure demo
uvicorn api.api_main:app --reload

# Terminal 2 — console
cd console
npm install
npm run dev
```

Optional: set `VITE_QUASAR_API_BASE` (defaults to `http://localhost:8000`).

## CORS

The API enables CORS when `QUASAR_ENABLE_CORS=1` (default). Only the origin in
`QUASAR_CORS_ORIGIN` is allowed (default `http://localhost:5173`). Do not broaden
to `*` in committed backend code without an explicit env flag review.

## Scripts

- `npm run typecheck` — `tsc --noEmit`
- `npm run build` — typecheck + production bundle
- `npm test` — Vitest component tests
