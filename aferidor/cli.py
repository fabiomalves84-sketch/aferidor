"""Command line for running the bench.

    python -m aferidor executar --fornecedor falso
    python -m aferidor executar --fornecedor openai --modelo gpt-4o
    python -m aferidor executar --fornecedor anthropic --limite 3
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from . import html_report, protocolo, report, revisao
from .grading import grade_all, self_check, tally_by_model, uncaught_controls
from .providers import (
    AnthropicProvider,
    FakeProvider,
    GeminiProvider,
    LocalProvider,
    OpenAIProvider,
    Provider,
    ProviderError,
)
from .runner import ConditionsMismatch, RunConfig, run
from .storage import read_answers, read_cases, write_answers, write_verdicts
from .traducao import LANGS

DEFAULT_CASES = Path("casos/casos.json")
DEFAULT_OUTPUT = Path("data/respostas.jsonl")
DEFAULT_VERDICTS = Path("data/vereditos.json")
DEFAULT_REPORT = Path("relatorios/relatorio.md")
DEFAULT_REPORT_HTML = Path("relatorios/relatorio.html")
DEFAULT_TOKENS_MAX = 4096


def build_provider(
    kind: str, model: str | None, temperature: float = 0.0, max_tokens: int | None = None
) -> Provider:
    if kind == "falso":
        return FakeProvider(name=f"falso:{model}" if model else "falso", temperature=temperature)
    kwargs: dict = {"temperature": temperature}
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    if kind == "openai":
        return OpenAIProvider(model=model, **kwargs) if model else OpenAIProvider(**kwargs)
    if kind == "anthropic":
        return AnthropicProvider(model=model, **kwargs) if model else AnthropicProvider(**kwargs)
    if kind == "local":
        return LocalProvider(model=model, **kwargs) if model else LocalProvider(**kwargs)
    if kind == "gemini":
        return GeminiProvider(model=model, **kwargs) if model else GeminiProvider(**kwargs)
    raise ValueError(f"fornecedor desconhecido {kind!r}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="aferidor", description="Banco de ensaio clínico")
    sub = parser.add_subparsers(dest="comando", required=True)

    executar = sub.add_parser("executar", help="enviar os casos a um modelo")
    executar.add_argument(
        "--fornecedor", choices=("falso", "openai", "anthropic", "gemini", "local"), default="falso"
    )
    executar.add_argument("--modelo", default=None, help="identificador do modelo")
    executar.add_argument("--casos", type=Path, default=DEFAULT_CASES)
    executar.add_argument("--saida", type=Path, default=DEFAULT_OUTPUT)
    executar.add_argument("--limite", type=int, default=0, help="0 executa todos")
    executar.add_argument("--tentativas", type=int, default=3)
    executar.add_argument(
        "--repeticoes", type=int, default=1, help="quantas vezes perguntar cada caso"
    )
    executar.add_argument(
        "--temperatura", type=float, default=0.0, help="temperatura pedida ao fornecedor"
    )
    executar.add_argument(
        "--tokens-max", type=int, default=DEFAULT_TOKENS_MAX,
        help="limite de tokens da resposta; um modelo que raciocina antes de responder precisa de mais",
    )
    executar.add_argument(
        "--recomecar",
        action="store_true",
        help="ignorar respostas anteriores deste modelo e perguntar tudo de novo",
    )

    verificar = sub.add_parser(
        "verificar", help="verificar se cada caso cumpre os próprios critérios"
    )
    verificar.add_argument("--casos", type=Path, default=DEFAULT_CASES)

    classificar = sub.add_parser("classificar", help="avaliar as respostas guardadas")
    classificar.add_argument("--casos", type=Path, default=DEFAULT_CASES)
    classificar.add_argument("--respostas", type=Path, default=DEFAULT_OUTPUT)
    classificar.add_argument("--saida", type=Path, default=DEFAULT_VERDICTS)
    classificar.add_argument(
        "--limite", type=int, default=0,
        help="0 usa todos os casos; tem de coincidir com o --limite usado em executar",
    )

    ensaio = sub.add_parser(
        "ensaio", help="executar, classificar e escrever o relatório numa só operação"
    )
    ensaio.add_argument(
        "--fornecedor", choices=("falso", "openai", "anthropic", "gemini", "local"), default="falso"
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
    ensaio.add_argument(
        "--tokens-max", type=int, default=DEFAULT_TOKENS_MAX,
        help="limite de tokens da resposta; um modelo que raciocina antes de responder precisa de mais",
    )
    ensaio.add_argument("--recomecar", action="store_true")
    ensaio.add_argument(
        "--protocolo", type=Path, default=None,
        help="protocolo com o critério de aprovação, escrito antes do ensaio",
    )
    ensaio.add_argument("--fontes-confirmadas", action="store_true")

    modelos = sub.add_parser(
        "modelos", help="listar os modelos disponíveis no fornecedor"
    )
    modelos.add_argument("--fornecedor", choices=("openai", "anthropic", "gemini", "local"), required=True)

    prot = sub.add_parser(
        "protocolo", help="escrever um protocolo com o critério de aprovação, antes do ensaio"
    )
    prot.add_argument("--nome", required=True)
    prot.add_argument("--casos", type=Path, default=DEFAULT_CASES)
    prot.add_argument("--saida", type=Path, required=True)

    rev = sub.add_parser(
        "revisao",
        help="exportar uma amostra de respostas para uma pessoa julgar, às cegas",
    )
    rev.add_argument("--casos", type=Path, default=DEFAULT_CASES)
    rev.add_argument("--respostas", type=Path, default=DEFAULT_OUTPUT)
    rev.add_argument("--n", type=int, default=60, help="quantas respostas (omissão 60)")
    rev.add_argument("--semente", type=int, default=1, help="a mesma semente dá a mesma amostra")
    rev.add_argument("--saida", type=Path, default=Path("relatorios/revisao.csv"))
    rev.add_argument(
        "--substituir", action="store_true",
        help="escrever por cima de uma folha que já existe (perde os juízos que lá estejam)",
    )

    conc = sub.add_parser(
        "concordancia", help="comparar os juízos de uma pessoa com os vereditos do corretor"
    )
    conc.add_argument("--revisao", type=Path, default=Path("relatorios/revisao.csv"))

    relatorio = sub.add_parser("relatorio", help="escrever o relatório")
    relatorio.add_argument("--casos", type=Path, default=DEFAULT_CASES)
    relatorio.add_argument("--respostas", type=Path, default=DEFAULT_OUTPUT)
    relatorio.add_argument("--saida", type=Path, default=None)
    relatorio.add_argument("--formato", choices=("md", "html"), default="md")
    relatorio.add_argument(
        "--linguas", default="pt",
        help="línguas da interface do relatório HTML, separadas por vírgulas (pt, en, es, fr, de); "
        "a primeira fica em --saida e cada outra num ficheiro ao lado, com um menu entre elas",
    )
    relatorio.add_argument(
        "--limite", type=int, default=0,
        help="0 usa todos os casos; tem de coincidir com o --limite usado em executar",
    )
    relatorio.add_argument(
        "--protocolo", type=Path, default=None,
        help="protocolo com o critério de aprovação, escrito antes do ensaio",
    )
    relatorio.add_argument(
        "--fontes-confirmadas",
        action="store_true",
        help="omitir o aviso de fontes por confirmar (apenas depois de confirmadas)",
    )

    return parser.parse_args(argv)


def comando_executar(
    args: argparse.Namespace, errors_out: dict[str, str] | None = None
) -> int:
    cases = read_cases(args.casos)
    if args.limite > 0:
        cases = cases[: args.limite]

    try:
        provider = build_provider(
            args.fornecedor, args.modelo, temperature=args.temperatura,
            max_tokens=getattr(args, "tokens_max", DEFAULT_TOKENS_MAX),
        )
    except ProviderError as error:
        print(f"erro: {error}", file=sys.stderr)
        return 2

    if args.recomecar and args.saida.exists():
        existing = read_answers(args.saida)
        kept = [a for a in existing if a.model != provider.name]
        discarded = len(existing) - len(kept)
        write_answers(kept, args.saida)
        if discarded:
            print(f"--recomecar: descartadas {discarded} respostas anteriores de {provider.name}")

    print(f"{len(cases)} casos x {args.repeticoes} amostra(s), modelo {provider.name}")

    def progress(case, answer, status) -> None:
        mark = "." if status == "ok" else ("-" if status == "já respondido" else "!")
        detail = f" {status}" if status not in ("ok",) else ""
        print(f"  {mark} {case.case_id}{detail}")

    try:
        result = run(
            cases,
            provider,
            path=args.saida,
            config=RunConfig(attempts=args.tentativas),
            repetitions=args.repeticoes,
            progress=progress,
        )
    except ConditionsMismatch as error:
        print(f"erro: {error}", file=sys.stderr)
        print(
            "para continuar esta medição, usar as mesmas condições; para iniciar outra,"
            " usar --recomecar ou outro --saida",
            file=sys.stderr,
        )
        return 2

    print(result.summary())
    print(f"respostas em {args.saida}")
    for case_id, message in result.errors.items():
        print(f"  por responder {case_id}: {message}", file=sys.stderr)
    if errors_out is not None:
        errors_out.update(result.errors)
    return 0 if result.complete else 1


def comando_classificar(args: argparse.Namespace) -> int:
    cases = read_cases(args.casos)
    if getattr(args, "limite", 0) > 0:
        cases = cases[: args.limite]
    if not args.respostas.exists():
        print(f"erro: não há respostas em {args.respostas}", file=sys.stderr)
        return 2

    answers = read_answers(args.respostas)
    try:
        verdicts, missing = grade_all(cases, answers)
    except ValueError as error:
        print(f"erro: {error}", file=sys.stderr)
        return 2

    args.saida.parent.mkdir(parents=True, exist_ok=True)
    write_verdicts(verdicts, args.saida)

    for model, counts in tally_by_model(verdicts).items():
        print(f"\n{model}")
        print(f"  {counts.passed}/{counts.total} corretas ({counts.accuracy:.0%})")
        if counts.critical:
            print(f"  {counts.critical} respostas com falha de risco crítico")
        for failure, number in counts.worst_first():
            print(f"    {failure.value:<26} {number:>3}  risco {failure.risk}")
        for case_id, failures in sorted(counts.failed_cases.items()):
            print(f"    {case_id}: {', '.join(failures)}")

    if missing:
        print(f"\ncasos sem resposta válida: {', '.join(sorted(set(missing)))}", file=sys.stderr)
    print(f"\nvereditos em {args.saida}")
    return 0


def comando_verificar(args: argparse.Namespace) -> int:
    cases = read_cases(args.casos)
    broken = self_check(cases)

    print(f"{len(cases) - len(broken)}/{len(cases)} casos coerentes")
    for case, verdict in broken:
        print(f"\n{case.case_id}: a própria referência não passa", file=sys.stderr)
        print(f"  referência: {case.reference}", file=sys.stderr)
        for result in verdict.results:
            if not result.passed:
                print(
                    f"  critério {result.criterion.kind} {list(result.criterion.terms)}"
                    f" -> {result.evidence}",
                    file=sys.stderr,
                )

    total, uncaught = uncaught_controls(cases)
    print(f"{total - len(uncaught)}/{total} controlos negativos apanhados")
    for control, verdict in uncaught:
        print(
            f"\n{control.case_id}: o critério {control.criterion.kind}"
            f" {list(control.criterion.terms)} não deteta uma resposta errada"
            f" ({control.change})",
            file=sys.stderr,
        )
        if verdict is not None:
            found = ", ".join(f.value for f in verdict.failures) or "nenhuma falha"
            print(f"  o veredito deu: {found}", file=sys.stderr)
    return 1 if broken or uncaught else 0


def _protocol_problem(args: argparse.Namespace) -> str | None:
    """Why this protocol cannot judge this run, printed; None when it can.

    A protocol judges the whole bank. With --limite only part of it is asked,
    and every limit would be met on a handful of cases.
    """
    problem = None
    try:
        protocolo.read_protocol(args.protocolo)
    except (OSError, ValueError) as error:
        problem = str(error)
    if problem is None and getattr(args, "limite", 0) > 0:
        problem = "um protocolo avalia o banco inteiro; não é compatível com --limite"
    if problem is not None:
        print(f"erro: {problem}", file=sys.stderr)
    return problem


def comando_relatorio(
    args: argparse.Namespace, reasons: dict[str, str] | None = None
) -> int:
    cases = read_cases(args.casos)
    if getattr(args, "limite", 0) > 0:
        cases = cases[: args.limite]
    if not args.respostas.exists():
        print(f"erro: não há respostas em {args.respostas}", file=sys.stderr)
        return 2

    answers = read_answers(args.respostas)
    try:
        verdicts, missing = grade_all(cases, answers)
    except ValueError as error:
        print(f"erro: {error}", file=sys.stderr)
        return 2
    formato = getattr(args, "formato", "md")

    saida = args.saida
    if saida is None:
        saida = DEFAULT_REPORT_HTML if formato == "html" else DEFAULT_REPORT

    protocol = None
    if getattr(args, "protocolo", None) is not None:
        if _protocol_problem(args) is not None:
            return 2
        protocol = protocolo.read_protocol(args.protocolo)
    langs = [x.strip() for x in getattr(args, "linguas", "pt").split(",") if x.strip()]
    unknown = [x for x in langs if x not in LANGS]
    if unknown or not langs:
        print(f"erro: língua desconhecida {', '.join(unknown)}; usar {', '.join(LANGS)}", file=sys.stderr)
        return 2
    if formato != "html" and langs != ["pt"]:
        print("erro: --linguas só se aplica ao formato html", file=sys.stderr)
        return 2
    common = dict(
        missing=missing, reasons=reasons, sources_verified=args.fontes_confirmadas,
        cases_source=_cases_source(args.casos), protocol=protocol,
    )
    saida.parent.mkdir(parents=True, exist_ok=True)
    if formato != "html":
        text = report.build(cases, answers, verdicts, **common)
        saida.write_text(text, encoding="utf-8")
        print(f"relatório em {saida} ({len(text.splitlines())} linhas)")
        return 0
    paths = {
        lang: saida if i == 0 else saida.with_name(f"{saida.stem}.{lang}{saida.suffix}")
        for i, lang in enumerate(langs)
    }
    alternates = {lang: path.name for lang, path in paths.items()} if len(langs) > 1 else None
    for lang, path in paths.items():
        text = html_report.build(
            cases, answers, verdicts, lingua=lang, alternates=alternates, **common
        )
        path.write_text(text, encoding="utf-8")
        print(f"relatório em {path} ({len(text.splitlines())} linhas)")
    return 0


def _cases_source(path: Path) -> tuple[str, str]:
    """The case file as the report names it: path, version when it has one, SHA-256."""
    raw = path.read_bytes()
    label = str(path)
    try:
        version = json.loads(raw).get("versao")
    except (AttributeError, ValueError):
        version = None
    if version:
        label += f", versão {version}"
    return label, hashlib.sha256(raw).hexdigest()


def comando_protocolo(args: argparse.Namespace) -> int:
    if args.saida.exists():
        print(f"erro: {args.saida} já existe; um protocolo não se reescreve depois de escrito",
              file=sys.stderr)
        return 2
    data = protocolo.template(args.nome, args.casos)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"protocolo em {args.saida}, para {args.casos} (SHA-256 {data['banco_sha256'][:12]})")
    print("rever os limites em criterios_de_aprovacao e fazer commit antes de correr o ensaio:")
    print("é o commit, e não a data escrita no ficheiro, que prova que o critério veio antes")
    return 0


def comando_revisao(args: argparse.Namespace) -> int:
    key = revisao.key_path_for(args.saida)
    if (args.saida.exists() or key.exists()) and not args.substituir:
        print(
            f"erro: {args.saida} já existe e pode ter juízos de uma pessoa; "
            "escolhe outro --saida, ou usa --substituir se quiseres mesmo apagá-la",
            file=sys.stderr,
        )
        return 2
    if not args.respostas.exists():
        print(f"erro: não há respostas em {args.respostas}", file=sys.stderr)
        return 2
    cases = read_cases(args.casos)
    answers = read_answers(args.respostas)
    try:
        verdicts, _ = grade_all(cases, answers)
        items = revisao.sample_for_review(cases, answers, verdicts, args.n, args.semente)
    except ValueError as error:
        print(f"erro: {error}", file=sys.stderr)
        return 2
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    revisao.write_review(items, args.saida, key, args.respostas)
    unknown = sorted({
        item.case.case_id for item in items
        if revisao.asked_the_same_question(item.case, item.answer) is None
    })
    if unknown:
        print(
            "aviso: estas respostas não guardaram o texto que lhes foi enviado, por isso não se "
            "sabe se a pergunta na folha é a que o modelo viu. Se algum destes casos mudou "
            f"depois do ensaio, deve ser retirado da revisão: {', '.join(unknown)}",
            file=sys.stderr,
        )
    passed = sum(1 for item in items if item.grader_passed)
    print(f"{len(items)} respostas para julgar em {args.saida} ({passed} que o corretor passou, "
          f"{len(items) - passed} que chumbou; a folha não diz quais)")
    print(f"chave em {key}; não deve ser mostrada a quem julga")
    print("na coluna 'juizo', escrever 'certa' ou 'errada'; depois, correr: "
          f"python3 -m aferidor concordancia --revisao {args.saida}")
    return 0


def comando_concordancia(args: argparse.Namespace) -> int:
    key = revisao.key_path_for(args.revisao)
    if not args.revisao.exists() or not key.exists():
        print(f"erro: falta {args.revisao} ou a sua chave {key}", file=sys.stderr)
        return 2
    try:
        result = revisao.read_review(args.revisao, key)
    except ValueError as error:
        print(f"erro: {error}", file=sys.stderr)
        return 2
    print(revisao.format_agreement(result))
    return 0 if result.judged else 1


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

    A verificacao dos casos corre primeiro e de proposito, nos dois sentidos: a
    resposta certa passa, e uma resposta errada construida para cada criterio
    falha. Perguntar a um modelo custa dinheiro; descobrir depois que um caso
    estava partido custa o dinheiro outra vez.
    """
    # The protocol is read before anything is asked: a wrong path or a broken
    # file found only at the report would already have paid for the run.
    if getattr(args, "protocolo", None) is not None:
        if _protocol_problem(args) is not None:
            return 2
    cases = read_cases(args.casos)
    broken = self_check(cases)
    _, uncaught = uncaught_controls(cases)
    if broken or uncaught:
        for case, _ in broken:
            print(f"erro: {case.case_id} não passa nos próprios critérios", file=sys.stderr)
        for control, _ in uncaught:
            print(
                f"erro: {control.case_id} tem um critério {control.criterion.kind}"
                f" que não deteta uma resposta errada ({control.change})",
                file=sys.stderr,
            )
        print("corrigir os casos antes de gastar uma execução", file=sys.stderr)
        return 2

    executar_args = argparse.Namespace(
        fornecedor=args.fornecedor, modelo=args.modelo, casos=args.casos,
        saida=args.saida, limite=args.limite, tentativas=args.tentativas,
        repeticoes=args.repeticoes, temperatura=args.temperatura,
        tokens_max=args.tokens_max, recomecar=args.recomecar,
    )
    errors: dict[str, str] = {}
    codigo = comando_executar(executar_args, errors_out=errors)
    if codigo == 2:
        return codigo

    classificar_args = argparse.Namespace(
        casos=args.casos, respostas=args.saida, saida=args.vereditos, limite=args.limite
    )
    codigo_classificar = comando_classificar(classificar_args)
    if codigo_classificar != 0:
        return codigo_classificar

    relatorio_args = argparse.Namespace(
        casos=args.casos, respostas=args.saida, saida=args.relatorio,
        fontes_confirmadas=args.fontes_confirmadas, limite=args.limite,
        protocolo=getattr(args, "protocolo", None),
    )
    codigo_relatorio = comando_relatorio(relatorio_args, reasons=errors)
    if codigo_relatorio != 0:
        return codigo_relatorio

    if codigo == 1:
        print(
            "\naviso: houve casos sem resposta; o relatório identifica-os e não os conta",
            file=sys.stderr,
        )
        return 1
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
    if args.comando == "protocolo":
        return comando_protocolo(args)
    if args.comando == "revisao":
        return comando_revisao(args)
    if args.comando == "concordancia":
        return comando_concordancia(args)
    return 2


__all__ = ["main", "build_provider", "parse_args"]
