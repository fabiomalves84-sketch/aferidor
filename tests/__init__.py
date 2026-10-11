"""Tests of the Aferidor.

Importing this package points the providers' key lookup at an empty folder, so no test, however it is started,
can open the repository's real `.env`. The tests that read a `.env` do it from a temporary one, by their own root.
"""

import tempfile
from pathlib import Path

from aferidor import providers

_NO_KEYS = tempfile.TemporaryDirectory(prefix="aferidor-sem-chaves-")
providers.KEYS_ROOT = Path(_NO_KEYS.name)
