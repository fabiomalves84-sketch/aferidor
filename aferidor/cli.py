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

from . import build_id, fontes, html_report, manifesto, protocolo, report, revisao
from .grading import (
    grade_all,
    met_by_the_question,
    self_check,
    tally_by_model,
    uncaught_controls,
    verdict_changes,
)
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
    prot.add_argument(
        "--congelar-corretor", action="store_true",
        help="fixar no protocolo a versão atual do corretor; o relatório assinala qualquer outra",
    )

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
        "concordancia", help="comparar os juízos de uma pessoa com os veredictos do corretor"
    )
    conc.add_argument("--revisao", type=Path, default=Path("relatorios/revisao.csv"))

    comparar = sub.add_parser(
        "comparar-vereditos",
        help="mostrar que veredictos de um ensaio mudam com os critérios e o corretor atuais",
    )
    comparar.add_argument("--casos", type=Path, default=DEFAULT_CASES)
    comparar.add_argument("--respostas", type=Path, required=True)
    comparar.add_argument("--vereditos", type=Path, required=True, help="vereditos.json gravado antes")

    manifesto = sub.add_parser(
        "manifesto", help="escrever ou verificar o SHA-256 de cada ficheiro de um ensaio registado"
    )
    manifesto.add_argument("pasta", type=Path, help="pasta do ensaio, por exemplo ensaios/2026-09-28-gemini-flash")
    manifesto.add_argument("--verificar", action="store_true", help="comparar a pasta com o manifesto existente")

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


def comando_executar(args: argparse.Namespace) -> int:
    return _executar(
        args.casos, args.fornecedor, args.modelo, args.saida, args.limite, args.tentativas,
        args.repeticoes, args.temperatura, args.tokens_max, args.recomecar,
    )


def _executar(
    casos: Path, fornecedor: str, modelo: str | None, saida: Path, limite: int, tentativas: int,
    repeticoes: int, temperatura: float, tokens_max: int, recomecar: bool,
    errors_out: dict[str, str] | None = None,
) -> int:
    cases = read_cases(casos)
    if limite > 0:
        cases = cases[:limite]

    try:
        provider = build_provider(fornecedor, modelo, temperature=temperatura, max_tokens=tokens_max)
    except ProviderError as error:
        print(f"erro: {error}", file=sys.stderr)
        return 2

    if recomecar and saida.exists():
        existing = read_answers(saida)
        kept = [a for a in existing if a.model != provider.name]
        discarded = len(existing) - len(kept)
        write_answers(kept, saida)
        if discarded:
            print(f"--recomecar: descartadas {discarded} respostas anteriores de {provider.name}")

    print(f"{len(cases)} casos x {repeticoes} amostra(s), modelo {provider.name}")

    def progress(case, answer, status) -> None:
        mark = "." if status == "ok" else ("-" if status == "já respondido" else "!")
        detail = f" {status}" if status not in ("ok",) else ""
        print(f"  {mark} {case.case_id}{detail}")

    try:
        result = run(
            cases,
            provider,
            path=saida,
            config=RunConfig(attempts=tentativas),
            repetitions=repeticoes,
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

    for note in result.notes:
        print(f"aviso: {note}", file=sys.stderr)
    print(result.summary())
    print(f"respostas em {saida}")
    for case_id, message in result.errors.items():
        print(f"  por responder {case_id}: {message}", file=sys.stderr)
    if errors_out is not None:
        errors_out.update(result.errors)
    return 0 if result.complete else 1


def comando_classificar(args: argparse.Namespace) -> int:
    return _classificar(args.casos, args.respostas, args.saida, args.limite)


def _classificar(casos: Path, respostas: Path, saida: Path, limite: int) -> int:
    cases = read_cases(casos)
    if limite > 0:
        cases = cases[:limite]
    if not respostas.exists():
        print(f"erro: não há respostas em {respostas}", file=sys.stderr)
        return 2

    answers = read_answers(respostas)
    try:
        verdicts, missing = grade_all(cases, answers)
    except ValueError as error:
        print(f"erro: {error}", file=sys.stderr)
        return 2

    saida.parent.mkdir(parents=True, exist_ok=True)
    write_verdicts(verdicts, saida)

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
    print(f"\nveredictos em {saida}")
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
            print(f"  o veredicto deu: {found}", file=sys.stderr)

    echoes = met_by_the_question(cases)
    if echoes:
        print(
            f"aviso: {len(echoes)} critérios cumprem-se só com o texto da pergunta "
            "(não distinguem uma resposta de uma repetição da pergunta):",
            file=sys.stderr,
        )
        for case, criterion in echoes:
            print(f"  {case.case_id}: {criterion.kind} {list(criterion.terms)}", file=sys.stderr)
    return 1 if broken or uncaught else 0


def comando_comparar(args: argparse.Namespace) -> int:
    """Measure what a change to the grader did, answer by answer, before committing it."""
    cases = read_cases(args.casos)
    answers = read_answers(args.respostas)
    verdicts, _ = grade_all(cases, answers)
    saved = json.loads(args.vereditos.read_text(encoding="utf-8"))
    changes = verdict_changes(saved, cases, answers, verdicts)
    worse = [c for c in changes if c.passed_before and not c.passed_now]
    better = [c for c in changes if not c.passed_before and c.passed_now]
    other = [c for c in changes if c.passed_before == c.passed_now]
    print(
        f"{len(changes)} de {len(saved)} veredictos mudam: {len(better)} passam a passar, "
        f"{len(worse)} passam a falhar, {len(other)} mudam só o tipo de falha"
    )
    for c in changes:
        before = "passava" if c.passed_before else ", ".join(c.failures_before)
        now = "passa" if c.passed_now else ", ".join(c.failures_now)
        print(f"  {c.case_id} {c.model} amostra {c.sample}: {before} -> {now}")
    return 0


def comando_manifesto(args: argparse.Namespace) -> int:
    folder = args.pasta
    if not folder.is_dir():
        print(f"erro: {folder} não é uma pasta", file=sys.stderr)
        return 2
    if not args.verificar:
        target = manifesto.write_manifest(folder)
        count = len(target.read_text(encoding="utf-8").splitlines())
        print(f"manifesto em {target} ({count} ficheiros); verificável com: shasum -a 256 -c {manifesto.MANIFEST}")
        return 0
    if not (folder / manifesto.MANIFEST).exists():
        print(f"erro: {folder} não tem {manifesto.MANIFEST}", file=sys.stderr)
        return 2
    result = manifesto.check_manifest(folder)
    for label, names in (("alterado", result.changed), ("em falta", result.missing), ("fora do manifesto", result.unlisted)):
        for name in names:
            print(f"  {label}: {name}", file=sys.stderr)
    print(f"{folder}: {'íntegra' if result.intact else 'difere do manifesto'}")
    return 0 if result.intact else 1


def _protocol_problem(path: Path, limite: int) -> str | None:
    """Why this protocol cannot judge this run, printed; None when it can.

    A protocol judges the whole bank. With --limite only part of it is asked,
    and every limit would be met on a handful of cases.
    """
    problem = None
    try:
        protocolo.read_protocol(path)
    except (OSError, ValueError) as error:
        problem = str(error)
    if problem is None and limite > 0:
        problem = "um protocolo avalia o banco inteiro; não é compatível com --limite"
    if problem is not None:
        print(f"erro: {problem}", file=sys.stderr)
    return problem


def _protocol_mismatches(path: Path, repeticoes: int, temperatura: float, casos: Path) -> list[str]:
    """Where this run would not be the one the protocol was written for.

    The report flags every one of these afterwards, but by then the run is
    paid for. A protocol that froze the grader also refuses any other build.
    """
    protocol = protocolo.read_protocol(path)
    found = []
    if repeticoes != protocol.samples:
        found.append(
            f"--repeticoes {repeticoes}, mas o protocolo prevê {protocol.samples} amostras por caso"
        )
    if temperatura != protocol.temperature:
        found.append(
            f"--temperatura {temperatura:g}, mas o protocolo prevê {protocol.temperature:g}"
        )
    if hashlib.sha256(Path(casos).read_bytes()).hexdigest() != protocol.cases_sha256:
        found.append("o banco de casos não é o banco para que o protocolo foi escrito (SHA-256 diferente)")
    if protocol.grader_build and protocol.grader_build != build_id():
        found.append(
            f"o protocolo fixou o corretor na versão {protocol.grader_build}, "
            f"mas esta é a {build_id()}"
        )
    return found


def comando_relatorio(args: argparse.Namespace) -> int:
    return _relatorio(
        args.casos, args.respostas, args.saida, args.formato, args.linguas, args.limite,
        args.protocolo, args.fontes_confirmadas,
    )


def _relatorio(
    casos: Path, respostas: Path, saida: Path | None, formato: str, linguas: str, limite: int,
    protocolo_path: Path | None, fontes_confirmadas: bool, reasons: dict[str, str] | None = None,
) -> int:
    cases = read_cases(casos)
    if limite > 0:
        cases = cases[:limite]
    if not respostas.exists():
        print(f"erro: não há respostas em {respostas}", file=sys.stderr)
        return 2

    answers = read_answers(respostas)
    try:
        verdicts, missing = grade_all(cases, answers)
    except ValueError as error:
        print(f"erro: {error}", file=sys.stderr)
        return 2

    if saida is None:
        saida = DEFAULT_REPORT_HTML if formato == "html" else DEFAULT_REPORT

    protocol = None
    if protocolo_path is not None:
        if _protocol_problem(protocolo_path, limite) is not None:
            return 2
        protocol = protocolo.read_protocol(protocolo_path)
    langs = [x.strip() for x in linguas.split(",") if x.strip()]
    unknown = [x for x in langs if x not in LANGS]
    if unknown or not langs:
        print(f"erro: língua desconhecida {', '.join(unknown)}; usar {', '.join(LANGS)}", file=sys.stderr)
        return 2
    if formato != "html" and langs != ["pt"]:
        print("erro: --linguas só se aplica ao formato html", file=sys.stderr)
        return 2
    common = dict(
        missing=missing, reasons=reasons, sources_verified=fontes_confirmadas,
        cases_source=_cases_source(casos), protocol=protocol,
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
            cases, answers, verdicts, lingua=lang, alternates=alternates,
            confirmation=fontes.read_confirmation(casos, [c.case_id for c in cases]), **common
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
    data = protocolo.template(args.nome, args.casos, freeze_grader=args.congelar_corretor)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"protocolo em {args.saida}, para {args.casos} (SHA-256 {data['banco_sha256'][:12]})")
    if "versao_corretor" in data:
        print(f"corretor fixado na versão {data['versao_corretor']}")
    print("rever os limites em criterios_de_aprovacao e fazer commit antes de correr o ensaio:")
    print("é o commit, e não a data escrita no ficheiro, que prova que o critério veio antes")
    return 0


def comando_revisao(args: argparse.Namespace) -> int:
    key = revisao.key_path_for(args.saida)
    if (args.saida.exists() or key.exists()) and not args.substituir:
        print(
            f"erro: {args.saida} já existe e pode ter juízos de uma pessoa; "
            "escolher outro --saida, ou usar --substituir para a apagar",
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
    """The three steps in one go, stopping at the first that fails.

    The cases are checked first, on purpose, in both directions: the right
    answer passes, and a wrong answer built for each criterion fails. Asking
    a model costs money; finding a broken case afterwards costs it again.
    """
    # The protocol is read before anything is asked: a wrong path or a broken
    # file found only at the report would already have paid for the run.
    if args.protocolo is not None:
        if _protocol_problem(args.protocolo, args.limite) is not None:
            return 2
        mismatches = _protocol_mismatches(args.protocolo, args.repeticoes, args.temperatura, args.casos)
        for mismatch in mismatches:
            print(f"erro: {mismatch}", file=sys.stderr)
        if mismatches:
            print("corrigir antes de gastar uma execução; o relatório assinalaria o mesmo", file=sys.stderr)
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

    errors: dict[str, str] = {}
    codigo = _executar(
        args.casos, args.fornecedor, args.modelo, args.saida, args.limite, args.tentativas,
        args.repeticoes, args.temperatura, args.tokens_max, args.recomecar, errors_out=errors,
    )
    if codigo == 2:
        return codigo

    codigo_classificar = _classificar(args.casos, args.saida, args.vereditos, args.limite)
    if codigo_classificar != 0:
        return codigo_classificar

    codigo_relatorio = _relatorio(
        args.casos, args.saida, args.relatorio, "md", "pt", args.limite,
        args.protocolo, args.fontes_confirmadas, reasons=errors,
    )
    if codigo_relatorio != 0:
        return codigo_relatorio

    if codigo == 1:
        print(
            "\naviso: houve casos sem resposta; o relatório identifica-os e não os conta",
            file=sys.stderr,
        )
        return 1
    return 0


_COMMANDS = {
    "executar": lambda a: comando_executar(a),
    "verificar": lambda a: comando_verificar(a),
    "classificar": lambda a: comando_classificar(a),
    "relatorio": lambda a: comando_relatorio(a),
    "ensaio": lambda a: comando_ensaio(a),
    "modelos": lambda a: comando_modelos(a),
    "protocolo": lambda a: comando_protocolo(a),
    "revisao": lambda a: comando_revisao(a),
    "concordancia": lambda a: comando_concordancia(a),
    "manifesto": lambda a: comando_manifesto(a),
    "comparar-vereditos": lambda a: comando_comparar(a),
}


def main(argv: list[str] | None = None) -> int:
    """Run one command; a missing or malformed file ends in a message, not a traceback."""
    args = parse_args(list(sys.argv[1:] if argv is None else argv))
    command = _COMMANDS.get(args.comando)
    if command is None:
        return 2
    try:
        return command(args)
    except json.JSONDecodeError as error:
        print(f"erro: ficheiro JSON inválido, linha {error.lineno}, coluna {error.colno}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as error:
        print(f"erro: {error}", file=sys.stderr)
        return 2

__all__ = ["main", "build_provider", "parse_args"]
