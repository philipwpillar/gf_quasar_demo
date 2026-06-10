"""Site orchestration: Tier 1 attestation → Tier 2 composition → Tier 3 admission.

Contract: ``compose_robot`` always runs a fresh mate-time attestation for every
``module_id`` via ``AttestationService.attest`` (never accepts stale refs).
Each module's ``ledger_seq`` is the sequence of that attestation entry.

Vendor key custody in this demo is server-side software signers; in production
each vendor custodies its own key.

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
from .site_errors import (
    DuplicateVendorError,
    RobotCompositionNotFoundError,
    RobotIdMismatchError,
    UnknownVendorError,
)
from .site_models import (
    ComposeRobotRequest,
    RobotComposition,
    SiteAdmissionRequest,
    SiteAdmissionVerdict,
    VendorIdentity,
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
        self._vendors: dict[str, VendorIdentity] = {}

    def enrol_vendor(self, vendor_id: str, signer: Signer) -> VendorIdentity:
        """Register a vendor authority and append ``vendor_enrolled`` to the ledger."""
        if vendor_id in self._vendors:
            raise DuplicateVendorError(vendor_id)

        identity = VendorIdentity(
            vendor_id=vendor_id,
            public_key_hex=signer.public_key_hex(),
        )
        self._ledger.append(
            EntryKind.VENDOR_ENROLLED,
            vendor_id,
            {
                "vendor_id": identity.vendor_id,
                "public_key_hex": identity.public_key_hex,
            },
        )
        self._vendors[vendor_id] = identity
        return identity

    def get_enrolled_vendor(self, vendor_id: str) -> VendorIdentity | None:
        """Return the enrolled vendor identity, or None if unknown."""
        return self._vendors.get(vendor_id)

    def compose_robot(
        self,
        request: ComposeRobotRequest,
        module_signers: dict[str, Signer],
        vendor_signers: dict[str, Signer],
    ) -> RobotComposition:
        if request.vendor_id not in self._vendors:
            raise UnknownVendorError(request.vendor_id)

        vendor_signer = vendor_signers.get(request.vendor_id)
        if vendor_signer is None:
            raise UnknownVendorError(request.vendor_id)

        module_refs: list[ModuleAttestationRef] = []

        for module_id in request.module_ids:
            signer = module_signers.get(module_id)
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
            vendor_id=request.vendor_id,
            vendor_signer=vendor_signer,
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

        vendor = self._vendors.get(robot_composition.vendor_id)
        enrolled_public_key_hex = vendor.public_key_hex if vendor else None

        return admit(
            self._ledger,
            self._site_authority_signer,
            request,
            robot_composition,
            enrolled_vendor_public_key_hex=enrolled_public_key_hex,
        )
