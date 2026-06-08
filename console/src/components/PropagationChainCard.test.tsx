import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { FleetRobot } from "../types/quasarLedgerTypes";
import { POLICY_MODE_STUB } from "../types/quasarLedgerTypes";

import PropagationChainCard from "./PropagationChainCard";

const propagationRobot: FleetRobot = {
  robot_id: "robot-propagation-demo",
  vendor_key_id: "vendor-synth-demo",
  module_ids: ["mod-secure-001", "mod-synth-002"],
  isSynthetic: true,
  composition: {
    robot_id: "robot-propagation-demo",
    vendor_key_id: "vendor-synth-demo",
    composed: false,
    reasons: [
      "robot robot-propagation-demo not trusted: module mod-synth-002 failed attestation (ledger seq 4)",
    ],
    ledger_seq: 5,
    chain_head: "c".repeat(64),
    module_refs: [
      { module_id: "mod-secure-001", attested: true, ledger_seq: 3 },
      { module_id: "mod-synth-002", attested: false, ledger_seq: 4 },
    ],
  },
  admission: {
    robot_id: "robot-propagation-demo",
    admitted: false,
    reasons: [
      "robot robot-propagation-demo not trusted: module mod-synth-002 failed attestation (ledger seq 4)",
    ],
    robot_composed_seq: 5,
    task_class: "industrial_inspection",
    zone: "zone_b",
    policy_mode: POLICY_MODE_STUB,
    authority_public_key_hex: "dd".repeat(32),
    signature_hex: "ee".repeat(64),
    ledger_seq: 6,
    chain_head: "f".repeat(64),
  },
};

describe("PropagationChainCard", () => {
  it("renders denied admission and names the failing module", () => {
    render(
      <PropagationChainCard
        robot={propagationRobot}
        admission={propagationRobot.admission}
      />,
    );

    expect(screen.getByTestId("propagation-chain")).toBeInTheDocument();
    expect(screen.getByText(/DENIED site admission/i)).toBeInTheDocument();
    expect(screen.getAllByText("mod-synth-002").length).toBeGreaterThan(0);
    expect(screen.getByText(/mate-time attestation FAILED/i)).toBeInTheDocument();
    expect(screen.getAllByText(/NOT COMPOSED/i).length).toBeGreaterThan(0);
  });
});
