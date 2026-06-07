"""Site orchestration: Tier 1 attestation → Tier 2 composition → Tier 3 admission.

Contract: ``compose_robot`` always runs a fresh mate-time attestation for every
``module_id`` via ``AttestationService.attest`` (never accepts stale refs).
Each module's ``ledger_seq`` is the sequence of that attestation entry.

Site policy breadth reuses the curated single-task rules from ``policy``;
attestation, composition, and ledger writes remain REAL.
"""

from __future__ import annotations

from attestation import AttestationService
from attestation.attestation_signer import Signer
from ledger import EntryKind, Ledger
from policy.policy_errors import MissingModuleSignerError
from policy.policy_models import ModuleAttestationRef

from .site_admission import admit
from .site_composition import compose_robot, composition_from_ledger_entry
from .site_errors import RobotCompositionNotFoundError, RobotIdMismatchError
from .site_models import (
    ComposeRobotRequest,
    RobotComposition,
    SiteAdmissionRequest,
    SiteAdmissionVerdict,
)


class SiteService:
    """Orchestrate robot composition and site-gate admission over the ledger spine."""

    def __init__(
        self,
        ledger: Ledger,
        attestation: AttestationService,
        site_authority_signer: Signer,
    ) -> None:
        self._ledger = ledger
        self._attestation = attestation
        self._site_authority_signer = site_authority_signer

    def compose_robot(
        self,
        request: ComposeRobotRequest,
        signers: dict[str, Signer],
    ) -> RobotComposition:
        module_refs: list[ModuleAttestationRef] = []

        for module_id in request.module_ids:
            signer = signers.get(module_id)
            if signer is None:
                raise MissingModuleSignerError(module_id)

            result = self._attestation.attest(module_id, signer)
            ledger_seq = len(self._ledger)
            module_refs.append(
                ModuleAttestationRef(
                    module_id=module_id,
                    attested=result.verified,
                    ledger_seq=ledger_seq,
                )
            )

        return compose_robot(
            self._ledger,
            robot_id=request.robot_id,
            vendor_key_id=request.vendor_key_id,
            module_refs=module_refs,
        )

    def load_composition(self, robot_composed_seq: int) -> RobotComposition:
        entry = self._ledger.get(robot_composed_seq)
        if entry.kind != EntryKind.ROBOT_COMPOSED:
            raise RobotCompositionNotFoundError(robot_composed_seq)
        return composition_from_ledger_entry(self._ledger, robot_composed_seq)

    def admit_robot(self, request: SiteAdmissionRequest) -> SiteAdmissionVerdict:
        robot_composition = self.load_composition(request.robot_composed_seq)
        if robot_composition.robot_id != request.robot_id:
            raise RobotIdMismatchError(
                request_robot_id=request.robot_id,
                composition_robot_id=robot_composition.robot_id,
            )
        return admit(
            self._ledger,
            self._site_authority_signer,
            request,
            robot_composition,
        )
