import { useCallback, useEffect, useState } from "react";

import {
  admitRobot,
  attestModule,
  composeRobot,
  corruptModuleSigner,
  enrolModule,
  healthCheck,
} from "./api/quasarApiClient";
import LedgerInspector, { fetchLedgerState } from "./components/LedgerInspector";
import ModuleAssemblyPanel from "./components/ModuleAssemblyPanel";
import PropagationChainCard from "./components/PropagationChainCard";
import QuasarAppBar from "./components/QuasarAppBar";
import QuasarFloatingNarrator from "./components/QuasarFloatingNarrator";
import QuasarSidebar, { type ShellSection } from "./components/QuasarSidebar";
import SiteFleetView from "./components/SiteFleetView";
import type {
  EnrolledModule,
  FleetRobot,
  LedgerEntry,
  LedgerVerifyResponse,
  SiteGateConfig,
} from "./types/quasarLedgerTypes";

const REAL_MODULE_ID = "mod-secure-001";
const SYNTHETIC_MODULE_IDS = ["mod-synth-002", "mod-synth-003"] as const;
const DEFAULT_GATE: SiteGateConfig = {
  task_class: "industrial_inspection",
  zone: "zone_b",
};
const PROPAGATION_ROBOT_ID = "robot-propagation-demo";
const TRUSTED_ROBOT_ID = "robot-trusted-demo";

export default function App() {
  const [modules, setModules] = useState<EnrolledModule[]>([]);
  const [selectedModuleIds, setSelectedModuleIds] = useState<string[]>([]);
  const [robots, setRobots] = useState<FleetRobot[]>([]);
  const [propagationRobotId, setPropagationRobotId] = useState<string | null>(null);
  const [ledgerEntries, setLedgerEntries] = useState<LedgerEntry[]>([]);
  const [ledgerVerify, setLedgerVerify] = useState<LedgerVerifyResponse | null>(null);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<ShellSection>("site-fleet");

  const propagationRobot = robots.find((r) => r.robot_id === propagationRobotId);

  const refreshLedger = useCallback(async () => {
    const { entries, verifyResult } = await fetchLedgerState();
    setLedgerEntries(entries);
    setLedgerVerify(verifyResult);
  }, []);

  useEffect(() => {
    healthCheck()
      .then(() => setApiOnline(true))
      .catch(() => setApiOnline(false));
  }, []);

  function navigateToSection(section: ShellSection) {
    setActiveSection(section);
  }

  async function withBusy<T>(fn: () => Promise<T>): Promise<T | undefined> {
    setBusy(true);
    setError(null);
    try {
      const result = await fn();
      await refreshLedger();
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      return undefined;
    } finally {
      setBusy(false);
    }
  }

  function toggleModule(moduleId: string) {
    setSelectedModuleIds((prev) =>
      prev.includes(moduleId)
        ? prev.filter((id) => id !== moduleId)
        : [...prev, moduleId],
    );
  }

  async function handleEnrolRealModule() {
    await withBusy(async () => {
      const response = await enrolModule(REAL_MODULE_ID);
      setModules((prev) => {
        if (prev.some((m) => m.module_id === response.module_id)) {
          return prev;
        }
        return [
          ...prev,
          {
            module_id: response.module_id,
            public_key_hex: response.public_key_hex,
            isRealSecureElement: true,
            isSynthetic: false,
          },
        ];
      });
      setSelectedModuleIds((prev) =>
        prev.includes(REAL_MODULE_ID) ? prev : [...prev, REAL_MODULE_ID],
      );
      setStatusMessage(`Enrolled real secure-element-backed module ${REAL_MODULE_ID}`);
    });
  }

  async function handleEnrolSyntheticModules() {
    await withBusy(async () => {
      for (const moduleId of SYNTHETIC_MODULE_IDS) {
        try {
          const response = await enrolModule(moduleId);
          setModules((prev) => {
            if (prev.some((m) => m.module_id === response.module_id)) {
              return prev;
            }
            return [
              ...prev,
              {
                module_id: response.module_id,
                public_key_hex: response.public_key_hex,
                isRealSecureElement: false,
                isSynthetic: true,
              },
            ];
          });
        } catch (err) {
          const message = err instanceof Error ? err.message : String(err);
          if (!message.includes("409")) {
            throw err;
          }
        }
      }
      setSelectedModuleIds((prev) => {
        const merged = new Set([...prev, ...SYNTHETIC_MODULE_IDS]);
        return [...merged];
      });
      setStatusMessage("Enrolled synthetic module stand-ins (labelled on screen)");
    });
  }

  async function handleAttestModule(moduleId: string) {
    await withBusy(async () => {
      const result = await attestModule(moduleId);
      setModules((prev) =>
        prev.map((m) =>
          m.module_id === moduleId ? { ...m, attestation: result } : m,
        ),
      );
    });
  }

  async function handleAttestAll() {
    for (const mod of modules) {
      await handleAttestModule(mod.module_id);
    }
  }

  async function handleComposeRobot(robotId: string, isSynthetic: boolean) {
    if (selectedModuleIds.length === 0) {
      setError("Select at least one module to compose a robot.");
      return;
    }
    await withBusy(async () => {
      const composition = await composeRobot({
        robot_id: robotId,
        vendor_key_id: isSynthetic ? "vendor-synth-demo" : "vendor-acme",
        module_ids: selectedModuleIds,
      });
      setRobots((prev) => {
        const existing = prev.find((r) => r.robot_id === robotId);
        const next: FleetRobot = {
          robot_id: robotId,
          vendor_key_id: isSynthetic ? "vendor-synth-demo" : "vendor-acme",
          module_ids: [...selectedModuleIds],
          composition,
          admission: existing?.admission,
          isSynthetic,
        };
        return [...prev.filter((r) => r.robot_id !== robotId), next];
      });
      setStatusMessage(
        `Robot ${robotId} composed — backend composed=${composition.composed}`,
      );
    });
  }

  async function handleAdmitRobot(robotId: string) {
    const robot = robots.find((r) => r.robot_id === robotId);
    if (!robot?.composition) {
      setError("Compose the robot before admitting to site.");
      return;
    }
    await withBusy(async () => {
      const admission = await admitRobot({
        robot_id: robotId,
        task_class: DEFAULT_GATE.task_class,
        zone: DEFAULT_GATE.zone,
        robot_composed_seq: robot.composition!.ledger_seq,
      });
      setRobots((prev) =>
        prev.map((r) => (r.robot_id === robotId ? { ...r, admission } : r)),
      );
      setStatusMessage(
        `Site admission for ${robotId} — backend admitted=${admission.admitted}`,
      );
    });
  }

  async function ensureEnrolled(
    moduleId: string,
    isReal: boolean,
  ): Promise<void> {
    try {
      const response = await enrolModule(moduleId);
      setModules((prev) => {
        if (prev.some((m) => m.module_id === response.module_id)) {
          return prev;
        }
        return [
          ...prev,
          {
            module_id: response.module_id,
            public_key_hex: response.public_key_hex,
            isRealSecureElement: isReal,
            isSynthetic: !isReal,
          },
        ];
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      if (!message.includes("409")) {
        throw err;
      }
    }
  }

  async function handlePropagationDemo() {
    setPropagationRobotId(PROPAGATION_ROBOT_ID);
    setSelectedModuleIds([REAL_MODULE_ID, SYNTHETIC_MODULE_IDS[0]]);

    await withBusy(async () => {
      await ensureEnrolled(REAL_MODULE_ID, true);
      await ensureEnrolled(SYNTHETIC_MODULE_IDS[0], false);

      try {
        await corruptModuleSigner(SYNTHETIC_MODULE_IDS[0]);
        setStatusMessage(
          `Dev hook: corrupted signer for ${SYNTHETIC_MODULE_IDS[0]} — next compose will fail attestation`,
        );
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        if (message.includes("404")) {
          setError(
            "Propagation demo requires QUASAR_ENABLE_DEV_HOOKS=1 on the API server.",
          );
          return;
        }
        throw err;
      }

      const composition = await composeRobot({
        robot_id: PROPAGATION_ROBOT_ID,
        vendor_key_id: "vendor-synth-demo",
        module_ids: [REAL_MODULE_ID, SYNTHETIC_MODULE_IDS[0]],
      });

      const admission = await admitRobot({
        robot_id: PROPAGATION_ROBOT_ID,
        task_class: DEFAULT_GATE.task_class,
        zone: DEFAULT_GATE.zone,
        robot_composed_seq: composition.ledger_seq,
      });

      setRobots((prev) => [
        ...prev.filter((r) => r.robot_id !== PROPAGATION_ROBOT_ID),
        {
          robot_id: PROPAGATION_ROBOT_ID,
          vendor_key_id: "vendor-synth-demo",
          module_ids: [REAL_MODULE_ID, SYNTHETIC_MODULE_IDS[0]],
          composition,
          admission,
          isSynthetic: true,
        },
      ]);

      setModules((prev) =>
        prev.map((m) => {
          const ref = composition.module_refs.find(
            (r) => r.module_id === m.module_id,
          );
          if (!ref) {
            return m;
          }
          return {
            ...m,
            attestation: {
              module_id: m.module_id,
              verified: ref.attested,
              reason: ref.attested ? "ok" : "signature_invalid",
              challenge_nonce_hex: "",
              verified_at: new Date().toISOString(),
            },
          };
        }),
      );
    });
  }

  async function handleTrustedDemo() {
    setPropagationRobotId(null);
    setSelectedModuleIds([REAL_MODULE_ID]);
    await withBusy(async () => {
      await ensureEnrolled(REAL_MODULE_ID, true);
      const composition = await composeRobot({
        robot_id: TRUSTED_ROBOT_ID,
        vendor_key_id: "vendor-acme",
        module_ids: [REAL_MODULE_ID],
      });
      const admission = await admitRobot({
        robot_id: TRUSTED_ROBOT_ID,
        task_class: DEFAULT_GATE.task_class,
        zone: DEFAULT_GATE.zone,
        robot_composed_seq: composition.ledger_seq,
      });
      setRobots((prev) => [
        ...prev.filter((r) => r.robot_id !== TRUSTED_ROBOT_ID),
        {
          robot_id: TRUSTED_ROBOT_ID,
          vendor_key_id: "vendor-acme",
          module_ids: [REAL_MODULE_ID],
          composition,
          admission,
          isSynthetic: false,
        },
      ]);
      setStatusMessage("Trusted path complete — real module composed and admitted");
    });
  }

  return (
    <div className="shell-root">
      <QuasarAppBar apiOnline={apiOnline} />

      <div className="shell-body">
        <QuasarSidebar activeSection={activeSection} onNavigate={navigateToSection} />

        <main className="shell-main">
          <div className="shell-toolbar">
            <button
              type="button"
              disabled={busy}
              onClick={handlePropagationDemo}
              className="btn-primary"
            >
              Run propagating-failure demo
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={handleTrustedDemo}
              className="btn-primary"
            >
              Run trusted-path demo
            </button>
            <button
              type="button"
              disabled={busy || selectedModuleIds.length === 0}
              onClick={() => handleComposeRobot("robot-manual", true)}
              className="btn-secondary"
            >
              Compose selected robot
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => handleAdmitRobot(PROPAGATION_ROBOT_ID)}
              className="btn-secondary"
            >
              Admit propagation robot
            </button>
          </div>

          {statusMessage && (
            <p className="mb-4 rounded-md border border-accent/20 bg-accent-subtle px-3 py-2 text-sm text-accent">
              {statusMessage}
            </p>
          )}

          {error && (
            <p className="mb-4 rounded-md border border-trust-fail-border bg-trust-fail-bg px-3 py-2 text-sm text-trust-fail-text">
              {error}
            </p>
          )}

          <div className="shell-page">
            {activeSection === "site-fleet" && (
              <>
                <SiteFleetView
                  gate={DEFAULT_GATE}
                  robots={robots}
                  modules={modules}
                  propagationRobotId={propagationRobotId}
                />
                {propagationRobot && (
                  <PropagationChainCard
                    robot={propagationRobot}
                    admission={propagationRobot.admission}
                  />
                )}
              </>
            )}

            {activeSection === "module-assembly" && (
              <ModuleAssemblyPanel
                modules={modules}
                selectedModuleIds={selectedModuleIds}
                onToggleModule={toggleModule}
                onEnrolRealModule={handleEnrolRealModule}
                onEnrolSyntheticModules={handleEnrolSyntheticModules}
                onAttestModule={handleAttestModule}
                onAttestAll={handleAttestAll}
                busy={busy}
                error={null}
              />
            )}

            {activeSection === "ledger" && (
              <LedgerInspector
                entries={ledgerEntries}
                verifyResult={ledgerVerify}
                onRefresh={refreshLedger}
                busy={busy}
              />
            )}
          </div>
        </main>
      </div>

      <QuasarFloatingNarrator />
    </div>
  );
}
