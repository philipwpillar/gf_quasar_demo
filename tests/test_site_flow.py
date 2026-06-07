"""End-to-end Tier 2 composition and Tier 3 site admission through the gateway."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.api_main import create_app
from attestation import SoftwareEd25519Signer
from ledger import EntryKind
from policy import POLICY_MODE_STUB
from quasar_site import RobotComposition, SiteAdmissionVerdict, verify_site_verdict


SITE_PATH_MODULES = (
    "quasar_site",
    "quasar_site.site_models",
    "quasar_site.site_composition",
    "quasar_site.site_admission",
    "quasar_site.site_service",
    "quasar_site.site_errors",
    "api.api_routes_site",
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def _enrol(client: TestClient, module_id: str) -> None:
    response = client.post("/modules/enrol", json={"module_id": module_id})
    assert response.status_code == 200


def _compose_payload(
    *,
    robot_id: str = "robot-001",
    vendor_key_id: str = "vendor-acme",
    module_ids: list[str] | None = None,
) -> dict:
    return {
        "robot_id": robot_id,
        "vendor_key_id": vendor_key_id,
        "module_ids": module_ids or ["mod-001", "mod-002"],
    }


def _admit_payload(
    *,
    robot_id: str = "robot-001",
    robot_composed_seq: int,
    task_class: str = "industrial_inspection",
    zone: str = "zone_b",
) -> dict:
    return {
        "robot_id": robot_id,
        "task_class": task_class,
        "zone": zone,
        "robot_composed_seq": robot_composed_seq,
    }


def test_compose_robot_all_modules_attested(client: TestClient) -> None:
    _enrol(client, "mod-001")
    _enrol(client, "mod-002")

    response = client.post("/robots/compose", json=_compose_payload())
    assert response.status_code == 200

    composition = RobotComposition.model_validate(response.json())
    assert composition.composed is True
    assert composition.reasons
    assert len(composition.module_refs) == 2
    assert all(ref.attested for ref in composition.module_refs)

    ledger = client.app.state.ledger
    entry = ledger.get(composition.ledger_seq)
    assert entry.kind == EntryKind.ROBOT_COMPOSED
    assert entry.payload["composed"] is True

    for ref in composition.module_refs:
        attestation_entry = ledger.get(ref.ledger_seq)
        assert attestation_entry.kind == EntryKind.ATTESTATION
        assert attestation_entry.payload["module_id"] == ref.module_id
        assert attestation_entry.payload["verified"] == ref.attested

    assert ledger.verify() == (True, None)


def test_compose_robot_one_failed_module(client: TestClient) -> None:
    _enrol(client, "mod-001")
    _enrol(client, "mod-002")

    client.app.state.module_signers["mod-002"] = SoftwareEd25519Signer()

    response = client.post("/robots/compose", json=_compose_payload())
    assert response.status_code == 200

    composition = RobotComposition.model_validate(response.json())
    assert composition.composed is False
    assert any("mod-002" in reason for reason in composition.reasons)

    ledger = client.app.state.ledger
    entry = ledger.get(composition.ledger_seq)
    assert entry.kind == EntryKind.ROBOT_COMPOSED
    assert entry.payload["composed"] is False

    failed_ref = next(ref for ref in composition.module_refs if ref.module_id == "mod-002")
    assert failed_ref.attested is False
    attestation_entry = ledger.get(failed_ref.ledger_seq)
    assert attestation_entry.payload["verified"] is False

    assert ledger.verify() == (True, None)


def test_admit_trusted_robot(client: TestClient) -> None:
    _enrol(client, "mod-001")
    _enrol(client, "mod-002")

    compose_response = client.post("/robots/compose", json=_compose_payload())
    composition = RobotComposition.model_validate(compose_response.json())

    admit_response = client.post(
        "/site/admit",
        json=_admit_payload(robot_composed_seq=composition.ledger_seq),
    )
    assert admit_response.status_code == 200

    verdict = SiteAdmissionVerdict.model_validate(admit_response.json())
    assert verdict.admitted is True
    assert verdict.policy_mode == POLICY_MODE_STUB
    assert verdict.robot_composed_seq == composition.ledger_seq
    assert verify_site_verdict(verdict) is True

    ledger = client.app.state.ledger
    entry = ledger.get(verdict.ledger_seq)
    assert entry.kind == EntryKind.SITE_ADMISSION
    assert entry.payload["admitted"] is True
    assert entry.payload["robot_composed_seq"] == composition.ledger_seq

    assert ledger.verify() == (True, None)


def test_admit_untrusted_robot_traces_failing_module(client: TestClient) -> None:
    _enrol(client, "mod-001")
    _enrol(client, "mod-002")

    client.app.state.module_signers["mod-002"] = SoftwareEd25519Signer()

    compose_response = client.post("/robots/compose", json=_compose_payload())
    composition = RobotComposition.model_validate(compose_response.json())
    assert composition.composed is False

    admit_response = client.post(
        "/site/admit",
        json=_admit_payload(robot_composed_seq=composition.ledger_seq),
    )
    verdict = SiteAdmissionVerdict.model_validate(admit_response.json())
    assert verdict.admitted is False
    assert any("mod-002" in reason for reason in verdict.reasons)
    assert verify_site_verdict(verdict) is True

    ledger = client.app.state.ledger
    entry = ledger.get(verdict.ledger_seq)
    assert entry.kind == EntryKind.SITE_ADMISSION
    assert entry.payload["admitted"] is False

    assert ledger.verify() == (True, None)


def test_admit_refuses_unsupported_task_or_zone(client: TestClient) -> None:
    _enrol(client, "mod-001")

    compose_response = client.post(
        "/robots/compose",
        json=_compose_payload(module_ids=["mod-001"]),
    )
    composition = RobotComposition.model_validate(compose_response.json())

    bad_task = client.post(
        "/site/admit",
        json=_admit_payload(
            robot_composed_seq=composition.ledger_seq,
            task_class="warehouse_picking",
        ),
    )
    bad_task_verdict = SiteAdmissionVerdict.model_validate(bad_task.json())
    assert bad_task_verdict.admitted is False
    assert any("not cleared:" in reason for reason in bad_task_verdict.reasons)

    bad_zone = client.post(
        "/site/admit",
        json=_admit_payload(
            robot_composed_seq=composition.ledger_seq,
            zone="zone_z",
        ),
    )
    bad_zone_verdict = SiteAdmissionVerdict.model_validate(bad_zone.json())
    assert bad_zone_verdict.admitted is False
    assert any("zone_z" in reason for reason in bad_zone_verdict.reasons)


def test_propagation_chain_attestation_fail_to_admission_denied(
    client: TestClient,
) -> None:
    """Demo moment: bad module → untrusted robot → denied admission, all recorded."""
    _enrol(client, "mod-001")
    _enrol(client, "mod-002")

    client.app.state.module_signers["mod-002"] = SoftwareEd25519Signer()

    compose_response = client.post("/robots/compose", json=_compose_payload())
    composition = RobotComposition.model_validate(compose_response.json())

    admit_response = client.post(
        "/site/admit",
        json=_admit_payload(robot_composed_seq=composition.ledger_seq),
    )
    verdict = SiteAdmissionVerdict.model_validate(admit_response.json())

    ledger = client.app.state.ledger
    exported = ledger.export()
    kinds = [EntryKind(raw["kind"]) for raw in exported]

    attestation_indices = [
        i for i, kind in enumerate(kinds) if kind == EntryKind.ATTESTATION
    ]
    robot_composed_index = kinds.index(EntryKind.ROBOT_COMPOSED)
    site_admission_index = kinds.index(EntryKind.SITE_ADMISSION)

    assert max(attestation_indices) < robot_composed_index < site_admission_index

    failed_attestation = next(
        raw
        for raw in exported
        if raw["kind"] == EntryKind.ATTESTATION.value
        and raw["payload"]["module_id"] == "mod-002"
    )
    assert failed_attestation["payload"]["verified"] is False

    robot_entry = ledger.get(composition.ledger_seq)
    assert robot_entry.payload["composed"] is False

    admission_entry = ledger.get(verdict.ledger_seq)
    assert admission_entry.payload["admitted"] is False

    assert composition.composed is False
    assert verdict.admitted is False
    assert verify_site_verdict(verdict) is True
    assert ledger.verify() == (True, None)


def test_tampered_site_verdict_fails_offline_verify(client: TestClient) -> None:
    _enrol(client, "mod-001")

    compose_response = client.post(
        "/robots/compose",
        json=_compose_payload(module_ids=["mod-001"]),
    )
    composition = RobotComposition.model_validate(compose_response.json())

    admit_response = client.post(
        "/site/admit",
        json=_admit_payload(robot_composed_seq=composition.ledger_seq),
    )
    verdict = SiteAdmissionVerdict.model_validate(admit_response.json())
    assert verify_site_verdict(verdict) is True

    tampered = verdict.model_copy(update={"admitted": not verdict.admitted})
    assert verify_site_verdict(tampered) is False

    tampered_reason = verdict.model_copy(update={"reasons": ["forged reason"]})
    assert verify_site_verdict(tampered_reason) is False


def test_site_path_has_no_narrator_imports() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    forbidden = ("narrator", "llm", "assistant")

    for module_name in SITE_PATH_MODULES:
        module = importlib.import_module(module_name)
        source_path = Path(module.__file__).resolve()
        assert source_path.is_relative_to(repo_root)

        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top_level = alias.name.split(".")[0]
                    assert top_level not in forbidden, (
                        f"{source_path} imports forbidden module {alias.name}"
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                top_level = node.module.split(".")[0]
                assert top_level not in forbidden, (
                    f"{source_path} imports forbidden module {node.module}"
                )
