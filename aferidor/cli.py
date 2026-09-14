"""Command line for running the bench.

    python -m aferidor executar --fornecedor falso
    python -m aferidor executar --fornecedor openai --modelo gpt-4o
    python -m aferidor executar --fornecedor anthropic --limite 3
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .providers import AnthropicProvider, FakeProvider, OpenAIProvider, Provider, ProviderError
from .runner import RunConfig, run
from .storage import read_cases

DEFAULT_CASES = Path("casos/casos.json")
DEFAULT_OUTPUT = Path("data/respostas.jsonl")


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


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.comando == "executar":
        return comando_executar(args)
    return 2


__all__ = ["main", "build_provider", "parse_args"]
