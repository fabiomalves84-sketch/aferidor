"""Reading keys: the environment first, then a `.env` of the repository, only for declared variables, and
never letting the value out in a message, a repr or an exception. Every `.env` here is a temporary file
with a made-up value; the repository's own is never opened."""

from __future__ import annotations

import builtins
import inspect
import io
import os
import pickle
import socket
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from aferidor import chaves
from aferidor.catalogo import CatalogError, load_catalog, parse_catalog
from aferidor.chaves import ENV_FILE, REPOSITORY_ROOT, KeysError, Secret, parse_env, read_key

FAKE = "valor-falso-9f3a7c21b8"
OTHER = "outro-valor-falso-4d4d4d"
DECLARED = {"CHAVE_FALSA", "OUTRA_FALSA"}
REAL_ENV = (REPOSITORY_ROOT / ENV_FILE).resolve()


def setUpModule() -> None:
    """No connection, and a guard on every way of opening the repository's real `.env`."""
    def refuse(*args, **kwargs):
        raise AssertionError("tentativa de ligação de rede num teste")

    def guarded(original):
        def wrapper(target, *args, **kwargs):
            if isinstance(target, (str, os.PathLike)) and Path(target).resolve() == REAL_ENV:
                raise AssertionError("um teste tentou abrir o .env verdadeiro do repositório")
            return original(target, *args, **kwargs)
        return wrapper

    real_read_text = Path.read_text

    def guarded_read_text(self, *args, **kwargs):
        if self.resolve() == REAL_ENV:
            raise AssertionError("um teste tentou abrir o .env verdadeiro do repositório")
        return real_read_text(self, *args, **kwargs)

    patches = [
        mock.patch.object(socket.socket, "connect", refuse),
        mock.patch.object(builtins, "open", guarded(builtins.open)),
        mock.patch.object(io, "open", guarded(io.open)),
        mock.patch.object(Path, "read_text", guarded_read_text),
    ]
    for patcher in patches:
        patcher.start()
        unittest.addModuleCleanup(patcher.stop)


class Folder:
    """A temporary repository root, with an optional `.env`."""

    def __init__(self, env: str | None = None) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.root = Path(self._dir.name)
        if env is not None:
            (self.root / ENV_FILE).write_text(env, encoding="utf-8")

    def __enter__(self) -> Path:
        return self.root

    def __exit__(self, *exc) -> None:
        self._dir.cleanup()


class TestTheEnvironmentComesFirst(unittest.TestCase):
    def test_the_environment_wins_over_the_file(self):
        with Folder(f"CHAVE_FALSA={OTHER}\n") as root:
            found = read_key("CHAVE_FALSA", DECLARED, root, {"CHAVE_FALSA": FAKE})
        self.assertEqual(found.reveal(), FAKE)

    def test_with_the_value_in_the_environment_the_file_is_not_even_opened(self):
        with Folder(f"CHAVE_FALSA={OTHER}\n") as root, mock.patch.object(Path, "read_text", side_effect=AssertionError("aberto")):
            self.assertEqual(read_key("CHAVE_FALSA", DECLARED, root, {"CHAVE_FALSA": FAKE}).reveal(), FAKE)

    def test_an_empty_or_blank_environment_value_falls_through_to_the_file(self):
        for blank in ("", "   "):
            with self.subTest(valor=repr(blank)), Folder(f"CHAVE_FALSA={FAKE}\n") as root:
                self.assertEqual(read_key("CHAVE_FALSA", DECLARED, root, {"CHAVE_FALSA": blank}).reveal(), FAKE)

    def test_nothing_anywhere_is_none_not_an_error(self):
        with Folder() as root:
            self.assertIsNone(read_key("CHAVE_FALSA", DECLARED, root, {}))
        with Folder("# só um comentário\n") as root:
            self.assertIsNone(read_key("CHAVE_FALSA", DECLARED, root, {}))

    def test_the_real_environment_is_used_when_none_is_given(self):
        with Folder() as root, mock.patch.dict(os.environ, {"CHAVE_FALSA": FAKE}):
            self.assertEqual(read_key("CHAVE_FALSA", DECLARED, root).reveal(), FAKE)


class TestOnlyDeclaredVariablesAreRead(unittest.TestCase):
    def test_a_variable_the_catalogue_does_not_declare_is_refused(self):
        with Folder(f"PATH_SECRETA={FAKE}\n") as root:
            with self.assertRaisesRegex(KeysError, "não está declarada no catálogo"):
                read_key("PATH_SECRETA", DECLARED, root, {"PATH_SECRETA": FAKE})

    def test_other_variables_in_the_file_are_not_kept(self):
        text = f"NAO_DECLARADA={OTHER}\nCHAVE_FALSA={FAKE}\n"
        self.assertEqual(parse_env(text, ["CHAVE_FALSA"]), {"CHAVE_FALSA": FAKE})
        self.assertNotIn(OTHER, repr(parse_env(text, ["CHAVE_FALSA"])))

    def test_each_declared_variable_gets_its_own_value(self):
        with Folder(f"CHAVE_FALSA={FAKE}\nOUTRA_FALSA={OTHER}\n") as root:
            self.assertEqual(read_key("CHAVE_FALSA", DECLARED, root, {}).reveal(), FAKE)
            self.assertEqual(read_key("OUTRA_FALSA", DECLARED, root, {}).reveal(), OTHER)

    def test_the_shipped_catalogue_declares_only_the_three_provider_keys(self):
        declared = load_catalog().key_variables()
        with Folder(f"HOME={FAKE}\nOPENAI_API_KEY={OTHER}\n") as root:
            self.assertEqual(read_key("OPENAI_API_KEY", declared, root, {}).reveal(), OTHER)
            with self.assertRaises(KeysError):
                read_key("HOME", declared, root, {})


class TestTheFormatOfTheFile(unittest.TestCase):
    def test_the_usual_forms_are_understood(self):
        text = (
            "# comentário\n"
            f"CHAVE_FALSA={FAKE}\n"
            f"export OUTRA_FALSA = '{OTHER}'\n"
        )
        self.assertEqual(parse_env(text, DECLARED), {"CHAVE_FALSA": FAKE, "OUTRA_FALSA": OTHER})
        self.assertEqual(parse_env(f'CHAVE_FALSA="{FAKE}"\n', DECLARED), {"CHAVE_FALSA": FAKE})
        self.assertEqual(parse_env(f"CHAVE_FALSA={FAKE} # nota\n", DECLARED), {"CHAVE_FALSA": FAKE})

    def test_malformed_lines_are_skipped_and_the_good_ones_still_read(self):
        text = f"sem igual\n=sem nome\n1INVALIDO=x\nCHAVE FALSA=x\n#CHAVE_FALSA={OTHER}\nCHAVE_FALSA=\n\x00lixo\nCHAVE_FALSA={FAKE}\n"
        self.assertEqual(parse_env(text, DECLARED), {"CHAVE_FALSA": FAKE})

    def test_an_empty_value_is_no_key(self):
        with Folder("CHAVE_FALSA=\nOUTRA_FALSA=''\n") as root:
            self.assertIsNone(read_key("CHAVE_FALSA", DECLARED, root, {}))
            self.assertIsNone(read_key("OUTRA_FALSA", DECLARED, root, {}))

    def test_windows_line_endings_do_not_leak_into_the_value(self):
        self.assertEqual(parse_env(f"CHAVE_FALSA={FAKE}\r\n", DECLARED), {"CHAVE_FALSA": FAKE})

    def test_a_file_that_is_not_text_or_is_huge_is_an_error_that_does_not_show_it(self):
        with Folder() as root:
            (root / ENV_FILE).write_bytes(b"\xff\xfe\x00CHAVE_FALSA=x")
            with self.assertRaisesRegex(KeysError, "não consegui ler"):
                read_key("CHAVE_FALSA", DECLARED, root, {})
            (root / ENV_FILE).write_text("#" * (70 * 1024), encoding="utf-8")
            with self.assertRaisesRegex(KeysError, "grande de mais"):
                read_key("CHAVE_FALSA", DECLARED, root, {})


class TestLinksOutsideTheRepository(unittest.TestCase):
    def test_a_link_to_a_file_outside_is_not_followed(self):
        with Folder() as root, Folder(f"CHAVE_FALSA={FAKE}\n") as elsewhere:
            (root / ENV_FILE).symlink_to(elsewhere / ENV_FILE)
            with self.assertRaisesRegex(KeysError, "aponta para fora do repositório"):
                read_key("CHAVE_FALSA", DECLARED, root, {})

    def test_a_link_inside_the_repository_is_fine(self):
        with Folder() as root:
            (root / "segredos.txt").write_text(f"CHAVE_FALSA={FAKE}\n", encoding="utf-8")
            (root / ENV_FILE).symlink_to(root / "segredos.txt")
            self.assertEqual(read_key("CHAVE_FALSA", DECLARED, root, {}).reveal(), FAKE)

    def test_a_broken_link_is_refused_not_ignored_as_if_there_were_no_file(self):
        with Folder() as root:
            (root / ENV_FILE).symlink_to(root / "nao-existe")
            with self.assertRaises(KeysError):
                read_key("CHAVE_FALSA", DECLARED, root, {})

    def test_a_directory_called_env_is_no_key_file(self):
        with Folder() as root:
            (root / ENV_FILE).mkdir()
            self.assertIsNone(read_key("CHAVE_FALSA", DECLARED, root, {}))


class TestTheValueNeverComesOut(unittest.TestCase):
    def test_a_secret_prints_hidden_in_every_form(self):
        secret = Secret(FAKE)
        for text in (repr(secret), str(secret), f"{secret}", f"{secret!r}", "%s %r" % (secret, secret), repr([secret]),
                     repr({"k": secret}), str((secret,))):
            self.assertNotIn(FAKE, text)
        self.assertEqual(repr(secret), "Secret(<oculto>)")

    def test_a_secret_has_no_attributes_that_carry_the_value_around(self):
        secret = Secret(FAKE)
        self.assertFalse(hasattr(secret, "__dict__"))
        self.assertNotIn(FAKE, repr(secret.__slots__))
        self.assertTrue(secret)
        self.assertFalse(Secret(""))

    def test_the_hash_does_not_depend_on_the_text_beyond_its_length(self):
        self.assertEqual(hash(Secret("a")), hash(Secret("b")))
        self.assertEqual(Secret("a"), Secret("a"))
        self.assertNotEqual(Secret("a"), Secret("b"))
        self.assertNotEqual(Secret("a"), "a")

    def test_no_exception_in_any_failure_path_carries_the_value(self):
        """Provoke every error the module can raise, with the made-up value around, and look for it in all
        of the exceptions: message, repr, arguments, and the chained cause."""
        raised: list[BaseException] = []

        def attempt(function, *args, **kwargs):
            try:
                function(*args, **kwargs)
            except (KeysError, CatalogError) as error:
                raised.append(error)
            else:
                self.fail("devia ter falhado")

        with Folder(f"PATH_SECRETA={FAKE}\n") as root:
            attempt(read_key, "PATH_SECRETA", DECLARED, root, {"PATH_SECRETA": FAKE})
        with Folder() as root, Folder(f"CHAVE_FALSA={FAKE}\n") as elsewhere:
            (root / ENV_FILE).symlink_to(elsewhere / ENV_FILE)
            attempt(read_key, "CHAVE_FALSA", DECLARED, root, {})
        with Folder() as root:
            (root / ENV_FILE).write_bytes(FAKE.encode() + b"\xff\xfe\x00")
            attempt(read_key, "CHAVE_FALSA", DECLARED, root, {})
        with Folder() as root:
            (root / ENV_FILE).write_text(f"CHAVE_FALSA={FAKE}\n" + "#" * (70 * 1024), encoding="utf-8")
            attempt(read_key, "CHAVE_FALSA", DECLARED, root, {})
        with Folder() as root:
            (root / ENV_FILE).symlink_to(root / "nao-existe")
            attempt(read_key, "CHAVE_FALSA", DECLARED, root, {})
        attempt(parse_catalog, f'{{"chave": "{FAKE}", ')
        attempt(parse_catalog, f'{{"lido_em": "2026-10-11", "usd_para_eur": {{"valor": "{FAKE}", "fonte": "x"}}, "modelos": {{}}}}')

        self.assertEqual(len(raised), 7)
        for error in raised:
            link: BaseException | None = error
            while link is not None:
                with self.subTest(erro=type(link).__name__):
                    for text in (str(link), repr(link), repr(link.args)):
                        self.assertNotIn(FAKE, text)
                self.assertIsNone(link.__context__, "a exceção não pode guardar a que a causou")
                link = link.__cause__

    def test_the_module_and_its_help_hold_no_value(self):
        self.assertNotIn(FAKE, inspect.getsource(chaves))
        self.assertNotIn(FAKE, pickle.dumps(Secret("")).decode("latin-1"))

    def test_a_key_in_the_file_never_shows_up_when_an_unrelated_variable_is_asked_for(self):
        with Folder(f"CHAVE_FALSA={FAKE}\n") as root:
            self.assertIsNone(read_key("OUTRA_FALSA", DECLARED, root, {}))


class TestTheRealFileIsNeverOpened(unittest.TestCase):
    def test_the_root_has_no_default_so_a_test_cannot_reach_it_by_accident(self):
        parameter = inspect.signature(read_key).parameters["root"]
        self.assertIs(parameter.default, inspect.Parameter.empty)

    def test_the_guard_of_this_module_would_catch_an_attempt(self):
        with self.assertRaisesRegex(AssertionError, "o .env verdadeiro"):
            open(REAL_ENV)

    def test_the_repository_ignores_the_file(self):
        ignored = (REPOSITORY_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn(".env", [line.strip() for line in ignored])


if __name__ == "__main__":
    unittest.main()
