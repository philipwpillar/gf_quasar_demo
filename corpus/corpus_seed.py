"""Synthetic telemetry generator — STUBBED depth, provenance-linked only.

Generates plausible behaviour samples against attestation entries that already
exist in the ledger. Deterministic for a given ``seed`` so the demo is
reproducible. DATA is synthetic and labelled stubbed; SCHEMA is full-fidelity.
"""

from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta, timezone

from ledger import EntryKind, Ledger

from corpus.corpus_models import TelemetrySample

TERRESTRIAL_TAGS = ("terrestrial_indoor", "terrestrial_outdoor")
FAULT_CLASSES = ("overcurrent", "encoder_drift", "thermal_derate", "comm_timeout")
STUB_LABEL = "synthetic_stubbed"


def _attestation_refs(ledger: Ledger) -> list[tuple[int, str, str]]:
    """Return (seq, config_id, module_id) for each attestation ledger entry."""
    refs: list[tuple[int, str, str]] = []
    for seq in range(1, len(ledger) + 1):
        entry = ledger.get(seq)
        if entry.kind != EntryKind.ATTESTATION:
            continue
        module_id = entry.payload.get("module_id", "")
        refs.append((seq, entry.config_id, module_id))
    return refs


def generate_samples(
    ledger: Ledger,
    *,
    count: int,
    seed: int = 42,
    fault_rate: float = 0.08,
) -> list[TelemetrySample]:
    """Emit up to ``count`` synthetic samples linked to real attestation entries.

    Returns fewer than ``count`` when the ledger has fewer attestation entries.
    Each sample is deterministic for the same ``seed`` and ledger state.
    """
    if count < 1:
        return []

    refs = _attestation_refs(ledger)
    if not refs:
        return []

    rng = random.Random(seed)
    base_time = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    samples: list[TelemetrySample] = []

    for index in range(count):
        attestation_ref, config_id, module_id = refs[index % len(refs)]
        sample_rng = random.Random(rng.randint(0, 2**31 - 1))

        fault_flag = sample_rng.random() < fault_rate
        fault_class = sample_rng.choice(FAULT_CLASSES) if fault_flag else None
        actuation_load = round(sample_rng.uniform(0.15, 0.95), 4)
        utilisation = round(sample_rng.uniform(0.05, 0.85), 4)
        cycles = sample_rng.randint(0, 5000)
        location_hash = hashlib.sha256(
            f"{config_id}:{module_id}:{index}:{seed}".encode()
        ).hexdigest()[:16]
        environment_tag = sample_rng.choice(TERRESTRIAL_TAGS)
        ts = base_time + timedelta(minutes=index * 5, seconds=sample_rng.randint(0, 59))

        samples.append(
            TelemetrySample(
                config_id=config_id,
                module_id=module_id,
                attestation_ref=attestation_ref,
                ts=ts,
                actuation_load=actuation_load,
                fault_flag=fault_flag,
                fault_class=fault_class,
                cycles_since_mate=cycles,
                utilisation=utilisation,
                location_hash=location_hash,
                environment_tag=environment_tag,
                extra={"source": STUB_LABEL, "generator_seed": seed},
            )
        )

    return samples
