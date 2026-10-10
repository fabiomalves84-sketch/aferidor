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
# What a link preview (og:locale) wants: language_TERRITORY.
OG_LOCALE = {"pt": "pt_PT", "en": "en_US", "es": "es_ES", "fr": "fr_FR", "de": "de_DE"}

MISSING: set[tuple[str, str]] = set()

# Languages whose interface was translated by a machine and not yet read by a native speaker. Only
# Portuguese, the language the report is written in, is the reference. A report in any other says so
# at the top of every page and in the footer. Reviewing a language is taking it off this list.
UNREVIEWED = ("en", "es", "fr", "de")
UNREVIEWED_NOTICE = "Tradução automática, não revista por um falante nativo; em caso de dúvida vale o português."

# Grammatical forms of a term, for the languages whose word changes with the case. Keyed by the
# Portuguese term and the form. A language not listed here shows the plain CATALOG entry, so only
# German is written out (the other four languages read as "falha crítica" in every form).
FORMS: dict[tuple[str, str], dict[str, str]] = {
    ("falha crítica", "com artigo"): {"de": "kritischen Fehler"},  # mit einem / einen ...
    ("falha crítica", "sem artigo"): {"de": "kritischem Fehler"},  # mit ... in einer ...
}


def t(text: str, lang: str = "pt", form: str = "", **values: object) -> str:
    """`text` in `lang`, with its placeholders filled. `form` picks a grammatical form of a
    term (see FORMS); a language without that form shows the plain translation."""
    if lang != "pt":
        translated = FORMS.get((text, form), {}).get(lang) if form else None
        if translated is None:
            translated = CATALOG.get(text, {}).get(lang)
        if translated is None:
            MISSING.add((lang, text))
        else:
            text = translated
    return text.format(**values) if values else text


def decimal(value: str, lang: str) -> str:
    """A number written with the decimal separator of `lang`."""
    return value.replace(",", ".") if lang == "en" else value.replace(".", ",")


__all__ = [
    "LANGS", "NAMES", "HTML_LANG", "OG_LOCALE", "MISSING", "FORMS", "UNREVIEWED", "UNREVIEWED_NOTICE",
    "t", "decimal", "CATALOG",
]
