"""Register the project ``site/`` component under a non-conflicting import name.

Python 3.13 exposes stdlib ``site`` as a frozen module, so a top-level ``site/``
package cannot be imported as ``site``. The on-disk component stays ``site/`` per
the codebase constitution; runtime imports use ``quasar_site`` instead.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

QUASAR_SITE_PACKAGE = "quasar_site"


def ensure_quasar_site_package() -> None:
    """Load ``site/`` as ``quasar_site`` if not already registered."""
    if QUASAR_SITE_PACKAGE in sys.modules:
        return

    site_dir = Path(__file__).resolve().parent / "site"
    spec = importlib.util.spec_from_file_location(
        QUASAR_SITE_PACKAGE,
        site_dir / "__init__.py",
        submodule_search_locations=[str(site_dir)],
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load site component from {site_dir}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[QUASAR_SITE_PACKAGE] = module
    spec.loader.exec_module(module)
