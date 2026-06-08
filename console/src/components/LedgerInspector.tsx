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
    <section className="card">
      <header className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="section-title">Ledger inspector</h2>
          <p className="section-subtitle">
            Hash-chained forensic log from{" "}
            <code className="rounded bg-surface-muted px-1 py-0.5 font-mono text-xs text-ink-secondary">
              /ledger/export
            </code>
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={handleVerify}
            className="btn-primary px-3 py-1.5 text-sm"
          >
            Verify chain
          </button>
          <button
            type="button"
            disabled={busy || entries.length === 0}
            onClick={handleIllustrativeTamper}
            className="rounded-md border border-trust-warn-border bg-trust-warn-bg px-3 py-1.5 text-sm font-medium text-trust-warn-text hover:opacity-90 disabled:opacity-50"
          >
            Illustrative tamper (local copy)
          </button>
          {illustrativeEntries && (
            <button
              type="button"
              onClick={clearIllustrative}
              className="btn-secondary px-3 py-1.5 text-sm"
            >
              Reset to live export
            </button>
          )}
        </div>
      </header>

      {illustrativeEntries && (
        <p className="mb-4 rounded-md border border-trust-warn-border bg-trust-warn-bg px-3 py-2 text-sm text-trust-warn-text">
          Illustrative mode: tamper applied to a <strong>local copy only</strong>. The
          backend ledger is unchanged.
        </p>
      )}

      {displayVerify && (
        <div
          className={`mb-5 flex items-center gap-2 rounded-md border px-3 py-2.5 text-sm ${
            displayVerify.intact
              ? "border-trust-ok-border bg-trust-ok-bg text-trust-ok-text"
              : "border-trust-fail-border bg-trust-fail-bg text-trust-fail-text"
          }`}
          data-testid="ledger-verify-result"
        >
          <span aria-hidden="true">{displayVerify.intact ? "✓" : "✗"}</span>
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
        <p className="text-sm text-ink-secondary">No ledger entries yet.</p>
      ) : (
        <ol className="space-y-3" data-testid="ledger-entry-list">
          {sortedForDisplay.map((entry) => (
            <li
              key={entry.seq}
              className="rounded-md border border-line bg-surface-inset p-4 text-sm"
              data-testid={`ledger-entry-${entry.seq}`}
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs font-semibold text-ink-muted">
                  #{entry.seq}
                </span>
                <span className="rounded-md border border-line bg-surface-card px-2 py-0.5 font-mono text-xs font-medium text-accent">
                  {entry.kind}
                </span>
                <span className="text-xs text-ink-faint">{entry.occurred_at}</span>
              </div>
              <pre className="ledger-pre">{JSON.stringify(entry.payload, null, 2)}</pre>
              <p className="mt-2 font-mono text-xs text-ink-faint">
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
