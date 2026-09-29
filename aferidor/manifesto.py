"""A manifest of a registered trial: the SHA-256 of every file in its folder.

A trial folder is evidence: raw answers, the case file as it was run, the
verdicts and the reports. Git keeps its history, but a copy sent by email or
downloaded as a zip carries none of it. The manifest travels with the folder
and lets anyone check, with the standard `shasum -a 256 -c`, that nothing in
it changed since it was written.

The format is the one `sha256sum` and `shasum` write, so checking it needs no
part of the Aferidor.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

MANIFEST = "MANIFESTO.sha256"


def _files(folder: Path) -> list[Path]:
    """Every file in the folder, the manifest itself and hidden files left out."""
    return sorted(
        p for p in folder.rglob("*")
        if p.is_file() and p.name != MANIFEST and not any(part.startswith(".") for part in p.relative_to(folder).parts)
    )


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 16), b""):
            digest.update(block)
    return digest.hexdigest()


def write_manifest(folder: Path) -> Path:
    """Write the manifest for `folder` and return its path."""
    folder = Path(folder)
    lines = [f"{_digest(p)}  {p.relative_to(folder).as_posix()}" for p in _files(folder)]
    target = folder / MANIFEST
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


@dataclass(frozen=True)
class ManifestCheck:
    """What differs between a folder and its manifest."""

    changed: tuple[str, ...]
    missing: tuple[str, ...]
    unlisted: tuple[str, ...]

    @property
    def intact(self) -> bool:
        return not (self.changed or self.missing or self.unlisted)


def check_manifest(folder: Path) -> ManifestCheck:
    """Compare every file in `folder` with the manifest written for it."""
    folder = Path(folder)
    listed: dict[str, str] = {}
    for line in (folder / MANIFEST).read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split("  ", 1)
            listed[name] = digest
    present = {p.relative_to(folder).as_posix(): p for p in _files(folder)}
    changed = tuple(sorted(n for n, d in listed.items() if n in present and _digest(present[n]) != d))
    missing = tuple(sorted(n for n in listed if n not in present))
    unlisted = tuple(sorted(n for n in present if n not in listed))
    return ManifestCheck(changed, missing, unlisted)


__all__ = ["MANIFEST", "write_manifest", "check_manifest", "ManifestCheck"]
