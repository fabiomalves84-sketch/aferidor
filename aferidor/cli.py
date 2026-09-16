"""Command line for running the bench.

    python -m aferidor executar --fornecedor falso
    python -m aferidor executar --fornecedor openai --modelo gpt-4o
    python -m aferidor executar --fornecedor anthropic --limite 3
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import html_report, report
from .grading import grade_all, self_check, tally_by_model
from .providers import (
    AnthropicProvider,
    FakeProvider,
    LocalProvider,
    OpenAIProvider,
    Provider,
    ProviderError,
)
from .runner import RunConfig, run
from .storage import read_answers, read_cases, write_verdicts

DEFAULT_CASES = Path("casos/casos.json")
DEFAULT_OUTPUT = Path("data/respostas.jsonl")
DEFAULT_VERDICTS = Path("data/vereditos.json")
DEFAULT_REPORT = Path("relatorios/relatorio.md")
DEFAULT_REPORT_HTML = Path("relatorios/relatorio.html")


def build_provider(kind: str, model: str | None, temperature: float = 0.0) -> Provider:
    if kind == "falso":
        return FakeProvider(name=f"falso:{model}" if model else "falso", temperature=temperature)
    if kind == "openai":
        kwargs = {"temperature": temperature}
        return OpenAIProvider(model=model, **kwargs) if model else OpenAIProvider(**kwargs)
    if kind == "anthropic":
        kwargs = {"temperature": temperature}
        return AnthropicProvider(model=model, **kwargs) if model else AnthropicProvider(**kwargs)
    if kind == "local":
        kwargs = {"temperature": temperature}
        return LocalProvider(model=model, **kwargs) if model else LocalProvider(**kwargs)
    raise ValueError(f"fornecedor desconhecido {kind!r}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="aferidor", description="Banco de ensaio clinico")
    sub = parser.add_subparsers(dest="comando", required=True)

    executar = sub.add_parser("executar", help="enviar os casos a um modelo")
    executar.add_argument(
        "--fornecedor", choices=("falso", "openai", "anthropic", "local"), default="falso"
    )
    executar.add_argument("--modelo", default=None, help="identificador do modelo")
    executar.add_argument("--casos", type=Path, default=DEFAULT_CASES)
    executar.add_argument("--saida", type=Path, default=DEFAULT_OUTPUT)
    executar.add_argument("--limite", type=int, default=0, help="0 corre todos")
    executar.add_argument("--tentativas", type=int, default=3)
    executar.add_argument(
        "--repeticoes", type=int, default=1, help="quantas vezes perguntar cada caso"
    )
    executar.add_argument(
        "--temperatura", type=float, default=0.0, help="temperatura pedida ao fornecedor"
    )
    executar.add_argument(
        "--recomecar",
        action="store_true",
        help="ignorar respostas anteriores deste modelo e perguntar tudo de novo",
    )

    verificar = sub.add_parser(
        "verificar", help="conferir se cada caso passa nos seus proprios criterios"
    )
    verificar.add_argument("--casos", type=Path, default=DEFAULT_CASES)

    classificar = sub.add_parser("classificar", help="avaliar as respostas guardadas")
    classificar.add_argument("--casos", type=Path, default=DEFAULT_CASES)
    classificar.add_argument("--respostas", type=Path, default=DEFAULT_OUTPUT)
    classificar.add_argument("--saida", type=Path, default=DEFAULT_VERDICTS)
    classificar.add_argument(
        "--limite", type=int, default=0,
        help="0 usa todos os casos; tem de bater com o --limite usado em executar",
    )

    ensaio = sub.add_parser(
        "ensaio", help="executar, classificar e escrever o relatorio de uma vez"
    )
    ensaio.add_argument(
        "--fornecedor", choices=("falso", "openai", "anthropic", "local"), default="falso"
    )
    ensaio.add_argument("--modelo", default=None)
    ensaio.add_argument("--casos", type=Path, default=DEFAULT_CASES)
    ensaio.add_argument("--saida", type=Path, default=DEFAULT_OUTPUT)
    ensaio.add_argument("--vereditos", type=Path, default=DEFAULT_VERDICTS)
    ensaio.add_argument("--relatorio", type=Path, default=DEFAULT_REPORT)
    ensaio.add_argument("--limite", type=int, default=0)
    ensaio.add_argument("--tentativas", type=int, default=3)
    ensaio.add_argument(
        "--repeticoes", type=int, default=1, help="quantas vezes perguntar cada caso"
    )
    ensaio.add_argument(
        "--temperatura", type=float, default=0.0, help="temperatura pedida ao fornecedor"
    )
    ensaio.add_argument("--recomecar", action="store_true")
    ensaio.add_argument("--fontes-confirmadas", action="store_true")

    modelos = sub.add_parser(
        "modelos", help="perguntar ao fornecedor que modelos tem disponiveis"
    )
    modelos.add_argument("--fornecedor", choices=("openai", "anthropic", "local"), required=True)

    relatorio = sub.add_parser("relatorio", help="escrever o relatorio legivel")
    relatorio.add_argument("--casos", type=Path, default=DEFAULT_CASES)
    relatorio.add_argument("--respostas", type=Path, default=DEFAULT_OUTPUT)
    relatorio.add_argument("--saida", type=Path, default=None)
    relatorio.add_argument("--formato", choices=("md", "html"), default="md")
    relatorio.add_argument(
        "--limite", type=int, default=0,
        help="0 usa todos os casos; tem de bater com o --limite usado em executar",
    )
    relatorio.add_argument(
        "--fontes-confirmadas",
        action="store_true",
        help="omitir o aviso de fontes por confirmar (so depois de as confirmar)",
    )

    return parser.parse_args(argv)


def comando_executar(args: argparse.Namespace) -> int:
    cases = read_cases(args.casos)
    if args.limite > 0:
        cases = cases[: args.limite]

    try:
        provider = build_provider(args.fornecedor, args.modelo, temperature=args.temperatura)
    except ProviderError as error:
        print(f"erro: {error}", file=sys.stderr)
        return 2

    print(f"{len(cases)} casos x {args.repeticoes} amostra(s), modelo {provider.name}")

    def progress(case, answer, status) -> None:
        mark = "." if status == "ok" else ("-" if status == "ja respondido" else "!")
        detail = f" {status}" if status not in ("ok",) else ""
        print(f"  {mark} {case.case_id}{detail}")

    result = run(
        cases,
        provider,
        path=None if args.recomecar else args.saida,
        config=RunConfig(attempts=args.tentativas),
        repetitions=args.repeticoes,
        progress=progress,
    )

    if args.recomecar:
        from .storage import write_answers

        args.saida.parent.mkdir(parents=True, exist_ok=True)
        write_answers(result.answers, args.saida)

    print(result.summary())
    print(f"respostas em {args.saida}")
    for case_id, message in result.errors.items():
        print(f"  por responder {case_id}: {message}", file=sys.stderr)
    return 0 if result.complete else 1


def comando_classificar(args: argparse.Namespace) -> int:
    cases = read_cases(args.casos)
    if getattr(args, "limite", 0) > 0:
        cases = cases[: args.limite]
    if not args.respostas.exists():
        print(f"erro: nao ha respostas em {args.respostas}", file=sys.stderr)
        return 2

    answers = read_answers(args.respostas)
    verdicts, missing = grade_all(cases, answers)

    args.saida.parent.mkdir(parents=True, exist_ok=True)
    write_verdicts(verdicts, args.saida)

    for model, counts in tally_by_model(verdicts).items():
        print(f"\n{model}")
        print(f"  {counts.passed}/{counts.total} corretas ({counts.accuracy:.0%})")
        if counts.critical:
            print(f"  {counts.critical} respostas com falha de risco critico")
        for failure, number in counts.worst_first():
            print(f"    {failure.value:<26} {number:>3}  risco {failure.risk}")
        for case_id, failures in sorted(counts.failed_cases.items()):
            print(f"    {case_id}: {', '.join(failures)}")

    if missing:
        print(f"\ncasos sem resposta valida: {', '.join(sorted(set(missing)))}", file=sys.stderr)
    print(f"\nvereditos em {args.saida}")
    return 0


def comando_verificar(args: argparse.Namespace) -> int:
    cases = read_cases(args.casos)
    broken = self_check(cases)

    print(f"{len(cases) - len(broken)}/{len(cases)} casos coerentes")
    for case, verdict in broken:
        print(f"\n{case.case_id}: a propria referencia nao passa", file=sys.stderr)
        print(f"  referencia: {case.reference}", file=sys.stderr)
        for result in verdict.results:
            if not result.passed:
                print(
                    f"  criterio {result.criterion.kind} {list(result.criterion.terms)}"
                    f" -> {result.evidence}",
                    file=sys.stderr,
                )
    return 1 if broken else 0


def comando_relatorio(args: argparse.Namespace) -> int:
    cases = read_cases(args.casos)
    if getattr(args, "limite", 0) > 0:
        cases = cases[: args.limite]
    if not args.respostas.exists():
        print(f"erro: nao ha respostas em {args.respostas}", file=sys.stderr)
        return 2

    answers = read_answers(args.respostas)
    verdicts, missing = grade_all(cases, answers)
    formato = getattr(args, "formato", "md")

    saida = args.saida
    if saida is None:
        saida = DEFAULT_REPORT_HTML if formato == "html" else DEFAULT_REPORT

    builder = html_report.build if formato == "html" else report.build
    text = builder(
        cases,
        answers,
        verdicts,
        missing=missing,
        sources_verified=args.fontes_confirmadas,
    )
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(text, encoding="utf-8")
    print(f"relatorio em {saida} ({len(text.splitlines())} linhas)")
    return 0


def comando_modelos(args: argparse.Namespace) -> int:
    try:
        provider = build_provider(args.fornecedor, None)
        nomes = provider.available_models()
    except ProviderError as error:
        print(f"erro: {error}", file=sys.stderr)
        return 2
    for nome in nomes:
        print(nome)
    print(f"\n{len(nomes)} modelos em {args.fornecedor}", file=sys.stderr)
    return 0


def comando_ensaio(args: argparse.Namespace) -> int:
    """Os tres passos de uma vez, parando ao primeiro que falhe.

    A verificacao de coerencia dos casos corre primeiro e de proposito. Perguntar
    a um modelo custa dinheiro; descobrir depois que um caso estava partido custa
    o dinheiro outra vez.
    """
    cases = read_cases(args.casos)
    broken = self_check(cases)
    if broken:
        for case, _ in broken:
            print(f"erro: {case.case_id} nao passa nos proprios criterios", file=sys.stderr)
        print("corrige os casos antes de gastar uma execucao", file=sys.stderr)
        return 2

    executar_args = argparse.Namespace(
        fornecedor=args.fornecedor, modelo=args.modelo, casos=args.casos,
        saida=args.saida, limite=args.limite, tentativas=args.tentativas,
        repeticoes=args.repeticoes, temperatura=args.temperatura,
        recomecar=args.recomecar,
    )
    codigo = comando_executar(executar_args)
    if codigo == 2:
        return codigo

    classificar_args = argparse.Namespace(
        casos=args.casos, respostas=args.saida, saida=args.vereditos, limite=args.limite
    )
    comando_classificar(classificar_args)

    relatorio_args = argparse.Namespace(
        casos=args.casos, respostas=args.saida, saida=args.relatorio,
        fontes_confirmadas=args.fontes_confirmadas, limite=args.limite,
    )
    comando_relatorio(relatorio_args)

    if codigo == 1:
        print(
            "\naviso: houve casos sem resposta; o relatorio nomeia-os e nao os conta",
            file=sys.stderr,
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.comando == "executar":
        return comando_executar(args)
    if args.comando == "verificar":
        return comando_verificar(args)
    if args.comando == "classificar":
        return comando_classificar(args)
    if args.comando == "relatorio":
        return comando_relatorio(args)
    if args.comando == "ensaio":
        return comando_ensaio(args)
    if args.comando == "modelos":
        return comando_modelos(args)
    return 2


__all__ = ["main", "build_provider", "parse_args"]
