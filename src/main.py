"""Deprecated legacy entrypoint. Use backend/main.py instead."""

raise RuntimeError(
    "Legacy backend entrypoint is disabled. Use backend/main.py (uvicorn backend.main:app) instead."
)
