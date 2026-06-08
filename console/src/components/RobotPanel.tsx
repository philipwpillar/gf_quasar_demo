import type { EnrolledModule, FleetRobot } from "../types/quasarLedgerTypes";

interface RobotPanelProps {
  robot: FleetRobot;
  modules: EnrolledModule[];
  highlightFailure?: boolean;
}

function statusPill(ok: boolean | undefined, okLabel: string, failLabel: string) {
  if (ok === undefined) {
    return (
      <span className="inline-flex items-center gap-1 rounded-md border border-trust-neutral-border bg-trust-neutral-bg px-2.5 py-1 text-xs font-semibold text-trust-neutral-text">
        <span aria-hidden="true">○</span>
        Pending
      </span>
    );
  }
  if (ok) {
    return (
      <span className="inline-flex items-center gap-1 rounded-md border border-trust-ok-border bg-trust-ok-bg px-2.5 py-1 text-xs font-semibold text-trust-ok-text">
        <span aria-hidden="true">✓</span>
        {okLabel}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-md border border-trust-fail-border bg-trust-fail-bg px-2.5 py-1 text-xs font-semibold text-trust-fail-text">
      <span aria-hidden="true">✗</span>
      {failLabel}
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
          ? "border-trust-fail-border bg-trust-fail-bg"
          : "border-line bg-surface-card"
      }`}
    >
      <header className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-mono text-base font-semibold text-ink">{robot.robot_id}</h3>
            {robot.isSynthetic && (
              <span className="rounded-md border border-trust-warn-border bg-trust-warn-bg px-2 py-0.5 text-xs font-semibold uppercase text-trust-warn-text">
                Synthetic robot
              </span>
            )}
          </div>
          <p className="text-xs text-ink-muted">vendor: {robot.vendor_key_id}</p>
        </div>
        {statusPill(
          composition?.composed,
          "Composed (trusted)",
          "Not composed (untrusted)",
        )}
      </header>

      <div className="mb-4">
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-muted">
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
                className={`flex items-center justify-between rounded-md border px-3 py-2 text-sm ${
                  failed
                    ? "border-trust-fail-border bg-white text-trust-fail-text"
                    : "border-line bg-surface-inset text-ink-secondary"
                }`}
              >
                <span className="font-mono">{moduleId}</span>
                <span className="inline-flex items-center gap-1 text-xs font-medium">
                  {failed && <span aria-hidden="true">✗</span>}
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
          <p className="text-ink-secondary">
            <span className="font-semibold text-ink">Backend reasons: </span>
            {composition.reasons.join(" · ")}
          </p>
          <p className="font-mono text-xs text-ink-muted">
            ledger seq {composition.ledger_seq} · chain head {composition.chain_head.slice(0, 16)}…
          </p>
        </div>
      )}

      {failedModuleIds.length > 0 && (
        <p className="mt-4 flex items-start gap-2 rounded-md border border-trust-fail-border bg-white px-3 py-2 text-sm text-trust-fail-text">
          <span aria-hidden="true" className="mt-0.5">
            ✗
          </span>
          <span>
            Untrusted because module(s) failed mate-time attestation:{" "}
            <span className="font-mono font-semibold">{failedModuleIds.join(", ")}</span>
          </span>
        </p>
      )}
    </article>
  );
}
