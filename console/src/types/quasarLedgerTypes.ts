/** TypeScript mirrors of backend Pydantic models — keep faithful to the API contract. */

export type EntryKind =
  | "module_enrolled"
  | "attestation"
  | "robot_composed"
  | "site_admission"
  | "clearance_decision"
  | "telemetry"
  | "decommission";

export interface LedgerEntry {
  seq: number;
  kind: EntryKind;
  occurred_at: string;
  config_id: string;
  payload: Record<string, unknown>;
  prev_hash: string;
  entry_hash: string;
}

export interface LedgerVerifyResponse {
  intact: boolean;
  first_broken_seq: number | null;
}

export interface ModuleAttestationRef {
  module_id: string;
  attested: boolean;
  ledger_seq: number;
}

export const POLICY_MODE_STUB = "stub_curated_single_task" as const;

export interface ClearanceRequest {
  config_id: string;
  module_ids: string[];
  task_class: string;
  zone: string;
}

export interface ClearanceVerdict {
  config_id: string;
  cleared: boolean;
  reasons: string[];
  attestation_refs: ModuleAttestationRef[];
  policy_mode: string;
  authority_public_key_hex: string;
  signature_hex: string;
  ledger_seq: number;
  chain_head: string;
}

export interface RobotComposition {
  robot_id: string;
  vendor_key_id: string;
  module_refs: ModuleAttestationRef[];
  composed: boolean;
  reasons: string[];
  ledger_seq: number;
  chain_head: string;
}

export interface ComposeRobotRequest {
  robot_id: string;
  vendor_key_id: string;
  module_ids: string[];
}

export interface SiteAdmissionRequest {
  robot_id: string;
  task_class: string;
  zone: string;
  robot_composed_seq: number;
}

export interface SiteAdmissionVerdict {
  robot_id: string;
  admitted: boolean;
  reasons: string[];
  robot_composed_seq: number;
  task_class: string;
  zone: string;
  policy_mode: string;
  authority_public_key_hex: string;
  signature_hex: string;
  ledger_seq: number;
  chain_head: string;
}

export type AttestationReason =
  | "ok"
  | "challenge_expired"
  | "signature_invalid"
  | "unknown_module"
  | "module_revoked";

export interface AttestationResult {
  module_id: string;
  verified: boolean;
  reason: AttestationReason;
  challenge_nonce_hex: string;
  verified_at: string;
}

export interface EnrolResponse {
  module_id: string;
  public_key_hex: string;
}

export interface RevokeModuleResponse {
  module_id: string;
  ledger_seq: number;
  revoked_at: string;
}

export interface EnrolledModule {
  module_id: string;
  public_key_hex: string;
  isRealSecureElement: boolean;
  isSynthetic: boolean;
  revoked?: boolean;
  attestation?: AttestationResult;
}

export interface FleetRobot {
  robot_id: string;
  vendor_key_id: string;
  module_ids: string[];
  composition?: RobotComposition;
  admission?: SiteAdmissionVerdict;
  isSynthetic: boolean;
}

export interface SiteGateConfig {
  task_class: string;
  zone: string;
}

/** Mirrors narrator/narrator_models.py — NarratorQuery */
export interface NarratorQuery {
  question: string;
  config_id?: string | null;
  robot_id?: string | null;
}

/** Mirrors narrator/narrator_models.py — NarratorAnswer */
export interface NarratorAnswer {
  answer: string;
  grounded_on: number[];
  llm_configured: boolean;
}
