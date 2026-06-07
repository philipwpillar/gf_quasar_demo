"""Corpus seed, provenance guard, and telemetry ingest tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from api.api_main import create_app
from attestation import AttestationService, SoftwareEd25519Signer
from corpus import (
    CorpusService,
    DanglingTelemetryError,
    TelemetrySample,
    generate_samples,
)
from ledger import EntryKind, Ledger


def _ledger_with_attestation() -> tuple[Ledger, AttestationService, int]:
    ledger = Ledger()
    service = AttestationService(ledger, config_id="cfg-demo")
    signer = SoftwareEd25519Signer()
    service.enrol("mod-001", signer)
    service.attest("mod-001", signer)
    attestation_seq = len(ledger)
    return ledger, service, attestation_seq


def test_generated_sample_attestation_ref_resolves() -> None:
    ledger, _, attestation_seq = _ledger_with_attestation()
    samples = generate_samples(ledger, count=3, seed=99)
    assert samples
    for sample in samples:
        entry = ledger.get(sample.attestation_ref)
        assert entry.kind == EntryKind.ATTESTATION
        assert sample.attestation_ref == attestation_seq


def test_ingest_rejects_dangling_attestation_ref() -> None:
    ledger, _, _ = _ledger_with_attestation()
    corpus = CorpusService(ledger)
    sample = TelemetrySample(
        config_id="cfg-demo",
        module_id="mod-001",
        attestation_ref=999,
        ts=datetime.now(timezone.utc),
    )
    with pytest.raises(DanglingTelemetryError):
        corpus.ingest(sample)


def test_ingest_rejects_non_attestation_ref() -> None:
    ledger, _, _ = _ledger_with_attestation()
    corpus = CorpusService(ledger)
    sample = TelemetrySample(
        config_id="cfg-demo",
        module_id="mod-001",
        attestation_ref=1,
        ts=datetime.now(timezone.utc),
    )
    with pytest.raises(DanglingTelemetryError):
        corpus.ingest(sample)


def test_ingest_writes_telemetry_and_ledger_verifies() -> None:
    ledger, _, attestation_seq = _ledger_with_attestation()
    corpus = CorpusService(ledger)
    sample = generate_samples(ledger, count=1, seed=7)[0]

    entry = corpus.ingest(sample)

    assert entry.kind == EntryKind.TELEMETRY
    assert entry.payload["attestation_ref"] == attestation_seq
    assert ledger.verify() == (True, None)


def test_environment_tag_accepts_lunar_schema() -> None:
    sample = TelemetrySample(
        config_id="cfg-demo",
        module_id="mod-001",
        attestation_ref=2,
        ts=datetime.now(timezone.utc),
        environment_tag="lunar",
    )
    assert sample.environment_tag == "lunar"


def test_seeding_is_deterministic_for_given_seed() -> None:
    ledger, _, _ = _ledger_with_attestation()
    first = generate_samples(ledger, count=5, seed=12345)
    second = generate_samples(ledger, count=5, seed=12345)
    assert [s.model_dump() for s in first] == [s.model_dump() for s in second]


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.delenv("QUASAR_LLM_API_KEY", raising=False)
    return TestClient(create_app())


def test_api_telemetry_rejects_dangling_ref(client: TestClient) -> None:
    client.post("/modules/enrol", json={"module_id": "mod-001"})
    client.post("/attest", json={"module_id": "mod-001"})

    response = client.post(
        "/telemetry",
        json={
            "config_id": "cfg-demo",
            "module_id": "mod-001",
            "attestation_ref": 999,
            "ts": "2026-01-15T12:00:00+00:00",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"] == "dangling_telemetry"


def test_api_corpus_seed_dev_gated(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    client.post("/modules/enrol", json={"module_id": "mod-001"})
    client.post("/attest", json={"module_id": "mod-001"})

    monkeypatch.delenv("QUASAR_ENABLE_DEV_HOOKS", raising=False)
    disabled = client.post("/corpus/seed", json={"count": 3, "seed": 1})
    assert disabled.status_code == 404

    monkeypatch.setenv("QUASAR_ENABLE_DEV_HOOKS", "1")
    enabled = client.post("/corpus/seed", json={"count": 3, "seed": 1})
    assert enabled.status_code == 200
    body = enabled.json()
    assert body["generated"] == 3
    assert body["ingested"] == 3

    ledger = client.app.state.ledger
    assert ledger.verify() == (True, None)
    telemetry_entries = [
        ledger.get(seq)
        for seq in range(1, len(ledger) + 1)
        if ledger.get(seq).kind == EntryKind.TELEMETRY
    ]
    assert len(telemetry_entries) == 3
