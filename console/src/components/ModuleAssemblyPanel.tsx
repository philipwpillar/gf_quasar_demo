import type { EnrolledModule } from "../types/quasarLedgerTypes";

interface ModuleAssemblyPanelProps {
  modules: EnrolledModule[];
  selectedModuleIds: string[];
  onToggleModule: (moduleId: string) => void;
  onEnrolRealModule: () => void;
  onEnrolSyntheticModules: () => void;
  onAttestModule: (moduleId: string) => void;
  onAttestAll: () => void;
  busy: boolean;
  error: string | null;
}

function trustBadgeClasses(verified: boolean | undefined): string {
  if (verified === undefined) {
    return "border-trust-neutral-border bg-trust-neutral-bg text-trust-neutral-text";
  }
  return verified
    ? "border-trust-ok-border bg-trust-ok-bg text-trust-ok-text"
    : "border-trust-fail-border bg-trust-fail-bg text-trust-fail-text";
}

function trustLabel(verified: boolean | undefined): string {
  if (verified === undefined) {
    return "Not attested yet";
  }
  return verified ? "Verified: true" : "Verified: false";
}

function trustIcon(verified: boolean | undefined): string {
  if (verified === undefined) {
    return "○";
  }
  return verified ? "✓" : "✗";
}

export default function ModuleAssemblyPanel({
  modules,
  selectedModuleIds,
  onToggleModule,
  onEnrolRealModule,
  onEnrolSyntheticModules,
  onAttestModule,
  onAttestAll,
  busy,
  error,
}: ModuleAssemblyPanelProps) {
  return (
    <section className="card h-full">
      <header className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="section-title">Module assembly</h2>
          <p className="section-subtitle">
            Tier 1 — mate-time attestation per module (backend-signed ledger entries)
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={onEnrolRealModule}
            className="btn-success px-3 py-1.5 text-sm"
          >
            Enrol real SE module
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={onEnrolSyntheticModules}
            className="btn-secondary px-3 py-1.5 text-sm"
          >
            Enrol synthetic modules
          </button>
          <button
            type="button"
            disabled={busy || modules.length === 0}
            onClick={onAttestAll}
            className="btn-primary px-3 py-1.5 text-sm"
          >
            Attest all
          </button>
        </div>
      </header>

      {error && (
        <p className="mb-4 rounded-md border border-trust-fail-border bg-trust-fail-bg px-3 py-2 text-sm text-trust-fail-text">
          {error}
        </p>
      )}

      {modules.length === 0 ? (
        <p className="text-sm text-ink-secondary">
          No modules enrolled. Enrol the real secure-element-backed module and synthetic
          stand-ins to begin assembly.
        </p>
      ) : (
        <ul className="space-y-3">
          {modules.map((mod) => {
            const selected = selectedModuleIds.includes(mod.module_id);
            return (
              <li
                key={mod.module_id}
                className="rounded-md border border-line bg-surface-inset p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <label className="flex cursor-pointer items-start gap-3">
                    <input
                      type="checkbox"
                      checked={selected}
                      onChange={() => onToggleModule(mod.module_id)}
                      className="mt-1 accent-accent"
                    />
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-sm font-semibold text-ink">
                          {mod.module_id}
                        </span>
                        {mod.isRealSecureElement && (
                          <span className="rounded-md border border-trust-ok-border bg-trust-ok-bg px-2 py-0.5 text-xs font-semibold uppercase tracking-wide text-trust-ok-text">
                            Real SE chain
                          </span>
                        )}
                        {mod.isSynthetic && (
                          <span className="rounded-md border border-trust-warn-border bg-trust-warn-bg px-2 py-0.5 text-xs font-semibold uppercase tracking-wide text-trust-warn-text">
                            Synthetic
                          </span>
                        )}
                      </div>
                      <p className="mt-1 font-mono text-xs text-ink-muted break-all">
                        {mod.public_key_hex}
                      </p>
                    </div>
                  </label>

                  <div className="flex flex-col items-end gap-2">
                    <span
                      className={`inline-flex items-center gap-1 rounded-md border px-2.5 py-1 text-xs font-semibold ${trustBadgeClasses(mod.attestation?.verified)}`}
                    >
                      <span aria-hidden="true">{trustIcon(mod.attestation?.verified)}</span>
                      {trustLabel(mod.attestation?.verified)}
                    </span>
                    {mod.attestation && (
                      <span className="text-xs text-ink-muted">
                        reason: {mod.attestation.reason}
                      </span>
                    )}
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => onAttestModule(mod.module_id)}
                      className="btn-secondary px-2 py-1 text-xs"
                    >
                      Attest
                    </button>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
