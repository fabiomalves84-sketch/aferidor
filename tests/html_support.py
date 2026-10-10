"""Shared by the tests of the HTML report: the page builders, the word counters, the example."""

from __future__ import annotations

import json as _json
import re
import tempfile as _tempfile
from datetime import date
from html.parser import HTMLParser as _HTMLParser
from pathlib import Path

from aferidor import html_report
from aferidor import report as _report
from aferidor.grading import grade_all
from aferidor.models import Case, Criterion, Source
from aferidor.protocolo import read_protocol as _read_protocol
from aferidor.protocolo import template as _template
from aferidor.risk import FailureType
from aferidor.storage import read_answers as _read_answers
from aferidor.storage import read_cases as _read_cases


def a_case(case_id: str = "C1", category: str = "dose") -> Case:
    return Case(
        case_id=case_id,
        category=category,
        question="Que dose de amoxicilina?",
        reference="Amoxicilina 1000 mg de 8/8h",
        source=Source(name="Guia ATB", reference="p. 17"),
        criteria=(
            Criterion(kind="contem", terms=("1000 mg", "1 g"), failure=FailureType.DOSE_INCORRETA),
        ),
    )


def visible(page: str) -> str:
    """The page as a reader sees it: tags out, whitespace collapsed."""
    import html as _h
    text = " ".join(_h.unescape(re.sub(r"<[^>]+>", " ", page)).split())
    return re.sub(r" ([:;,.)])", r"\1", text)


def build(cases, answers, **kwargs) -> str:
    verdicts, missing = grade_all(cases, answers)
    return html_report.build(
        cases, answers, verdicts, missing=kwargs.pop("missing", missing),
        today=date(2026, 9, 14), **kwargs
    )


PAGES = ("inicio", "sobre", "fontes", "resultados", "areas", "casos", "conclusoes", "metodo")


def navigation(text: str) -> list[str]:
    nav = re.search(r'<nav class="indice".*?</nav>', text, flags=re.S).group(0)
    return re.findall(r'href="#([^"]+)"', nav)


def panels(text: str) -> list[str]:
    return re.findall(r'<section class="painel" id="([^"]+)"', text)


def tokens(block: str) -> dict[str, str]:
    return dict(re.findall(r"--([a-z0-9-]+):\s*(#[0-9a-f]{6})", block))


def contrast(fg: str, bg: str) -> float:
    """WCAG 2.1 contrast ratio between two #rrggbb colours."""
    def luminance(colour: str) -> float:
        channels = [int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
    high, low = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (high + 0.05) / (low + 0.05)


ROOT = Path(__file__).resolve().parent.parent


EXAMPLE_TRIALS = ("2026-09-29-gemma4-31b-casos", "2026-09-28-gemini-flash", "2026-09-27-locais-12-14b")


FIRST_PAGE_WORDS = {"reference": 148, "review_done": 143, "protocol": 157}


ABOUT_PAGE_WORDS = 270


FRAME_WORDS = 60


TRANSLATION_NOTICE_WORDS = 20


def words(text: str) -> int:
    """Words as the budget counts them: runs of characters between spaces that hold a letter or a digit."""
    return len([w for w in text.split() if re.search(r"\w", w)])


class _PanelText(_HTMLParser):
    """The text of one panel as a reader sees it, without what is data or a component.

    Left out: the cases and answers (`lang="pt-PT"`), blockquotes, code, whatever is only for screen
    readers (`.vh`), the cards, charts and tables, and the inside of a closed <details> (its
    <summary> counts). A paragraph written later counts by default: this is an exclusion list.
    """

    SKIP_TAGS = {"blockquote", "code", "style", "script", "table"}
    SKIP_CLASSES = {"vh", "cartoes", "comparacao", "legenda-estados", "legenda-riscos", "falhas-grelha", "grade-wrap"}
    VOID = {"br", "hr", "img", "input", "meta", "link"}

    def __init__(self) -> None:
        super().__init__()
        self.depth = 0
        self.skip_from: list[int] = []
        self.details: list[int] = []
        self.in_summary = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.VOID:
            return
        self.depth += 1
        a = dict(attrs)
        classes = set((a.get("class") or "").split())
        if tag in self.SKIP_TAGS or a.get("lang") == "pt-PT" or classes & self.SKIP_CLASSES:
            self.skip_from.append(self.depth)
        if tag == "details":
            self.details.append(self.depth)
        if tag == "summary":
            self.in_summary += 1

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if self.skip_from and self.skip_from[-1] == self.depth:
            self.skip_from.pop()
        if self.details and self.details[-1] == self.depth:
            self.details.pop()
        if tag == "summary":
            self.in_summary -= 1
        self.depth -= 1

    def handle_data(self, data):
        if self.skip_from:
            return
        if self.details and not self.in_summary:
            return
        self.parts.append(data)


def panel_html(page: str, ident: str) -> str:
    """The HTML of one page of the report: from its section to the next one, or to the end of <main>."""
    start = page.index(f'<section class="painel" id="{ident}"')
    following = [i for i in (page.find('<section class="painel" id="', start + 10), page.find("</main>", start)) if i > 0]
    return page[start:min(following)]


def panel_text(page: str, ident: str) -> str:
    parser = _PanelText()
    parser.feed(panel_html(page, ident))
    return " ".join(" ".join(parser.parts).split())


def element_text(page: str, css_class: str) -> str:
    """The visible text of the element with this class, on the first page."""
    first = panel_html(page, "inicio")
    at = first.index(f'class="{css_class}"')
    start = first.rindex("<", 0, at)
    tag = re.match(r"<(\w+)", first[start:]).group(1)
    depth, i = 0, start
    for m in re.finditer(rf"</?{tag}\b[^>]*>", first[start:]):
        depth += -1 if m.group(0).startswith("</") else 1
        if depth == 0:
            i = start + m.end()
            break
    parser = _PanelText()
    parser.feed(first[start:i])
    return " ".join(" ".join(parser.parts).split())


class _Example:
    """The public example: the real bank and the answers of the three trials it is made from."""

    _cache: dict = {}

    @classmethod
    def data(cls):
        if not cls._cache:
            cases = _read_cases(ROOT / "casos" / "casos.json")
            answers = [a for name in EXAMPLE_TRIALS for a in _read_answers(ROOT / "ensaios" / name / "respostas.jsonl")]
            verdicts, missing = grade_all(cases, answers)
            cls._cache.update(cases=cases, answers=answers, verdicts=verdicts, missing=missing)
        return cls._cache

    @staticmethod
    def bank_sha256() -> str:
        import hashlib

        return hashlib.sha256((ROOT / "casos" / "casos.json").read_bytes()).hexdigest()

    _pages: dict = {}

    @classmethod
    def page(cls, **kwargs) -> str:
        """The page, built once for each set of arguments (and each value of the review flag, which the
        tests switch): building the whole report takes a good part of a second, and over fifty tests ask."""
        from aferidor import fontes

        key = (tuple(sorted((k, repr(v)) for k, v in kwargs.items())), _report.CLINICAL_REVIEW_DONE)
        if key in cls._pages:
            return cls._pages[key]
        d = cls.data()
        built = dict(kwargs)
        built.setdefault(
            "confirmation", fontes.read_confirmation(ROOT / "casos" / "casos.json", [c.case_id for c in d["cases"]])
        )
        cls._pages[key] = html_report.build(
            d["cases"], d["answers"], d["verdicts"], missing=d["missing"], today=date(2026, 10, 10),
            cases_source=("casos/casos.json", cls.bank_sha256()), **built,
        )
        return cls._pages[key]

    @classmethod
    def protocol(cls, written_on: date | None = None):
        """A protocol for this bank. With a date before the first answer and the bank's own hash it
        raises no warning; the real one of 29/09 raises two with these answers."""
        if written_on is None:
            return _read_protocol(ROOT / "protocolos" / "2026-09-29-gemma4-31b-casos.json")
        with _tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "p.json"
            path.write_text(_json.dumps(_template("x", ROOT / "casos" / "casos.json", today=written_on)), encoding="utf-8")
            return _read_protocol(path)


def example_page_of(models: tuple[str, ...], **kwargs) -> str:
    """The example with only the answers of these models, for pages with two or one."""
    from aferidor import fontes

    d = _Example.data()
    answers = [a for a in d["answers"] if a.model in models]
    verdicts, missing = grade_all(d["cases"], answers)
    kwargs.setdefault(
        "confirmation", fontes.read_confirmation(ROOT / "casos" / "casos.json", [c.case_id for c in d["cases"]])
    )
    return html_report.build(
        d["cases"], answers, verdicts, missing=missing, today=date(2026, 10, 10),
        cases_source=("casos/casos.json", _Example.bank_sha256()), **kwargs,
    )


class _ConsultationExample:
    """The consultation bank with the answers of the trial that asked it, for the page with ten sources."""

    _cache: dict = {}

    @classmethod
    def page(cls, **kwargs) -> str:
        from aferidor import fontes

        if not cls._cache:
            cases = _read_cases(ROOT / "casos" / "consulta.json")
            answers = _read_answers(ROOT / "ensaios" / "2026-09-29-gemini-consulta" / "respostas.jsonl")
            verdicts, missing = grade_all(cases, answers)
            cls._cache.update(cases=cases, answers=answers, verdicts=verdicts, missing=missing)
        d = cls._cache
        kwargs.setdefault(
            "confirmation", fontes.read_confirmation(ROOT / "casos" / "consulta.json", [c.case_id for c in d["cases"]])
        )
        return html_report.build(
            d["cases"], d["answers"], d["verdicts"], missing=d["missing"], today=date(2026, 10, 10),
            cases_source=("casos/consulta.json", ""), **kwargs,
        )


SOURCES_PAGE_WORDS = 100


CONCLUSIONS_WORDS = 140


GEMMA, PHI, GEMINI = "gemini:gemma-4-31b-it", "local:phi4:14b", "gemini:gemini-3.5-flash-lite"


def conclusions_text(page: str) -> str:
    return visible(panel_text(page, "conclusoes"))


def fake_summaries(*results: tuple[str, int, int]) -> dict:
    """Summaries built by hand: (model, critical cases, cases), to reach branches the data does not."""
    from aferidor.grading import ConsistencySummary

    return {m: ConsistencySummary(model=m, cases=c, critical_cases=k, unstable_cases=0, sample_accuracy=0.5)
            for m, k, c in results}
