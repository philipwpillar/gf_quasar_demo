import type { EnrolledModule, FleetRobot } from "../types/quasarLedgerTypes";

interface RobotPanelProps {
  robot: FleetRobot;
  modules: EnrolledModule[];
  highlightFailure?: boolean;
}

function statusPill(ok: boolean | undefined, okLabel: string, failLabel: string) {
  if (ok === undefined) {
    return (
      <span className="rounded bg-slate-700 px-2 py-1 text-xs font-semibold text-slate-200">
        Pending
      </span>
    );
  }
  return (
    <span
      className={`rounded px-2 py-1 text-xs font-semibold ${
        ok
          ? "bg-emerald-900 text-emerald-100 border border-emerald-600"
          : "bg-rose-900 text-rose-100 border border-rose-600"
      }`}
    >
      {ok ? okLabel : failLabel}
    </span>
  );
}

export default function RobotPanel({
  robot,
  modules,
  highlightFailure = false,
}: RobotPanelProps) {
  const composition = robot.composition;
  const failedModuleIds =
    composition?.module_refs.filter((ref) => !ref.attested).map((ref) => ref.module_id) ??
    [];

  return (
    <article
      className={`rounded-lg border p-4 ${
        highlightFailure && composition && !composition.composed
          ? "border-rose-600 bg-rose-950/40"
          : "border-slate-700 bg-slate-900"
      }`}
    >
      <header className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-mono text-base font-semibold text-slate-100">
              {robot.robot_id}
            </h3>
            {robot.isSynthetic && (
              <span className="rounded bg-amber-950 px-2 py-0.5 text-xs font-semibold uppercase text-amber-300 border border-amber-700">
                Synthetic robot
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400">vendor: {robot.vendor_key_id}</p>
        </div>
        {statusPill(
          composition?.composed,
          "Composed (trusted)",
          "Not composed (untrusted)",
        )}
      </header>

      <div className="mb-3">
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
          Constituent modules
        </h4>
        <ul className="space-y-2">
          {robot.module_ids.map((moduleId) => {
            const mod = modules.find((m) => m.module_id === moduleId);
            const ref = composition?.module_refs.find((r) => r.module_id === moduleId);
            const failed = ref ? !ref.attested : false;
            return (
              <li
                key={moduleId}
                className={`flex items-center justify-between rounded border px-2 py-1.5 text-sm ${
                  failed
                    ? "border-rose-600 bg-rose-950/50 text-rose-100"
                    : "border-slate-700 bg-slate-950 text-slate-200"
                }`}
              >
                <span className="font-mono">{moduleId}</span>
                <span className="text-xs">
                  {ref
                    ? ref.attested
                      ? "attested"
                      : "FAILED attestation"
                    : mod?.attestation
                      ? mod.attestation.verified
                        ? "attested (pre-compose)"
                        : "failed (pre-compose)"
                      : "—"}
                </span>
              </li>
            );
          })}
        </ul>
      </div>

      {composition && (
        <div className="space-y-2 text-sm">
          <p className="text-slate-300">
            <span className="font-semibold text-slate-400">Backend reasons: </span>
            {composition.reasons.join(" · ")}
          </p>
          <p className="font-mono text-xs text-slate-500">
            ledger seq {composition.ledger_seq} · chain head {composition.chain_head.slice(0, 16)}…
          </p>
        </div>
      )}

      {failedModuleIds.length > 0 && (
        <p className="mt-3 rounded border border-rose-700 bg-rose-950 px-2 py-1.5 text-sm text-rose-100">
          Untrusted because module(s) failed mate-time attestation:{" "}
          <span className="font-mono font-semibold">{failedModuleIds.join(", ")}</span>
        </p>
      )}
    </article>
  );
}
