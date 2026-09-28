"""The HTML report's interface in other languages.

Only the interface is translated: titles, explanations, labels, the glossary.
The questions, the reference answers and the model answers are what was
measured, in European Portuguese, and they are never translated; a report in
another language says so at the top.

The catalogue is keyed by the Portuguese text itself, so the Portuguese report
is the source and reads exactly as it did before any translation existed. A
template carries `{name}` placeholders, filled after the lookup. A missing
translation falls back to Portuguese and is recorded in `MISSING`, which the
tests keep empty for every language.
"""

from __future__ import annotations

from .traducao_catalogo import CATALOG

LANGS = ("pt", "en", "es", "fr", "de")
NAMES = {
    "pt": "Português",
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
}
HTML_LANG = {"pt": "pt-PT", "en": "en", "es": "es", "fr": "fr", "de": "de"}

MISSING: set[tuple[str, str]] = set()


def t(text: str, lang: str = "pt", **values: object) -> str:
    """`text` in `lang`, with its placeholders filled."""
    if lang != "pt":
        translated = CATALOG.get(text, {}).get(lang)
        if translated is None:
            MISSING.add((lang, text))
        else:
            text = translated
    return text.format(**values) if values else text


def decimal(value: str, lang: str) -> str:
    """A number written with the decimal separator of `lang`."""
    return value.replace(",", ".") if lang == "en" else value.replace(".", ",")


__all__ = ["LANGS", "NAMES", "HTML_LANG", "MISSING", "t", "decimal", "CATALOG"]
