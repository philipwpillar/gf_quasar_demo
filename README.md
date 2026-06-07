# GravitonForge Quasar — Demo

The trust-and-provenance layer for embodied AI. This repository is the
**demonstrator**, not the production system.

> **Status: scaffold.** This is the repo skeleton. No load-bearing component
> is built yet. The build order below is the sequence of work, not a claim of
> what exists. Everything marked REAL is held to production-grade rigour when
> built; everything marked STUBBED is disclosed as such on screen.

On screen, an operator assembles robots from modules and admits them to a
multi-vendor site. The system verifies each module's cryptographic identity,
runs a mate-time attestation check against a secure element, composes verified
modules into a robot identity, decides whether that robot is cleared to operate
on the site for a given task, issues a signed cleared / not-cleared verdict with
plain-language reasons, and writes every step to an append-only, hash-chained,
forensically-legible ledger. An LLM assistant narrates the ledger but never
decides anything.

No real robot is required to build or run this.

## The unit is the site, not the robot

The market unit is the **multi-vendor site** — a construction site, a substation,
a warehouse populated by heterogeneous machines from many makers — not a single
reconfigurable robot. The same freshness-bound challenge-response primitive is
applied at three boundaries, with only *what counts as an identity* moving up a
level each time:

- **Tier 1 — Module → Robot (mate-time).** Each module signs a fresh nonce in its
  secure element; the verifier checks it against the enrolled public key.
- **Tier 2 — Robot composition.** A robot identity is composed from its set of
  attested module refs plus a vendor-issued key.
- **Tier 3 — Robot → Site (admission-time).** The assembled robot presents its
  identity at the site gate; site policy clears it for a task in a zone.

The demo moment the hierarchy unlocks: a robot is **refused site admission**
because **one module inside it failed mate-time attestation** — bad module →
untrusted robot → denied admission — and the ledger records every link. At least
one full real chain stays live (one genuine secure-element module, attested for
real, composed, admitted); the rest of the fleet is seeded synthetic and
labelled on screen.

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
gf_quasar_demo/
ledger/        # append-only, hash-chained decision log     [REAL]
attestation/   # module identity + mate-time verify        [REAL]
policy/        # clearance engine, curated single-task rules [STUB breadth]
corpus/        # telemetry sink + synthetic seed generator  [STUB depth]
narrator/      # LLM assistant; read-only, never decides    [STUB / READ-ONLY]
api/           # FastAPI gateway, pydantic-validated boundaries
shared/        # cross-component primitives (canonical hashing, time helpers)
console/       # React + Vite + TypeScript + Tailwind console
tests/         # pytest; ledger and attestation core carry real coverage

Components follow one rule: package-by-component at the top level, a consistent
file-role taxonomy inside each. `shared/` is deliberately thin and holds
`canonical_hashing.py` — the one deterministic serialise-and-hash routine the
ledger and any external `verify()` must both call. See
`docs/QUASAR_CODEBASE_ORGANIZATION.txt` for the authoritative naming and
structure rules.

## Ledger entry kinds

The ledger carries all seven entry kinds from line one, so the three-tier
hierarchy lives in the spine rather than being bolted on later. All chain
identically and obey the same deterministic-serialisation rule.

| Entry kind | Records |
|------------|---------|
| `module_enrolled` | A module's identity and public key are registered. |
| `attestation` | The result of a mate-time challenge-response (Tier 1). |
| `robot_composed` | A robot identity composed from attested module refs + a vendor key (Tier 2). |
| `site_admission` | A robot's admission decision at a site gate — cleared / not-cleared for a task in a zone (Tier 3). A clearance/provenance event, never a dispatch log. |
| `clearance_decision` | The signed cleared / not-cleared verdict and plain-language reasons. |
| `telemetry` | A behaviour sample, provenance-linked to its attestation via `attestation_ref`. |
| `decommission` | Hook for the future kill-and-prove-dead protocol (stub). |

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
uvicorn api.api_main:app --reload    # (once api/api_main.py exists)
```

Tests:

```bash
pytest
```

## Build order

Sequenced to de-risk the load-bearing claims first.

1. **Ledger + `verify()`** — provable in isolation, no hardware needed. The spine.
   Carries all seven entry kinds (incl. `robot_composed`, `site_admission`) from
   line one.
2. **Attestation core in software (Ed25519)**, then swap the sign step onto a
   real secure element.
3. **API gateway + clearance flow** wiring attestation and ledger together.
4. **Console** with the module-assembly view and the reconfigure → signed verdict
   moment, plus the site → robots → modules hierarchy and the propagating-failure
   path as centrepiece.
5. **LLM narrator + synthetic corpus seed** last. They are polish, not proof.

## Disciplines that are easy to get subtly wrong

- **Deterministic serialisation.** Ledger entries serialise with sorted keys and
  fixed separators so the same logical entry always hashes identically. The one
  routine lives in `shared/canonical_hashing.py`; a second copy is a
  chain-splitting hazard.
- **Provenance link.** Every telemetry sample carries an `attestation_ref` back
  to a real ledger entry.
- **Tier 3 attests, never orchestrates.** Site admission is an identity/compliance
  gate that records a provenance event, not a task dispatcher. Drifting toward
  "we coordinate your site" walks into the robotics-services trap.
- **Narrator boundary.** The LLM has read-only access; its output is never an
  input to `/clearance`.
- **No overclaiming.** "Real secure element, real attestation protocol," never
  "full root-of-trust."
- **No secrets in the repo.** Keys and `.env` are gitignored. This is the
  cardinal rule of an attestation project.

---

