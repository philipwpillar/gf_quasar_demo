"""End-to-end clearance flow through the FastAPI gateway."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.api_main import create_app
from attestation import SoftwareEd25519Signer
from ledger import EntryKind
from policy import POLICY_MODE_STUB, ClearanceVerdict, verify_verdict


CLEARANCE_PATH_MODULES = (
    "policy.policy_models",
    "policy.policy_rules",
    "policy.policy_service",
    "policy.policy_errors",
    "api.api_routes_clearance",
    "api.api_errors",
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def _enrol(client: TestClient, module_id: str) -> None:
    response = client.post("/modules/enrol", json={"module_id": module_id})
    assert response.status_code == 200


def _clearance_payload(
    *,
    config_id: str = "robot-001",
    module_ids: list[str] | None = None,
) -> dict:
    return {
        "config_id": config_id,
        "module_ids": module_ids or ["mod-001", "mod-002"],
        "task_class": "industrial_inspection",
        "zone": "zone_b",
    }


def test_clearance_flow_all_good(client: TestClient) -> None:
    _enrol(client, "mod-001")
    _enrol(client, "mod-002")

    response = client.post("/clearance", json=_clearance_payload())
    assert response.status_code == 200

    verdict = ClearanceVerdict.model_validate(response.json())
    assert verdict.cleared is True
    assert verdict.reasons
    assert verdict.policy_mode == POLICY_MODE_STUB
    assert verify_verdict(verdict) is True

    ledger = client.app.state.ledger
    entry = ledger.get(verdict.ledger_seq)
    assert entry.kind == EntryKind.CLEARANCE_DECISION
    assert entry.payload["cleared"] is True
    assert entry.payload["policy_mode"] == POLICY_MODE_STUB

    verify_response = client.get("/ledger/verify")
    assert verify_response.status_code == 200
    assert verify_response.json() == {"intact": True, "first_broken_seq": None}
    assert ledger.verify() == (True, None)


def test_clearance_blocked_when_module_revoked(client: TestClient) -> None:
    _enrol(client, "mod-001")
    _enrol(client, "mod-002")

    revoke_response = client.post(
        "/modules/revoke",
        json={"module_id": "mod-002", "reason": "governance deprovision"},
    )
    assert revoke_response.status_code == 200
    assert revoke_response.json()["module_id"] == "mod-002"

    response = client.post("/clearance", json=_clearance_payload())
    assert response.status_code == 200

    verdict = ClearanceVerdict.model_validate(response.json())
    assert verdict.cleared is False
    assert any("module_revoked" in reason for reason in verdict.reasons)
    assert verify_verdict(verdict) is True

    ledger = client.app.state.ledger
    assert ledger.verify() == (True, None)


def test_revoke_api_unknown_module_returns_404(client: TestClient) -> None:
    response = client.post(
        "/modules/revoke",
        json={"module_id": "mod-missing", "reason": "test"},
    )
    assert response.status_code == 404
    assert response.json()["error"] == "unknown_module"


def test_revoke_api_double_revoke_returns_409(client: TestClient) -> None:
    _enrol(client, "mod-001")
    first = client.post(
        "/modules/revoke",
        json={"module_id": "mod-001", "reason": "first"},
    )
    assert first.status_code == 200

    second = client.post(
        "/modules/revoke",
        json={"module_id": "mod-001", "reason": "second"},
    )
    assert second.status_code == 409
    assert second.json()["error"] == "module_already_revoked"


def test_clearance_blocked_when_one_module_fails_attestation(
    client: TestClient,
) -> None:
    _enrol(client, "mod-001")
    _enrol(client, "mod-002")

    client.app.state.module_signers["mod-002"] = SoftwareEd25519Signer()

    response = client.post("/clearance", json=_clearance_payload())
    assert response.status_code == 200

    verdict = ClearanceVerdict.model_validate(response.json())
    assert verdict.cleared is False
    assert any("mod-002" in reason for reason in verdict.reasons)
    assert verify_verdict(verdict) is True

    ledger = client.app.state.ledger
    entry = ledger.get(verdict.ledger_seq)
    assert entry.kind == EntryKind.CLEARANCE_DECISION
    assert entry.payload["cleared"] is False

    verify_response = client.get("/ledger/verify")
    assert verify_response.json()["intact"] is True
    assert ledger.verify() == (True, None)


def test_tampered_verdict_fails_offline_verify(client: TestClient) -> None:
    _enrol(client, "mod-001")

    response = client.post(
        "/clearance",
        json=_clearance_payload(module_ids=["mod-001"]),
    )
    verdict = ClearanceVerdict.model_validate(response.json())
    assert verify_verdict(verdict) is True

    tampered = verdict.model_copy(update={"cleared": not verdict.cleared})
    assert verify_verdict(tampered) is False

    tampered_reason = verdict.model_copy(update={"reasons": ["forged reason"]})
    assert verify_verdict(tampered_reason) is False


def test_clearance_path_has_no_narrator_imports() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    forbidden = ("narrator", "llm", "assistant")

    for module_name in CLEARANCE_PATH_MODULES:
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
