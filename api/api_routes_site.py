"""Site routes — robot composition (Tier 2) and site admission (Tier 3)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from quasar_site import (
    ComposeRobotRequest,
    RobotComposition,
    SiteAdmissionRequest,
    SiteAdmissionVerdict,
    SiteService,
)

router = APIRouter(tags=["site"])


@router.post("/robots/compose", response_model=RobotComposition)
def compose_robot(
    request_body: ComposeRobotRequest, request: Request
) -> RobotComposition:
    """Compose a robot from enrolled modules (re-attests each module).

    Writes ``robot_composed`` to the ledger. No LLM / narrator code participates.
    """
    site: SiteService = request.app.state.site
    module_signers: dict = request.app.state.module_signers

    return site.compose_robot(request_body, module_signers)


@router.post("/site/admit", response_model=SiteAdmissionVerdict)
def admit_robot(
    request_body: SiteAdmissionRequest, request: Request
) -> SiteAdmissionVerdict:
    """Admit or refuse a composed robot for a task in a zone.

    Writes a signed ``site_admission`` provenance event — never task dispatch.
    """
    site: SiteService = request.app.state.site
    return site.admit_robot(request_body)
