import { useState } from "react";

import { exportLedger, verifyLedger } from "../api/quasarApiClient";
import type { EntryKind, LedgerEntry, LedgerVerifyResponse } from "../types/quasarLedgerTypes";

const ENTRY_KIND_ORDER: EntryKind[] = [
  "module_enrolled",
  "attestation",
  "robot_composed",
  "site_admission",
  "clearance_decision",
  "telemetry",
  "decommission",
];

interface LedgerInspectorProps {
  entries: LedgerEntry[];
  verifyResult: LedgerVerifyResponse | null;
  onRefresh: () => Promise<void>;
  busy: boolean;
}

function kindIndex(kind: EntryKind): number {
  const idx = ENTRY_KIND_ORDER.indexOf(kind);
  return idx === -1 ? ENTRY_KIND_ORDER.length : idx;
}

export default function LedgerInspector({
  entries,
  verifyResult,
  onRefresh,
  busy,
}: LedgerInspectorProps) {
  const [illustrativeEntries, setIllustrativeEntries] = useState<LedgerEntry[] | null>(
    null,
  );
  const [illustrativeVerify, setIllustrativeVerify] =
    useState<LedgerVerifyResponse | null>(null);

  const displayEntries = illustrativeEntries ?? entries;
  const displayVerify = illustrativeVerify ?? verifyResult;

  const sortedForDisplay = [...displayEntries].sort((a, b) => {
    if (a.seq !== b.seq) {
      return a.seq - b.seq;
    }
    return kindIndex(a.kind) - kindIndex(b.kind);
  });

  async function handleVerify() {
    await onRefresh();
  }

  function handleIllustrativeTamper() {
    if (entries.length === 0) {
      return;
    }
    const localCopy = structuredClone(entries);
    const target = localCopy[localCopy.length - 1];
    if (target) {
      target.payload = {
        ...target.payload,
        _illustrative_tamper: "local copy only — does not affect backend",
      };
      target.entry_hash = "f".repeat(64);
    }
    setIllustrativeEntries(localCopy);
    setIllustrativeVerify({ intact: false, first_broken_seq: target?.seq ?? 1 });
  }

  function clearIllustrative() {
    setIllustrativeEntries(null);
    setIllustrativeVerify(null);
  }

  return (
    <section className="rounded-lg border border-slate-700 bg-slate-900 p-4">
      <header className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold text-slate-100">Ledger inspector</h2>
          <p className="text-sm text-slate-400">
            Hash-chained forensic log from <code className="text-slate-300">/ledger/export</code>
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={handleVerify}
            className="rounded bg-indigo-800 px-3 py-1.5 text-sm font-medium text-indigo-50 hover:bg-indigo-700 disabled:opacity-50"
          >
            Verify chain
          </button>
          <button
            type="button"
            disabled={busy || entries.length === 0}
            onClick={handleIllustrativeTamper}
            className="rounded border border-amber-700 bg-amber-950 px-3 py-1.5 text-sm font-medium text-amber-200 hover:bg-amber-900 disabled:opacity-50"
          >
            Illustrative tamper (local copy)
          </button>
          {illustrativeEntries && (
            <button
              type="button"
              onClick={clearIllustrative}
              className="rounded bg-slate-700 px-3 py-1.5 text-sm text-slate-100 hover:bg-slate-600"
            >
              Reset to live export
            </button>
          )}
        </div>
      </header>

      {illustrativeEntries && (
        <p className="mb-3 rounded border border-amber-700 bg-amber-950 px-3 py-2 text-sm text-amber-100">
          Illustrative mode: tamper applied to a <strong>local copy only</strong>. The
          backend ledger is unchanged.
        </p>
      )}

      {displayVerify && (
        <div
          className={`mb-4 rounded border px-3 py-2 text-sm ${
            displayVerify.intact
              ? "border-emerald-700 bg-emerald-950 text-emerald-100"
              : "border-rose-700 bg-rose-950 text-rose-100"
          }`}
          data-testid="ledger-verify-result"
        >
          {displayVerify.intact ? (
            <span>Chain intact</span>
          ) : (
            <span>
              Chain broken — first broken seq: {displayVerify.first_broken_seq ?? "unknown"}
            </span>
          )}
        </div>
      )}

      {sortedForDisplay.length === 0 ? (
        <p className="text-sm text-slate-400">No ledger entries yet.</p>
      ) : (
        <ol className="space-y-2" data-testid="ledger-entry-list">
          {sortedForDisplay.map((entry) => (
            <li
              key={entry.seq}
              className="rounded border border-slate-700 bg-slate-950 p-3 text-sm"
              data-testid={`ledger-entry-${entry.seq}`}
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs text-slate-500">#{entry.seq}</span>
                <span className="rounded bg-slate-800 px-2 py-0.5 font-mono text-xs text-indigo-200">
                  {entry.kind}
                </span>
                <span className="text-xs text-slate-500">{entry.occurred_at}</span>
              </div>
              <pre className="mt-2 overflow-x-auto font-mono text-xs text-slate-400">
                {JSON.stringify(entry.payload, null, 2)}
              </pre>
              <p className="mt-1 font-mono text-xs text-slate-600">
                prev {entry.prev_hash.slice(0, 12)}… → hash {entry.entry_hash.slice(0, 12)}…
              </p>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

export async function fetchLedgerState(): Promise<{
  entries: LedgerEntry[];
  verifyResult: LedgerVerifyResponse;
}> {
  const [entries, verifyResult] = await Promise.all([exportLedger(), verifyLedger()]);
  return { entries, verifyResult };
}
