"""Pytest configuration — ensure project root and local packages resolve correctly."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from bootstrap_site_package import ensure_quasar_site_package

ensure_quasar_site_package()
