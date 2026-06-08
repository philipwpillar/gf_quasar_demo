import type { EnrolledModule, FleetRobot, SiteGateConfig } from "../types/quasarLedgerTypes";
import { POLICY_MODE_STUB } from "../types/quasarLedgerTypes";

import RobotPanel from "./RobotPanel";

interface SiteFleetViewProps {
  gate: SiteGateConfig;
  robots: FleetRobot[];
  modules: EnrolledModule[];
  propagationRobotId: string | null;
}

function admissionPill(admitted: boolean | undefined) {
  if (admitted === undefined) {
    return (
      <span className="inline-flex items-center gap-1 rounded-md border border-trust-neutral-border bg-trust-neutral-bg px-2.5 py-1 text-xs font-semibold text-trust-neutral-text">
        <span aria-hidden="true">○</span>
        Not admitted yet
      </span>
    );
  }
  if (admitted) {
    return (
      <span className="inline-flex items-center gap-1 rounded-md border border-trust-ok-border bg-trust-ok-bg px-2.5 py-1 text-xs font-semibold text-trust-ok-text">
        <span aria-hidden="true">✓</span>
        Admitted: true
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-md border border-trust-fail-border bg-trust-fail-bg px-2.5 py-1 text-xs font-semibold text-trust-fail-text">
      <span aria-hidden="true">✗</span>
      Admitted: false (DENIED)
    </span>
  );
}

export default function SiteFleetView({
  gate,
  robots,
  modules,
  propagationRobotId,
}: SiteFleetViewProps) {
  return (
    <section className="card h-full">
      <header className="mb-5">
        <h2 className="section-title">Site fleet view</h2>
        <p className="section-subtitle">
          Tier 3 site gate — task class and zone from backend policy (stub breadth)
        </p>
      </header>

      <div className="mb-5 flex flex-wrap items-center gap-3 rounded-md border border-line bg-surface-inset p-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">Site gate</p>
          <p className="font-mono text-sm text-ink">
            task_class={gate.task_class} · zone={gate.zone}
          </p>
        </div>
        <span className="rounded-md border border-trust-warn-border bg-trust-warn-bg px-2.5 py-1 text-xs font-semibold uppercase tracking-wide text-trust-warn-text">
          policy_mode: {POLICY_MODE_STUB}
        </span>
      </div>

      {robots.length === 0 ? (
        <p className="text-sm text-ink-secondary">No robots on site yet. Compose and admit below.</p>
      ) : (
        <div className="space-y-6">
          {robots.map((robot) => (
            <div key={robot.robot_id} className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-line bg-surface-inset p-4">
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
                    Site admission verdict
                  </p>
                  <p className="font-mono text-sm font-medium text-ink">{robot.robot_id}</p>
                </div>
                {admissionPill(robot.admission?.admitted)}
              </div>

              {robot.admission && (
                <div className="rounded-md border border-line bg-surface-card p-4 text-sm text-ink-secondary">
                  <p>
                    <span className="font-semibold text-ink">Backend reasons: </span>
                    {robot.admission.reasons.join(" · ")}
                  </p>
                  <p className="mt-1.5 font-mono text-xs text-ink-muted">
                    policy_mode={robot.admission.policy_mode} · ledger seq{" "}
                    {robot.admission.ledger_seq}
                  </p>
                  <p className="mt-1 font-mono text-xs text-ink-faint break-all">
                    signature {robot.admission.signature_hex.slice(0, 24)}…
                  </p>
                </div>
              )}

              <RobotPanel
                robot={robot}
                modules={modules}
                highlightFailure={robot.robot_id === propagationRobotId}
              />
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
