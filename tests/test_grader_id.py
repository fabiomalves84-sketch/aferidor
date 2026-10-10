"""`grader_id`: a version of what corrects and approves, apart from the version of the whole package."""

from __future__ import annotations

import ast
import hashlib
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import aferidor
from aferidor import GRADER_FILES, _digest_of, build_id, grader_id

PACKAGE = Path(aferidor.__file__).resolve().parent
LISTED = {name[:-3] for name in GRADER_FILES}
# `protocolo` words its messages with `traducao` and reads the build from the package: neither takes
# part in the approval rule, and putting them in the list would make every translation edit move the id.
PROTOCOLO_MAY_IMPORT = {"__init__", "traducao"}


def imports_of(module: str) -> set[str]:
    """The modules of the package a module imports, by name (`__init__` for `from . import x`)."""
    tree = ast.parse((PACKAGE / f"{module}.py").read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 1:
            if node.module:
                found.add(node.module.split(".")[0])
            else:
                found.add("__init__")
    return found


def closure(module: str) -> set[str]:
    seen: set[str] = set()
    pending = [module]
    while pending:
        for found in imports_of(pending.pop()):
            if found not in seen:
                seen.add(found)
                pending.append(found)
    return seen


class TestTheListCoversWhatCorrects(unittest.TestCase):
    def test_what_checks_and_grading_import_is_in_the_list(self):
        """If one of them starts importing another module, that module decides the correction too: it has
        to be in GRADER_FILES, and this fails until it is."""
        for module in ("checks", "grading"):
            with self.subTest(modulo=module):
                outside = closure(module) - LISTED
                self.assertEqual(outside, set(), f"{module} importa módulos fora de GRADER_FILES: acrescentá-los")

    def test_the_other_listed_files_import_only_listed_ones_except_what_protocolo_needs_for_its_messages(self):
        for module in LISTED - {"protocolo"}:
            with self.subTest(modulo=module):
                self.assertEqual(imports_of(module) - LISTED, set())
        self.assertEqual(imports_of("protocolo") - LISTED - PROTOCOLO_MAY_IMPORT, set())

    def test_every_listed_file_exists(self):
        for name in GRADER_FILES:
            with self.subTest(ficheiro=name):
                self.assertTrue((PACKAGE / name).is_file())


class TestTheIdentifiers(unittest.TestCase):
    def test_the_grader_id_has_the_version_the_word_corretor_and_twelve_hex_characters(self):
        self.assertRegex(grader_id(), rf"^{re.escape(aferidor.__version__)}\+corretor\.[0-9a-f]{{12}}$")

    def test_the_same_files_give_the_same_value(self):
        self.assertEqual(grader_id(), grader_id())
        self.assertEqual(
            grader_id(), f"{aferidor.__version__}+corretor.{_digest_of(PACKAGE, GRADER_FILES)[:12]}"
        )

    def test_the_build_id_is_still_the_hash_of_every_py_file_of_the_package(self):
        """Adding the grader id did not change what the build id means."""
        digest = hashlib.sha256()
        for source in sorted(PACKAGE.glob("*.py")):
            digest.update(source.name.encode("utf-8") + b"\0" + source.read_bytes() + b"\0")
        self.assertEqual(build_id(), f"{aferidor.__version__}+{digest.hexdigest()[:12]}")
        self.assertNotEqual(build_id().split("+")[1], grader_id().rsplit(".", 1)[1])

    def test_only_the_listed_files_move_it(self):
        """In a copy of the package: editing a listed file changes the digest, editing the report does not."""
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder)
            for name in (*GRADER_FILES, "html_report.py", "traducao_catalogo.py", "html_estilo.py"):
                shutil.copy(PACKAGE / name, copy / name)
            before = _digest_of(copy, GRADER_FILES)
            for presentation in ("html_report.py", "traducao_catalogo.py", "html_estilo.py"):
                with (copy / presentation).open("a", encoding="utf-8") as handle:
                    handle.write("\n# edited\n")
            self.assertEqual(_digest_of(copy, GRADER_FILES), before)
            for listed in GRADER_FILES:
                with self.subTest(ficheiro=listed):
                    original = (copy / listed).read_bytes()
                    (copy / listed).write_bytes(original + b"\n# edited\n")
                    self.assertNotEqual(_digest_of(copy, GRADER_FILES), before)
                    (copy / listed).write_bytes(original)


if __name__ == "__main__":
    unittest.main()
