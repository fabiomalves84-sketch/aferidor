"""Aferidor: a test bench for clinical answers from language models."""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

__version__ = "0.1.0"


@lru_cache(maxsize=1)
def code_digest() -> str:
    """SHA-256 of every Python source file in this package, in name order.

    Written on every answer so a measurement can be tied to the exact code
    that produced it. A git commit would not do: it says nothing about
    changes not yet committed, and reading git during a run is exactly what
    the project keeps to one session. This can be recomputed on any later
    checkout to find which commit matches.
    """
    digest = hashlib.sha256()
    package = Path(__file__).resolve().parent
    for source in sorted(package.glob("*.py")):
        digest.update(source.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(source.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def build_id() -> str:
    """The version, and the first 12 characters of `code_digest`."""
    return f"{__version__}+{code_digest()[:12]}"
