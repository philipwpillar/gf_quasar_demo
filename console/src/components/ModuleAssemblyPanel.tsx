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

function trustBadge(verified: boolean | undefined): string {
  if (verified === undefined) {
    return "bg-slate-700 text-slate-200";
  }
  return verified
    ? "bg-emerald-900 text-emerald-100 border border-emerald-600"
    : "bg-rose-900 text-rose-100 border border-rose-600";
}

function trustLabel(verified: boolean | undefined): string {
  if (verified === undefined) {
    return "Not attested yet";
  }
  return verified ? "Verified: true" : "Verified: false";
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
    <section className="rounded-lg border border-slate-700 bg-slate-900 p-4">
      <header className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold text-slate-100">Module assembly</h2>
          <p className="text-sm text-slate-400">
            Tier 1 — mate-time attestation per module (backend-signed ledger entries)
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={onEnrolRealModule}
            className="rounded bg-emerald-800 px-3 py-1.5 text-sm font-medium text-emerald-50 hover:bg-emerald-700 disabled:opacity-50"
          >
            Enrol real SE module
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={onEnrolSyntheticModules}
            className="rounded bg-slate-700 px-3 py-1.5 text-sm font-medium text-slate-100 hover:bg-slate-600 disabled:opacity-50"
          >
            Enrol synthetic modules
          </button>
          <button
            type="button"
            disabled={busy || modules.length === 0}
            onClick={onAttestAll}
            className="rounded bg-indigo-800 px-3 py-1.5 text-sm font-medium text-indigo-50 hover:bg-indigo-700 disabled:opacity-50"
          >
            Attest all
          </button>
        </div>
      </header>

      {error && (
        <p className="mb-3 rounded border border-rose-700 bg-rose-950 px-3 py-2 text-sm text-rose-200">
          {error}
        </p>
      )}

      {modules.length === 0 ? (
        <p className="text-sm text-slate-400">
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
                className="rounded border border-slate-700 bg-slate-950 p-3"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <label className="flex cursor-pointer items-start gap-3">
                    <input
                      type="checkbox"
                      checked={selected}
                      onChange={() => onToggleModule(mod.module_id)}
                      className="mt-1"
                    />
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-sm font-semibold text-slate-100">
                          {mod.module_id}
                        </span>
                        {mod.isRealSecureElement && (
                          <span className="rounded bg-emerald-950 px-2 py-0.5 text-xs font-semibold uppercase tracking-wide text-emerald-300 border border-emerald-700">
                            Real SE chain
                          </span>
                        )}
                        {mod.isSynthetic && (
                          <span className="rounded bg-amber-950 px-2 py-0.5 text-xs font-semibold uppercase tracking-wide text-amber-300 border border-amber-700">
                            Synthetic
                          </span>
                        )}
                      </div>
                      <p className="mt-1 font-mono text-xs text-slate-500 break-all">
                        {mod.public_key_hex}
                      </p>
                    </div>
                  </label>

                  <div className="flex flex-col items-end gap-2">
                    <span
                      className={`rounded px-2 py-1 text-xs font-semibold ${trustBadge(mod.attestation?.verified)}`}
                    >
                      {trustLabel(mod.attestation?.verified)}
                    </span>
                    {mod.attestation && (
                      <span className="text-xs text-slate-400">
                        reason: {mod.attestation.reason}
                      </span>
                    )}
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => onAttestModule(mod.module_id)}
                      className="rounded bg-slate-700 px-2 py-1 text-xs text-slate-100 hover:bg-slate-600 disabled:opacity-50"
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
