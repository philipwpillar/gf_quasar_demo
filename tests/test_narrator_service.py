"""Narrator service tests — read-only boundary, graceful degrade, import guards."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.api_main import create_app
from attestation import AttestationService, SoftwareEd25519Signer
from ledger import Ledger
from narrator import NOT_CONFIGURED_MESSAGE, NarratorQuery, NarratorService
from narrator.narrator_context import build_narrator_context


DECISION_PATH_MODULES = (
    "policy.policy_models",
    "policy.policy_rules",
    "policy.policy_service",
    "policy.policy_errors",
    "attestation.attestation_core",
    "attestation.attestation_service",
    "attestation.attestation_signer",
    "quasar_site.site_models",
    "quasar_site.site_composition",
    "quasar_site.site_admission",
    "quasar_site.site_service",
    "api.api_routes_clearance",
    "api.api_routes_site",
    "api.api_routes_attestation",
)

NARRATOR_MODULES = (
    "narrator.narrator_service",
    "narrator.narrator_llm",
)

FORBIDDEN_IN_NARRATOR = (
    "policy.policy_service",
    "quasar_site.site_admission",
    "quasar_site.site_composition",
    "quasar_site.site_service",
    "attestation.attestation_signer",
)

FORBIDDEN_IN_DECISION_PATH = ("narrator", "llm", "assistant")


def _ledger_with_history() -> Ledger:
    ledger = Ledger()
    service = AttestationService(ledger, config_id="cfg-demo")
    signer = SoftwareEd25519Signer()
    service.enrol("mod-001", signer)
    service.attest("mod-001", signer)
    return ledger


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.delenv("QUASAR_LLM_API_KEY", raising=False)
    return TestClient(create_app())


def test_assistant_query_without_llm_key_degrades_gracefully(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("QUASAR_LLM_API_KEY", raising=False)
    client.post("/modules/enrol", json={"module_id": "mod-001"})

    response = client.post(
        "/assistant/query",
        json={"question": "Why was this configuration not cleared?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["llm_configured"] is False
    assert "not configured" in body["answer"].lower()
    assert NOT_CONFIGURED_MESSAGE.split(".")[0].lower() in body["answer"].lower()


def test_narrator_context_is_read_only_and_pure() -> None:
    ledger = _ledger_with_history()
    length_before = len(ledger)
    head_before = ledger.head_hash

    build_narrator_context(ledger, question="Summarise attestation history")

    assert len(ledger) == length_before
    assert ledger.head_hash == head_before


def test_grounded_on_references_real_ledger_seqs() -> None:
    ledger = _ledger_with_history()
    _, grounded_on = build_narrator_context(
        ledger, question="Which modules failed attestation?"
    )
    assert grounded_on
    for seq in grounded_on:
        assert 1 <= seq <= len(ledger)


def test_narrator_does_not_import_decision_path_modules() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    for module_name in NARRATOR_MODULES:
        module = importlib.import_module(module_name)
        source_path = Path(module.__file__).resolve()
        assert source_path.is_relative_to(repo_root)
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))

        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)

        for forbidden in FORBIDDEN_IN_NARRATOR:
            assert forbidden not in imported, (
                f"{source_path} must not import decision-path module {forbidden}"
            )


def test_decision_path_has_no_narrator_imports() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    for module_name in DECISION_PATH_MODULES:
        module = importlib.import_module(module_name)
        source_path = Path(module.__file__).resolve()
        assert source_path.is_relative_to(repo_root)
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top_level = alias.name.split(".")[0]
                    assert top_level not in FORBIDDEN_IN_DECISION_PATH, (
                        f"{source_path} imports forbidden module {alias.name}"
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                top_level = node.module.split(".")[0]
                assert top_level not in FORBIDDEN_IN_DECISION_PATH, (
                    f"{source_path} imports forbidden module {node.module}"
                )


def test_narrator_orchestration_with_mock_llm() -> None:
    ledger = _ledger_with_history()

    def fake_llm(context: str, question: str) -> tuple[str, bool]:
        assert "Question:" in context
        return "Mocked plain-language answer from the ledger view.", True

    service = NarratorService(ledger, llm_callable=fake_llm)
    answer = service.query(NarratorQuery(question="Show me what this configuration did."))

    assert answer.llm_configured is True
    assert "Mocked plain-language answer" in answer.answer
    assert answer.grounded_on
    for seq in answer.grounded_on:
        ledger.get(seq)
