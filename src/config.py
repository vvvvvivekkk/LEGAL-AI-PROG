"""Load runtime configuration from a repo-root `.env` file.

Every entry point that can reach an LLM (the FastAPI app, the generation
factory) calls `load_env()` once. Real environment variables always win over
the file, so a deployment can override anything without editing `.env`.
`.env` is gitignored; `.env.example` documents the keys.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = REPO_ROOT / ".env"

_loaded = False


def load_env() -> Path | None:
    """Load `.env` (if present) into os.environ without overriding set vars.

    Returns the path loaded, or None if there was nothing to load. Safe to
    call repeatedly — only the first call does any work.
    """
    global _loaded
    if _loaded:
        return ENV_FILE if ENV_FILE.exists() else None
    _loaded = True
    if not ENV_FILE.exists():
        return None
    from dotenv import load_dotenv

    load_dotenv(ENV_FILE, override=False)
    return ENV_FILE


def env(name: str, default: str | None = None) -> str | None:
    """Read one setting, loading `.env` first. Empty strings count as unset."""
    load_env()
    value = os.environ.get(name)
    return value if value else default
