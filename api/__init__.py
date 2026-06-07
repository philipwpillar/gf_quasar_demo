"""FastAPI gateway. Pydantic-validated boundaries; the front end never
touches a service directly. Pydantic raises 422 on shape errors."""

from api.api_main import app, create_app

__all__ = ["app", "create_app"]
