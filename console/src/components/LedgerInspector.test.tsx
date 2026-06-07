import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { LedgerEntry } from "../types/quasarLedgerTypes";

import LedgerInspector from "./LedgerInspector";

const entries: LedgerEntry[] = [
  {
    seq: 1,
    kind: "module_enrolled",
    occurred_at: "2026-01-01T00:00:00+00:00",
    config_id: "cfg-demo",
    payload: { module_id: "mod-secure-001" },
    prev_hash: "0".repeat(64),
    entry_hash: "a".repeat(64),
  },
  {
    seq: 2,
    kind: "attestation",
    occurred_at: "2026-01-01T00:00:01+00:00",
    config_id: "cfg-demo",
    payload: { module_id: "mod-synth-002", verified: false },
    prev_hash: "a".repeat(64),
    entry_hash: "b".repeat(64),
  },
  {
    seq: 3,
    kind: "robot_composed",
    occurred_at: "2026-01-01T00:00:02+00:00",
    config_id: "robot-propagation-demo",
    payload: { composed: false },
    prev_hash: "b".repeat(64),
    entry_hash: "c".repeat(64),
  },
];

describe("LedgerInspector", () => {
  it("shows entries in sequence order and reflects verify result", () => {
    render(
      <LedgerInspector
        entries={entries}
        verifyResult={{ intact: true, first_broken_seq: null }}
        onRefresh={vi.fn().mockResolvedValue(undefined)}
        busy={false}
      />,
    );

    const list = screen.getByTestId("ledger-entry-list");
    const items = list.querySelectorAll("[data-testid^='ledger-entry-']");
    expect(items).toHaveLength(3);
    expect(items[0]).toHaveAttribute("data-testid", "ledger-entry-1");
    expect(items[1]).toHaveAttribute("data-testid", "ledger-entry-2");
    expect(items[2]).toHaveAttribute("data-testid", "ledger-entry-3");

    expect(screen.getByTestId("ledger-verify-result")).toHaveTextContent(
      /Chain intact/i,
    );
  });
});
