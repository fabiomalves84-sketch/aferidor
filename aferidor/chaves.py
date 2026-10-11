"""Reading API keys without ever showing them.

A key comes from the environment first and, only if it is missing there, from a `.env` file at the root
of the repository. Only variables the catalogue declares are read from that file; every other line is
skipped before its value is kept. The value never reaches a message, a log or a `repr`: it lives in a
`Secret`, which prints as hidden and is revealed only by an explicit call at the moment of sending.

A `.env` that is a link pointing outside the repository is refused, not followed: a link is how a file
elsewhere on the disk would end up read in the project's name.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable, Mapping
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ".env"
_MAX_BYTES = 64 * 1024
_LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$")


class KeysError(RuntimeError):
    """A key file cannot be read safely. The message never carries a value."""


class Secret:
    """A value that does not print. `reveal()` is the one place it comes out."""

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        self._value = value

    def reveal(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return "Secret(<oculto>)"

    __str__ = __repr__

    def __bool__(self) -> bool:
        return bool(self._value)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Secret) and self._value == other._value

    def __hash__(self) -> int:
        return hash(("Secret", len(self._value)))


def _unquote(raw: str) -> str:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value.split(" #", 1)[0].strip()


def parse_env(text: str, wanted: Iterable[str]) -> dict[str, str]:
    """The wanted variables found in `.env` text. Malformed lines and other variables are skipped silently."""
    names = set(wanted)
    found: dict[str, str] = {}
    for line in text.splitlines():
        match = _LINE.match(line)
        if not match or line.lstrip().startswith("#") or match.group(1) not in names:
            continue
        value = _unquote(match.group(2))
        if value:
            found[match.group(1)] = value
    return found


def _env_path(root: Path) -> Path | None:
    """The `.env` of this repository, or None if there is none; refuses one that leads outside it."""
    path = root / ENV_FILE
    if not path.is_symlink() and not path.exists():
        return None
    resolved_root = root.resolve()
    outside = False
    try:
        path.resolve(strict=True).relative_to(resolved_root)
    except (OSError, ValueError):
        outside = True
    if outside:
        raise KeysError(
            "o ficheiro .env é uma ligação que aponta para fora do repositório e não é seguido; "
            "substituir por um ficheiro normal na raiz do repositório"
        )
    return path if path.is_file() else None


def read_key(
    variable: str,
    declared: Iterable[str],
    root: Path,
    environ: Mapping[str, str] | None = None,
) -> Secret | None:
    """The key named by `variable`, from the environment, else from `<root>/.env`; None if neither has it.

    `root` has no default on purpose: a caller always says whose `.env` it means, so a test can never open
    the real one by accident. `declared` is the catalogue's list of key variables; asking for one that is
    not in it is a mistake in the caller and is refused.
    """
    allowed = frozenset(declared)
    if variable not in allowed:
        raise KeysError(f"a variável {variable!r} não está declarada no catálogo e não é lida")
    env = os.environ if environ is None else environ
    value = env.get(variable, "").strip()
    if value:
        return Secret(value)
    path = _env_path(root)
    if path is None:
        return None
    # The reason is kept and raised after the `except`, never inside it: an exception raised there keeps
    # the original as `__context__`, and a `UnicodeDecodeError` carries the bytes it could not read.
    problem = ""
    text = ""
    try:
        if path.stat().st_size > _MAX_BYTES:
            problem = "o ficheiro .env é grande de mais para ser um ficheiro de chaves e não foi lido"
        else:
            text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        problem = "não consegui ler o ficheiro .env (permissões ou codificação)"
    if problem:
        raise KeysError(problem)
    value = parse_env(text, [variable]).get(variable, "")
    return Secret(value) if value else None
