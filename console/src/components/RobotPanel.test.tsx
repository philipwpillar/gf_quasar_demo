import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { FleetRobot } from "../types/quasarLedgerTypes";
import { POLICY_MODE_STUB } from "../types/quasarLedgerTypes";

import RobotPanel from "./RobotPanel";

const baseRobot: FleetRobot = {
  robot_id: "robot-forged-vendor",
  vendor_id: "vendor_alpha",
  module_ids: ["mod-001"],
  isSynthetic: false,
  composition: {
    robot_id: "robot-forged-vendor",
    vendor_id: "vendor_alpha",
    vendor_signature_hex: "aa".repeat(64),
    vendor_public_key_hex: "bb".repeat(32),
    composed: true,
    reasons: ["robot robot-forged-vendor composed from 1 attested module(s)"],
    ledger_seq: 4,
    chain_head: "c".repeat(64),
    module_refs: [{ module_id: "mod-001", attested: true, ledger_seq: 3 }],
  },
  admission: {
    robot_id: "robot-forged-vendor",
    admitted: false,
    reasons: [
      "robot robot-forged-vendor not trusted: vendor signature invalid for vendor_alpha",
    ],
    robot_composed_seq: 4,
    task_class: "industrial_inspection",
    zone: "zone_b",
    policy_mode: POLICY_MODE_STUB,
    authority_public_key_hex: "dd".repeat(32),
    signature_hex: "ee".repeat(64),
    ledger_seq: 5,
    chain_head: "f".repeat(64),
  },
};

describe("RobotPanel", () => {
  it("renders vendor trust failure distinctly from module attestation failure", () => {
    render(<RobotPanel robot={baseRobot} modules={[]} />);

    expect(screen.getByTestId("vendor-trust-failure")).toBeInTheDocument();
    expect(screen.getByText(/vendor trust failure/i)).toBeInTheDocument();
    expect(screen.getByText(/Vendor: vendor_alpha/i)).toBeInTheDocument();
    expect(screen.queryByText(/mate-time attestation/i)).not.toBeInTheDocument();
  });
});
