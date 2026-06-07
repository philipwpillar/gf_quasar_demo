import { useCallback, useEffect, useState } from "react";

import {
  admitRobot,
  attestModule,
  composeRobot,
  corruptModuleSigner,
  enrolModule,
  getApiBase,
  healthCheck,
} from "./api/quasarApiClient";
import LedgerInspector, { fetchLedgerState } from "./components/LedgerInspector";
import ModuleAssemblyPanel from "./components/ModuleAssemblyPanel";
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
    <div className="mx-auto min-h-screen max-w-6xl px-4 py-6">
      <header className="mb-6 border-b border-slate-800 pb-4">
        <h1 className="text-2xl font-bold text-slate-50">
          GravitonForge Quasar — Fleet Console
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          Operator view over the trust gateway. Verdicts are backend-computed and signed —
          this console does not decide clearance.
        </p>
        <div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-500">
          <span>
            API: <span className="font-mono text-slate-400">{getApiBase()}</span>
          </span>
          <span>
            Status:{" "}
            {apiOnline === null ? (
              "checking…"
            ) : apiOnline ? (
              <span className="text-emerald-400">connected</span>
            ) : (
              <span className="text-rose-400">offline</span>
            )}
          </span>
          <span className="rounded bg-amber-950 px-2 py-0.5 text-amber-300 border border-amber-800">
            STUB disclosure: policy breadth = stub_curated_single_task
          </span>
        </div>
      </header>

      <div className="mb-4 flex flex-wrap gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={handlePropagationDemo}
          className="rounded bg-rose-800 px-4 py-2 text-sm font-semibold text-rose-50 hover:bg-rose-700 disabled:opacity-50"
        >
          Run propagating-failure demo
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={handleTrustedDemo}
          className="rounded bg-emerald-800 px-4 py-2 text-sm font-semibold text-emerald-50 hover:bg-emerald-700 disabled:opacity-50"
        >
          Run trusted-path demo
        </button>
        <button
          type="button"
          disabled={busy || selectedModuleIds.length === 0}
          onClick={() => handleComposeRobot("robot-manual", true)}
          className="rounded bg-slate-700 px-4 py-2 text-sm text-slate-100 hover:bg-slate-600 disabled:opacity-50"
        >
          Compose selected robot
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => handleAdmitRobot(PROPAGATION_ROBOT_ID)}
          className="rounded bg-slate-700 px-4 py-2 text-sm text-slate-100 hover:bg-slate-600 disabled:opacity-50"
        >
          Admit propagation robot
        </button>
      </div>

      {statusMessage && (
        <p className="mb-3 rounded border border-indigo-800 bg-indigo-950 px-3 py-2 text-sm text-indigo-100">
          {statusMessage}
        </p>
      )}

      {error && (
        <p className="mb-3 rounded border border-rose-700 bg-rose-950 px-3 py-2 text-sm text-rose-200">
          {error}
        </p>
      )}

      <div className="space-y-6">
        <SiteFleetView
          gate={DEFAULT_GATE}
          robots={robots}
          modules={modules}
          propagationRobotId={propagationRobotId}
        />

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

        <LedgerInspector
          entries={ledgerEntries}
          verifyResult={ledgerVerify}
          onRefresh={refreshLedger}
          busy={busy}
        />
      </div>
    </div>
  );
}
