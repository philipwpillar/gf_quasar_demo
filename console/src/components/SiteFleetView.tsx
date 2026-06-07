import type {
  EnrolledModule,
  FleetRobot,
  SiteAdmissionVerdict,
  SiteGateConfig,
} from "../types/quasarLedgerTypes";
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
      <span className="rounded bg-slate-700 px-2 py-1 text-xs font-semibold text-slate-200">
        Not admitted yet
      </span>
    );
  }
  return (
    <span
      className={`rounded px-2 py-1 text-xs font-semibold ${
        admitted
          ? "bg-emerald-900 text-emerald-100 border border-emerald-600"
          : "bg-rose-900 text-rose-100 border border-rose-600"
      }`}
    >
      {admitted ? "Admitted: true" : "Admitted: false (DENIED)"}
    </span>
  );
}

function findFailingModule(robot: FleetRobot): string | null {
  const ref = robot.composition?.module_refs.find((r) => !r.attested);
  return ref?.module_id ?? null;
}

function PropagationChain({
  robot,
  admission,
}: {
  robot: FleetRobot;
  admission?: SiteAdmissionVerdict;
}) {
  const failingModule = findFailingModule(robot);
  if (!failingModule || robot.composition?.composed !== false) {
    return null;
  }

  return (
    <div
      className="mb-6 rounded-lg border-2 border-rose-600 bg-rose-950/30 p-4"
      data-testid="propagation-chain"
    >
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-rose-200">
        Propagating failure chain (backend-signed verdicts)
      </h3>
      <ol className="space-y-3">
        <li className="flex flex-wrap items-center gap-2 text-sm">
          <span className="rounded bg-rose-900 px-2 py-1 font-mono text-xs text-rose-100 border border-rose-600">
            Tier 1 · Module
          </span>
          <span className="font-mono font-semibold text-rose-100">{failingModule}</span>
          <span className="text-rose-200">mate-time attestation FAILED</span>
          <span aria-hidden="true" className="text-rose-400">
            →
          </span>
        </li>
        <li className="flex flex-wrap items-center gap-2 text-sm">
          <span className="rounded bg-rose-900 px-2 py-1 font-mono text-xs text-rose-100 border border-rose-600">
            Tier 2 · Robot
          </span>
          <span className="font-mono font-semibold text-rose-100">{robot.robot_id}</span>
          <span className="text-rose-200">NOT COMPOSED (untrusted)</span>
          <span aria-hidden="true" className="text-rose-400">
            →
          </span>
        </li>
        <li className="flex flex-wrap items-center gap-2 text-sm">
          <span className="rounded bg-rose-900 px-2 py-1 font-mono text-xs text-rose-100 border border-rose-600">
            Tier 3 · Site gate
          </span>
          <span className="font-mono font-semibold text-rose-100">{robot.robot_id}</span>
          <span className="text-rose-200">
            {admission?.admitted === false
              ? "DENIED site admission"
              : "admission pending"}
          </span>
        </li>
      </ol>
      {admission && (
        <p className="mt-3 text-sm text-rose-100">
          <span className="font-semibold">Signed site verdict reasons: </span>
          {admission.reasons.join(" · ")}
        </p>
      )}
      <p className="mt-2 text-xs text-rose-300/80">
        Each tier&apos;s ledger entry is behind this chain — inspect the ledger below.
      </p>
    </div>
  );
}

export default function SiteFleetView({
  gate,
  robots,
  modules,
  propagationRobotId,
}: SiteFleetViewProps) {
  const propagationRobot = robots.find((r) => r.robot_id === propagationRobotId);

  return (
    <section className="rounded-lg border border-slate-700 bg-slate-900 p-4">
      <header className="mb-4">
        <h2 className="text-lg font-semibold text-slate-100">Site fleet view</h2>
        <p className="text-sm text-slate-400">
          Tier 3 site gate — task class and zone from backend policy (stub breadth)
        </p>
      </header>

      <div className="mb-4 flex flex-wrap items-center gap-3 rounded border border-slate-700 bg-slate-950 p-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">Site gate</p>
          <p className="font-mono text-sm text-slate-200">
            task_class={gate.task_class} · zone={gate.zone}
          </p>
        </div>
        <span className="rounded bg-amber-950 px-2 py-1 text-xs font-semibold uppercase text-amber-300 border border-amber-700">
          policy_mode: {POLICY_MODE_STUB}
        </span>
      </div>

      {propagationRobot && (
        <PropagationChain
          robot={propagationRobot}
          admission={propagationRobot.admission}
        />
      )}

      {robots.length === 0 ? (
        <p className="text-sm text-slate-400">No robots on site yet. Compose and admit below.</p>
      ) : (
        <div className="space-y-6">
          {robots.map((robot) => (
            <div key={robot.robot_id} className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2 rounded border border-slate-700 bg-slate-950 p-3">
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500">
                    Site admission verdict
                  </p>
                  <p className="font-mono text-sm text-slate-200">{robot.robot_id}</p>
                </div>
                {admissionPill(robot.admission?.admitted)}
              </div>

              {robot.admission && (
                <div className="rounded border border-slate-700 bg-slate-950 p-3 text-sm text-slate-300">
                  <p>
                    <span className="font-semibold text-slate-400">Backend reasons: </span>
                    {robot.admission.reasons.join(" · ")}
                  </p>
                  <p className="mt-1 font-mono text-xs text-slate-500">
                    policy_mode={robot.admission.policy_mode} · ledger seq{" "}
                    {robot.admission.ledger_seq}
                  </p>
                  <p className="mt-1 font-mono text-xs text-slate-600 break-all">
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
