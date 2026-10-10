"""Aferidor: a test bench for clinical answers from language models."""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

__version__ = "0.1.0"


# The files that decide how an answer is corrected and whether a model is approved: the criteria and
# the checks (`checks`), the verdict and the cases (`grading`, `models`, `risk`), the reading of the
# criteria from the case files (`storage`) and the approval rule (`protocolo`). A protocol that
# freezes the correction (`corretor_id`) is judged against these and nothing else. The criteria
# themselves are data, covered by the case file's SHA-256, and the text of the question by the
# SHA-256 of the prompt of each answer.
GRADER_FILES = ("checks.py", "grading.py", "models.py", "protocolo.py", "risk.py", "storage.py")


def _digest_of(package: Path, names: list[str] | tuple[str, ...]) -> str:
    """SHA-256 of these files of `package`, in the order given, each with its name."""
    digest = hashlib.sha256()
    for name in names:
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update((package / name).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


@lru_cache(maxsize=1)
def code_digest() -> str:
    """SHA-256 of every Python source file in this package, in name order.

    Written on every answer so a measurement can be tied to the exact code
    that produced it. A git commit would not do: it says nothing about
    changes not yet committed, and reading git during a run is exactly what
    the project keeps to one session. This can be recomputed on any later
    checkout to find which commit matches.
    """
    package = Path(__file__).resolve().parent
    return _digest_of(package, [source.name for source in sorted(package.glob("*.py"))])


def build_id() -> str:
    """The version, and the first 12 characters of `code_digest`."""
    return f"{__version__}+{code_digest()[:12]}"


@lru_cache(maxsize=1)
def grader_digest() -> str:
    """SHA-256 of the files in `GRADER_FILES`: only what decides the correction and the approval."""
    return _digest_of(Path(__file__).resolve().parent, GRADER_FILES)


def grader_id() -> str:
    """The version, and the first 12 characters of `grader_digest`; "corretor" says which kind it is.

    Unlike `build_id`, it does not change when the report, the style or the translations are edited.
    """
    return f"{__version__}+corretor.{grader_digest()[:12]}"
