"""Command line for running the bench.

    python -m aferidor executar --fornecedor falso
    python -m aferidor executar --fornecedor openai --modelo gpt-4o
    python -m aferidor executar --fornecedor anthropic --limite 3
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .grading import grade_all, self_check, tally_by_model
from .providers import AnthropicProvider, FakeProvider, OpenAIProvider, Provider, ProviderError
from .runner import RunConfig, run
from .storage import read_answers, read_cases, write_verdicts

DEFAULT_CASES = Path("casos/casos.json")
DEFAULT_OUTPUT = Path("data/respostas.jsonl")
DEFAULT_VERDICTS = Path("data/vereditos.json")


def build_provider(kind: str, model: str | None) -> Provider:
    if kind == "falso":
        return FakeProvider(name=f"falso:{model}" if model else "falso")
    if kind == "openai":
        return OpenAIProvider(model=model) if model else OpenAIProvider()
    if kind == "anthropic":
        return AnthropicProvider(model=model) if model else AnthropicProvider()
    raise ValueError(f"fornecedor desconhecido {kind!r}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="aferidor", description="Banco de ensaio clinico")
    sub = parser.add_subparsers(dest="comando", required=True)

    executar = sub.add_parser("executar", help="enviar os casos a um modelo")
    executar.add_argument(
        "--fornecedor", choices=("falso", "openai", "anthropic"), default="falso"
    )
    executar.add_argument("--modelo", default=None, help="identificador do modelo")
    executar.add_argument("--casos", type=Path, default=DEFAULT_CASES)
    executar.add_argument("--saida", type=Path, default=DEFAULT_OUTPUT)
    executar.add_argument("--limite", type=int, default=0, help="0 corre todos")
    executar.add_argument("--tentativas", type=int, default=3)
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

    return parser.parse_args(argv)


def comando_executar(args: argparse.Namespace) -> int:
    cases = read_cases(args.casos)
    if args.limite > 0:
        cases = cases[: args.limite]

    try:
        provider = build_provider(args.fornecedor, args.modelo)
    except ProviderError as error:
        print(f"erro: {error}", file=sys.stderr)
        return 2

    print(f"{len(cases)} casos, modelo {provider.name}")

    def progress(case, answer, status) -> None:
        mark = "." if status == "ok" else ("-" if status == "ja respondido" else "!")
        detail = f" {status}" if status not in ("ok",) else ""
        print(f"  {mark} {case.case_id}{detail}")

    result = run(
        cases,
        provider,
        path=None if args.recomecar else args.saida,
        config=RunConfig(attempts=args.tentativas),
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


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.comando == "executar":
        return comando_executar(args)
    if args.comando == "verificar":
        return comando_verificar(args)
    if args.comando == "classificar":
        return comando_classificar(args)
    return 2


__all__ = ["main", "build_provider", "parse_args"]
