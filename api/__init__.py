"""FastAPI gateway. Pydantic-validated boundaries; the front end never
touches a service directly. Pydantic raises 422 on shape errors."""

from bootstrap_site_package import ensure_quasar_site_package

ensure_quasar_site_package()

from api.api_main import app, create_app

__all__ = ["app", "create_app"]
