"""The HTML report: same numbers as the Markdown one, escaped and self contained."""

from __future__ import annotations

import unittest
from pathlib import Path
from datetime import date, datetime

from aferidor import html_report, report
from aferidor.grading import consistency_by_case, consistency_by_model, grade_all
from aferidor.models import Answer, Case, Criterion, Source
from aferidor.risk import FailureType


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


def an_answer(text: str, case_id: str = "C1", model: str = "falso", sample: int = 1) -> Answer:
    return Answer(
        case_id=case_id, model=model, text=text, asked_at=datetime(2026, 9, 14), sample=sample
    )


def build(cases, answers, **kwargs) -> str:
    verdicts, missing = grade_all(cases, answers)
    return html_report.build(
        cases, answers, verdicts, missing=kwargs.pop("missing", missing),
        today=date(2026, 9, 14), **kwargs
    )


class TestDocument(unittest.TestCase):
    def test_it_is_a_complete_self_contained_document(self):
        text = build([a_case()], [an_answer("1 g")])
        self.assertTrue(text.startswith("<!DOCTYPE html>"))
        self.assertIn("<title>Relatório do Aferidor</title>", text)
        self.assertIn("</html>", text)

    def test_it_loads_nothing_from_the_network(self):
        text = build([a_case()], [an_answer("1 g")])
        self.assertNotIn("http://", text)
        self.assertNotIn("https://", text)
        self.assertNotIn("<link ", text)
        self.assertNotIn("<script", text)

    def test_it_works_in_dark_mode(self):
        self.assertIn("prefers-color-scheme: dark", build([a_case()], [an_answer("1 g")]))

    def test_it_carries_the_date(self):
        self.assertIn("2026-09-14", build([a_case()], [an_answer("1 g")]))


class TestEscaping(unittest.TestCase):
    def test_a_scripted_answer_is_escaped_not_executed(self):
        text = build(
            [a_case()], [an_answer("<script>alert(1)</script>", sample=1)]
        )
        self.assertNotIn("<script>alert", text)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", text)


class TestHeadline(unittest.TestCase):
    def test_the_critical_case_count_is_shown_per_model(self):
        text = build([a_case()], [an_answer("500 mg")])
        self.assertIn('<span class="destaque">1</span>', text)
        self.assertIn("de 1 casos com falha crítica em alguma amostra", text)


class TestGrid(unittest.TestCase):
    def test_cases_are_grouped_by_category(self):
        cases = [a_case("C1", category="dose"), a_case("C2", category="interacao")]
        text = build(cases, [an_answer("1 g", case_id="C1"), an_answer("1 g", case_id="C2")])
        self.assertIn("dose", text)
        self.assertIn("interacao", text)

    def test_the_state_is_written_out_not_just_shown_in_colour(self):
        text = build([a_case()], [an_answer("500 mg")])
        self.assertIn("estável errado", text)

    def test_a_stable_pass_says_so(self):
        text = build([a_case()], [an_answer("1 g")])
        self.assertIn("estável certo", text)

    def test_a_mixed_result_across_samples_is_unstable(self):
        text = build(
            [a_case()],
            [an_answer("1 g", sample=1), an_answer("500 mg", sample=2)],
        )
        self.assertIn("instável", text)

    def test_a_case_never_asked_to_a_model_says_so(self):
        cases = [a_case("C1"), a_case("C2")]
        text = build(cases, [an_answer("1 g", case_id="C1")], missing=["C2"])
        self.assertIn("sem resposta", text)

    def test_a_known_reason_is_shown_next_to_the_case(self):
        cases = [a_case("C1"), a_case("C2")]
        text = build(
            cases, [an_answer("1 g", case_id="C1")],
            missing=["C2"], reasons={"C2": "resposta truncada no limite de tokens"},
        )
        self.assertIn("C2 (resposta truncada no limite de tokens)", text)


class TestMissingSamples(unittest.TestCase):
    def test_a_partial_case_is_named_with_how_many_samples_came_in(self):
        cases = [a_case("C1"), a_case("C2")]
        answers = (
            [an_answer("1 g", case_id="C1", model="qwen", sample=s) for s in (1, 2, 3)]
            + [an_answer("1 g", case_id="C2", model="qwen", sample=s) for s in range(1, 6)]
        )
        text = build(cases, answers)
        self.assertIn("Amostras em falta", text)
        self.assertIn("C1 (qwen, 3 de 5 amostras)", text)

    def test_no_gaps_means_no_section(self):
        text = build([a_case("C1")], [an_answer("1 g", case_id="C1")])
        self.assertNotIn("Amostras em falta", text)


class TestDetail(unittest.TestCase):
    def test_a_failed_case_gets_a_details_block(self):
        text = build([a_case()], [an_answer("500 mg")])
        self.assertIn("<details>", text)
        self.assertIn("Que dose de amoxicilina?", text)
        self.assertIn("Amoxicilina 1000 mg de 8/8h", text)
        self.assertIn("Guia ATB", text)

    def test_a_passing_case_gets_no_details_block(self):
        text = build([a_case()], [an_answer("1 g")])
        self.assertNotIn("<details>", text)

    def test_each_distinct_answer_appears_once(self):
        text = build(
            [a_case()],
            [
                an_answer("500 mg", sample=1),
                an_answer("500 mg", sample=2),
                an_answer("600 mg", sample=3),
            ],
        )
        detail = text.split('id="casos-com-falha"', 1)[1]
        self.assertEqual(detail.count("500 mg"), 1)
        self.assertIn("600 mg", detail)


class TestNumbersMatchMarkdown(unittest.TestCase):
    def test_the_same_verdicts_give_the_same_counts_in_both_formats(self):
        cases = [a_case("C1"), a_case("C2")]
        answers = [
            an_answer("1 g", case_id="C1", sample=1),
            an_answer("500 mg", case_id="C1", sample=2),
            an_answer("500 mg", case_id="C2", sample=1),
        ]
        verdicts, missing = grade_all(cases, answers)
        markdown = report.build(cases, answers, verdicts, missing=missing, today=date(2026, 9, 14))
        page = html_report.build(cases, answers, verdicts, missing=missing, today=date(2026, 9, 14))

        consistency = consistency_by_case(cases, answers, verdicts)
        summary = consistency_by_model(consistency)["falso"]

        self.assertIn(f"{summary.critical_cases} de {summary.cases} casos", markdown)
        self.assertIn(f'<span class="destaque">{summary.critical_cases}</span>', page)
        self.assertIn(f"de {summary.cases} casos com falha crítica em alguma amostra", page)


class TestReadableByAnOutsider(unittest.TestCase):
    """The page has to say what it is before it shows a number."""

    def test_it_opens_by_saying_what_the_aferidor_is_and_how_to_read_it(self):
        text = build([a_case()], [an_answer("Amoxicilina 500 mg")])
        self.assertLess(text.index("O que é isto"), text.index('<span class="destaque">'))
        self.assertIn("Como ler este relatório", text)

    def test_every_section_is_reachable_from_the_index(self):
        text = build([a_case()], [an_answer("Amoxicilina 500 mg")])
        for anchor in ("resumo", "grelha", "falhas", "casos-com-falha", "condicoes", "metodo"):
            with self.subTest(anchor=anchor):
                self.assertIn(f'href="#{anchor}"', text)
                self.assertIn(f'id="{anchor}"', text)

    def test_a_state_is_never_shown_by_colour_alone(self):
        text = build([a_case()], [an_answer("Amoxicilina 500 mg")])
        self.assertIn("✕ estável errado", text)

    def test_failure_charts_share_one_scale_across_models(self):
        """Two charts on their own scales make a smaller count look as long as a bigger one."""
        answers = [an_answer("Amoxicilina 500 mg", model="a"), an_answer("nada", model="b")]
        extra = [an_answer("Amoxicilina 500 mg", case_id="C2", model="a")]
        text = build([a_case("C1"), a_case("C2")], answers + extra)
        self.assertIn("calc(2 / 2 * 100%)", text)
        self.assertIn("calc(1 / 2 * 100%)", text)


class TestModelNames(unittest.TestCase):
    """An identifier such as local:llama3.1:8b means nothing to most readers."""

    def test_known_models_get_a_readable_name_and_a_description(self):
        from aferidor.html_report import model_label

        self.assertEqual(
            model_label("local:llama3.1:8b"),
            ("Llama 3.1", "Meta · 8 mil milhões de parâmetros · corrido localmente, pelo Ollama"),
        )
        self.assertEqual(model_label("anthropic:claude-sonnet-4-5")[0], "Claude Sonnet 4.5")
        self.assertEqual(model_label("openai:gpt-4o")[0], "GPT-4o")

    def test_an_unknown_model_is_shown_by_its_identifier_not_guessed(self):
        from aferidor.html_report import model_label

        self.assertEqual(model_label("xpto-9"), ("xpto-9", ""))

    def test_the_identifier_is_always_shown_next_to_the_name(self):
        text = build([a_case()], [an_answer("1 g", model="local:qwen3:8b")])
        self.assertIn("Qwen 3", text)
        self.assertIn('<code class="modelo-id">local:qwen3:8b</code>', text)


class TestWhatJumpsOut(unittest.TestCase):
    """Areas, a direct comparison, the gravest mistakes and the models' context."""

    def two_models(self):
        cases = [a_case("C1"), a_case("C2")]
        answers = [
            an_answer("Amoxicilina 500 mg", "C1", model="local:llama3.1:8b"),
            an_answer("Amoxicilina 500 mg", "C2", model="local:llama3.1:8b"),
            an_answer("Amoxicilina 1 g", "C1", model="local:qwen3:8b"),
            an_answer("Amoxicilina 500 mg", "C2", model="local:qwen3:8b"),
        ]
        return build(cases, answers)

    def test_critical_cases_are_shown_by_clinical_area(self):
        text = self.two_models()
        self.assertIn('id="areas"', text)
        self.assertIn("<th scope=\"row\">Dose</th>", text)
        self.assertIn("<strong>2</strong> de 2", text)

    def test_the_comparison_names_the_better_model_and_says_when_it_can_be_chance(self):
        text = self.two_models()
        self.assertIn("<strong>Qwen 3</strong> teve menos casos com falha crítica (1 de 2, contra 2 de 2", text)
        self.assertIn("a diferença pode ser acaso", text)

    def test_the_gravest_mistakes_are_highlighted_with_what_should_have_been_said(self):
        text = self.two_models()
        worst = text.split('id="erros"', 1)[1].split("</section>", 1)[0]
        self.assertIn("A referência diz", worst)
        self.assertIn("Dose incorreta", worst)
        self.assertIn('href="#caso-C1"', worst)
        self.assertIn('id="caso-C1"', text)

    def test_small_local_models_are_put_in_context(self):
        self.assertIn("modelos abertos e pequenos", self.two_models())

    def test_models_not_run_locally_get_no_such_note(self):
        text = build([a_case()], [an_answer("1 g", model="openai:gpt-4o")])
        self.assertNotIn("modelos abertos e pequenos", text)


class TestGlossary(unittest.TestCase):
    """Abbreviations explained on hover, and a glossary of the ones used."""

    def page(self, answer_text="Amoxicilina 500 mg na DPOC"):
        case = Case(
            case_id="C1", category="dose",
            question="Exacerbação de DPOC: que dose? Ver no mapa da consulta.",
            reference="Amoxicilina 1000 mg de 8/8h", source=Source(name="DGS", reference="Norma"),
            criteria=(Criterion(kind="contem", terms=("1000 mg",), failure=FailureType.DOSE_INCORRETA),),
        )
        return build([case], [an_answer(answer_text)])

    def test_an_abbreviation_in_a_question_is_marked_with_its_definition(self):
        text = self.page()
        self.assertIn('data-termo="DPOC"', text)
        self.assertIn("Doença pulmonar obstrutiva crónica", text)

    def test_the_model_answer_is_never_marked(self):
        text = self.page()
        self.assertIn("<blockquote>Amoxicilina 500 mg na DPOC</blockquote>", text)

    def test_a_lowercase_word_is_not_taken_for_an_abbreviation(self):
        self.assertNotIn('data-termo="MAPA"', self.page())

    def test_the_glossary_lists_only_the_terms_the_page_uses(self):
        text = self.page()
        glossary = text.split('id="glossario"', 1)[1].split("</details>", 1)[0]
        self.assertIn(">DPOC</dt>", glossary)
        self.assertNotIn(">HbA1c</dt>", glossary)

    def test_every_marked_term_points_to_its_glossary_entry(self):
        import re

        text = self.page()
        for target in re.findall(r'aria-describedby="([^"]+)"', text):
            with self.subTest(target=target):
                self.assertIn(f'id="{target}"', text)


class TestCaseCodes(unittest.TestCase):
    def test_a_case_code_is_spelled_out(self):
        from aferidor.html_report import case_code_meaning

        self.assertEqual(
            case_code_meaning("ATB-PAC-001"),
            "Antibioterapia · Pneumonia adquirida na comunidade · caso n.º 1",
        )
        self.assertEqual(case_code_meaning("TAB-03"), "Cessação tabágica · caso n.º 3")

    def test_an_unknown_part_is_left_as_it_is(self):
        from aferidor.html_report import case_code_meaning

        self.assertEqual(case_code_meaning("XYZ-9"), "XYZ · caso n.º 9")

    def test_every_case_code_in_the_banks_is_fully_spelled_out(self):
        from aferidor.html_report import case_code_meaning
        from aferidor.storage import read_cases

        root = Path(__file__).resolve().parent.parent / "casos"
        for case in read_cases(root / "casos.json") + read_cases(root / "consulta.json"):
            with self.subTest(case=case.case_id):
                for part in case_code_meaning(case.case_id).split(" · "):
                    self.assertNotIn(part, case.case_id.split("-"))

    def test_codes_carry_their_meaning_on_the_page_and_the_glossary_explains_them(self):
        text = build([a_case("ATB-PAC-001")], [an_answer("Amoxicilina 500 mg", case_id="ATB-PAC-001")])
        self.assertIn('data-def="Antibioterapia · Pneumonia adquirida na comunidade · caso n.º 1"', text)
        self.assertIn(">Código do caso</dt>", text)


class TestEmpty(unittest.TestCase):
    def test_no_verdicts_says_so_instead_of_reporting_zero_percent(self):
        text = html_report.build([a_case()], [], [], today=date(2026, 9, 14))
        body = text.split("<body>", 1)[1]
        self.assertIn("Não há vereditos", body)
        self.assertNotIn("0%", body)


if __name__ == "__main__":
    unittest.main()
