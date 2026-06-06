# GravitonForge Quasar — Demo

The trust-and-provenance layer for embodied AI. This repository is the
**demonstrator**, not the production system.

> **Status: scaffold.** This is the repo skeleton. No load-bearing component
> is built yet. The build order below is the sequence of work, not a claim of
> what exists. Everything marked REAL is held to production-grade rigour when
> built; everything marked STUBBED is disclosed as such on screen.

On screen, an operator assembles a robot from modules. The system verifies each
module's cryptographic identity, runs a mate-time attestation check against a
secure element, decides whether that exact configuration is cleared to operate,
issues a signed cleared / not-cleared verdict with plain-language reasons, and
writes the decision to an append-only, hash-chained, forensically-legible ledger.
An LLM assistant narrates the ledger but never decides anything.

No real robot is required to build or run this.

## REAL vs. STUBBED

| Component | Status | Notes |
|-----------|--------|-------|
| Mate-time attestation | **REAL** | Ed25519 / secure-element signatures, freshness-bound challenge-response. |
| Forensic ledger | **REAL** | Append-only, hash-chained, with a `verify()` any third party can run. |
| Policy / clearance engine | **STUBBED (breadth)** | Curated rule set for one task class, not the full optimiser. |
| Behaviour corpus | **STUBBED (depth)** | Synthetic, provenance-linked telemetry, not a real fleet. |
| Hardware root-of-trust | **NOT CLAIMED** | A dev-board secure element is real key custody; not a full RoT. |

A demo that hides its seams invites the wrong questions in diligence. Stubbed
components are disclosed as such on screen.

## Layout

```
gf_quasar_demo/
  attestation/   # module identity + mate-time verify        [REAL]
  ledger/        # append-only, hash-chained decision log     [REAL]
  policy/        # clearance engine, curated single-task rules [STUB breadth]
  corpus/        # telemetry sink + synthetic seed generator  [STUB depth]
  api/           # FastAPI gateway, pydantic-validated boundaries
  console/       # React + Vite + TypeScript + Tailwind console
  tests/         # pytest; ledger and attestation core carry real coverage
```

## Tech stack

- **Backend:** Python 3.11+, FastAPI, Pydantic v2
- **Crypto:** `cryptography` (Ed25519 in software; signing step swaps onto an
  ATECC608 / TPM 2.0 dev board without changing the protocol)
- **Ledger:** in-memory append-only store behind a `Ledger` class; production
  preserves the `verify()` contract
- **Frontend:** React + Vite, TypeScript, Tailwind CSS
- **LLM layer:** any hosted model over a read-only view of the ledger and policy
  (narrator only, never in the decision path)
- **Testing:** pytest

## Getting started

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env                 # fill locally; never commit .env
uvicorn api.main:app --reload        # (once api/main.py exists)
```

Tests:

```bash
pytest
```

## Build order

Sequenced to de-risk the load-bearing claims first.

1. **Ledger + `verify()`** — provable in isolation, no hardware needed. The spine.
2. **Attestation core in software (Ed25519)**, then swap the sign step onto a
   real secure element.
3. **API gateway + clearance flow** wiring attestation and ledger together.
4. **Console** with the module-assembly view and the reconfigure → signed verdict
   moment.
5. **LLM narrator + synthetic corpus seed** last. They are polish, not proof.

## Disciplines that are easy to get subtly wrong

- **Deterministic serialisation.** Ledger entries serialise with sorted keys and
  fixed separators so the same logical entry always hashes identically.
- **Provenance link.** Every telemetry sample carries an `attestation_ref` back
  to a real ledger entry.
- **Narrator boundary.** The LLM has read-only access; its output is never an
  input to `/clearance`.
- **No overclaiming.** "Real secure element, real attestation protocol," never
  "full root-of-trust."
- **No secrets in the repo.** Keys and `.env` are gitignored. This is the
  cardinal rule of an attestation project.

---

GravitonForge Quasar (working name). Confidential.
