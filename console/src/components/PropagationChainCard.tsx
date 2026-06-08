import type { FleetRobot, SiteAdmissionVerdict } from "../types/quasarLedgerTypes";

function findFailingModule(robot: FleetRobot): string | null {
  const ref = robot.composition?.module_refs.find((r) => !r.attested);
  return ref?.module_id ?? null;
}

interface PropagationChainCardProps {
  robot: FleetRobot;
  admission?: SiteAdmissionVerdict;
}

export default function PropagationChainCard({
  robot,
  admission,
}: PropagationChainCardProps) {
  const failingModule = findFailingModule(robot);
  if (!failingModule || robot.composition?.composed !== false) {
    return null;
  }

  return (
    <section className="card h-full">
      <header className="mb-4">
        <h2 className="section-title">Propagating failure chain</h2>
        <p className="section-subtitle">Backend-signed verdicts across Tier 1 → 2 → 3</p>
      </header>

      <div
        className="rounded-lg border-2 border-trust-fail-border bg-trust-fail-bg p-5"
        data-testid="propagation-chain"
      >
        <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-trust-fail-text">
          <span aria-hidden="true">✗</span>
          Propagating failure chain (backend-signed verdicts)
        </h3>
        <ol className="relative space-y-4 border-l-2 border-trust-fail-border/40 pl-5">
          <li className="flex flex-wrap items-center gap-2 text-sm">
            <span className="rounded-md border border-trust-fail-border bg-white px-2 py-1 font-mono text-xs font-semibold text-trust-fail-text">
              Tier 1 · Module
            </span>
            <span className="font-mono font-semibold text-ink">{failingModule}</span>
            <span className="text-trust-fail-text">mate-time attestation FAILED</span>
            <span aria-hidden="true" className="text-trust-fail-border">
              ↓
            </span>
          </li>
          <li className="flex flex-wrap items-center gap-2 text-sm">
            <span className="rounded-md border border-trust-fail-border bg-white px-2 py-1 font-mono text-xs font-semibold text-trust-fail-text">
              Tier 2 · Robot
            </span>
            <span className="font-mono font-semibold text-ink">{robot.robot_id}</span>
            <span className="text-trust-fail-text">NOT COMPOSED (untrusted)</span>
            <span aria-hidden="true" className="text-trust-fail-border">
              ↓
            </span>
          </li>
          <li className="flex flex-wrap items-center gap-2 text-sm">
            <span className="rounded-md border border-trust-fail-border bg-white px-2 py-1 font-mono text-xs font-semibold text-trust-fail-text">
              Tier 3 · Site gate
            </span>
            <span className="font-mono font-semibold text-ink">{robot.robot_id}</span>
            <span className="text-trust-fail-text">
              {admission?.admitted === false
                ? "DENIED site admission"
                : "admission pending"}
            </span>
          </li>
        </ol>
        {admission && (
          <p className="mt-4 text-sm text-ink-secondary">
            <span className="font-semibold text-ink">Signed site verdict reasons: </span>
            {admission.reasons.join(" · ")}
          </p>
        )}
        <p className="mt-2 text-xs text-ink-muted">
          Each tier&apos;s ledger entry is behind this chain — inspect the ledger below.
        </p>
      </div>
    </section>
  );
}
