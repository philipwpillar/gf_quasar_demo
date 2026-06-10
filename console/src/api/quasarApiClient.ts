import type {
  AttestationResult,
  ClearanceRequest,
  ClearanceVerdict,
  ComposeRobotRequest,
  EnrolResponse,
  RevokeModuleResponse,
  LedgerEntry,
  LedgerVerifyResponse,
  NarratorAnswer,
  NarratorQuery,
  RobotComposition,
  SiteAdmissionRequest,
  SiteAdmissionVerdict,
  VendorEnrolResponse,
} from "../types/quasarLedgerTypes";

const API_BASE =
  import.meta.env.VITE_QUASAR_API_BASE?.trim() || "http://localhost:8000";

async function requestJson<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { message?: string; detail?: string };
      detail = body.message ?? body.detail ?? detail;
    } catch {
      // keep statusText
    }
    throw new Error(`${response.status}: ${detail}`);
  }

  return (await response.json()) as T;
}

export function getApiBase(): string {
  return API_BASE;
}

export async function healthCheck(): Promise<{ status: string }> {
  return requestJson("/healthz");
}

export async function enrolModule(moduleId: string): Promise<EnrolResponse> {
  return requestJson("/modules/enrol", {
    method: "POST",
    body: JSON.stringify({ module_id: moduleId }),
  });
}

export async function revokeModule(
  moduleId: string,
  reason: string,
): Promise<RevokeModuleResponse> {
  return requestJson("/modules/revoke", {
    method: "POST",
    body: JSON.stringify({ module_id: moduleId, reason }),
  });
}

export async function attestModule(moduleId: string): Promise<AttestationResult> {
  return requestJson("/attest", {
    method: "POST",
    body: JSON.stringify({ module_id: moduleId }),
  });
}

export async function corruptModuleSigner(
  moduleId: string,
): Promise<{ module_id: string; message: string }> {
  return requestJson("/dev/corrupt-module-signer", {
    method: "POST",
    body: JSON.stringify({ module_id: moduleId }),
  });
}

export async function enrolVendor(vendorId: string): Promise<VendorEnrolResponse> {
  return requestJson("/vendors/enrol", {
    method: "POST",
    body: JSON.stringify({ vendor_id: vendorId }),
  });
}

export async function corruptVendorSigner(
  vendorId: string,
): Promise<{ vendor_id: string; message: string }> {
  return requestJson("/dev/corrupt-vendor-signer", {
    method: "POST",
    body: JSON.stringify({ vendor_id: vendorId }),
  });
}

export async function composeRobot(
  body: ComposeRobotRequest,
): Promise<RobotComposition> {
  return requestJson("/robots/compose", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function admitRobot(
  body: SiteAdmissionRequest,
): Promise<SiteAdmissionVerdict> {
  return requestJson("/site/admit", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function requestClearance(
  body: ClearanceRequest,
): Promise<ClearanceVerdict> {
  return requestJson("/clearance", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function verifyLedger(): Promise<LedgerVerifyResponse> {
  return requestJson("/ledger/verify");
}

export async function exportLedger(): Promise<LedgerEntry[]> {
  return requestJson("/ledger/export");
}

export async function queryAssistant(
  question: string,
  scope?: Pick<NarratorQuery, "config_id" | "robot_id">,
): Promise<NarratorAnswer> {
  const body: NarratorQuery = { question, ...scope };
  return requestJson("/assistant/query", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
