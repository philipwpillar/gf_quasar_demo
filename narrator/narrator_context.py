"""Read-only rendered view of ledger + policy for the LLM narrator.

Pure function: builds a deterministic snapshot from ``ledger.export()`` and
never mutates the ledger. The narrator sends this view to a third-party API;
in production the corpus is the asset and this would run on owned/local infra.
"""

from __future__ import annotations

from ledger import EntryKind, Ledger

RELEVANT_KINDS = frozenset(
    {
        EntryKind.MODULE_ENROLLED,
        EntryKind.ATTESTATION,
        EntryKind.ROBOT_COMPOSED,
        EntryKind.SITE_ADMISSION,
        EntryKind.CLEARANCE_DECISION,
        EntryKind.TELEMETRY,
        EntryKind.DECOMMISSION,
    }
)


def build_narrator_context(
    ledger: Ledger,
    *,
    question: str,
    config_id: str | None = None,
    robot_id: str | None = None,
) -> tuple[str, list[int]]:
    """Return (rendered_text, grounded_on_seqs) for the narrator prompt.

    Does not append to or mutate the ledger. ``grounded_on_seqs`` lists every
    ledger sequence included in the rendered view.
    """
    export = ledger.export()
    grounded_on: list[int] = []
    lines: list[str] = [
        "=== Quasar ledger snapshot (read-only) ===",
        "",
    ]

    if config_id:
        lines.append(f"Scope filter: config_id={config_id}")
    if robot_id:
        lines.append(f"Scope filter: robot_id={robot_id}")
    if config_id or robot_id:
        lines.append("")

    for raw in export:
        seq = raw["seq"]
        kind = raw["kind"]
        if kind not in {k.value for k in RELEVANT_KINDS}:
            continue

        entry_config = raw.get("config_id", "")
        payload = raw.get("payload", {})

        if config_id and entry_config != config_id:
            if kind not in (
                EntryKind.ROBOT_COMPOSED.value,
                EntryKind.SITE_ADMISSION.value,
            ):
                if payload.get("config_id") != config_id:
                    continue

        if robot_id:
            payload_robot = payload.get("robot_id")
            if payload_robot is not None and payload_robot != robot_id:
                if entry_config != robot_id:
                    continue

        grounded_on.append(seq)
        if kind == EntryKind.DECOMMISSION.value:
            lines.append(
                f"[seq={seq}] module {payload.get('module_id', '?')} revoked at "
                f"{payload.get('revoked_at', '?')}: {payload.get('reason', '?')}"
            )
        else:
            lines.append(f"[seq={seq}] kind={kind} config_id={entry_config}")
            for key, value in sorted(payload.items()):
                lines.append(f"  {key}: {value}")
        lines.append("")

    if _asks_about_tampering(question):
        intact, broken_seq = ledger.verify()
        lines.append("=== Ledger integrity (backend verify()) ===")
        lines.append(f"intact: {intact}")
        lines.append(f"first_broken_seq: {broken_seq}")
        lines.append("")

    lines.append(f"Question: {question}")
    return "\n".join(lines), grounded_on


def _asks_about_tampering(question: str) -> bool:
    lowered = question.lower()
    return any(
        token in lowered
        for token in ("tamper", "tampered", "integrity", "chain intact", "broken chain")
    )
