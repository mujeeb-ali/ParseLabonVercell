"""Vercel entrypoint for ParseLab.

Vercel looks for a FastAPI instance named ``app`` in a root ``index.py``. This
file just exposes the existing app from ``backend/app/main.py``, which serves
both the JSON API under ``/api`` and the built React interface (``frontend/dist``),
so the whole site runs from this one function.

(Named ``index.py`` rather than ``app.py`` because the backend package itself is
called ``app``; a root ``app.py`` would shadow it on import.)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from app.main import app  # noqa: E402,F401  (re-exported for Vercel)
