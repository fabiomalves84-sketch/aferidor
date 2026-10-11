"""Command line for running the bench.

    python -m aferidor executar --fornecedor falso
    python -m aferidor executar --fornecedor openai --modelo gpt-4o
    python -m aferidor executar --fornecedor anthropic --limite 3
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from . import build_id, fontes, grader_id, html_report, manifesto, protocolo, report, revisao
from .catalogo import Catalog, Model, load_catalog
from .custos import Ledger, estimate, format_estimate
from .grading import (
    grade_all,
    met_by_the_question,
    self_check,
    tally_by_model,
    uncaught_controls,
    verdict_changes,
)
from .models import Answer, Case
from .providers import (
    AnthropicProvider,
    FakeProvider,
    GeminiProvider,
    GoogleProvider,
    LocalProvider,
    OpenAICompatible,
    OpenAIProvider,
    Provider,
    ProviderError,
)
from .pago import PaidCalls
from .proveniencia import provenance_path
from .runner import ConditionsMismatch, RunConfig, build_prompt, run
from .storage import read_answers, read_cases, write_answers, write_verdicts
from .traducao import LANGS

DEFAULT_CASES = Path("casos/casos.json")
DEFAULT_OUTPUT = Path("data/respostas.jsonl")
DEFAULT_VERDICTS = Path("data/vereditos.json")
DEFAULT_REPORT = Path("relatorios/relatorio.md")
DEFAULT_REPORT_HTML = Path("relatorios/relatorio.html")
DEFAULT_TOKENS_MAX = 4096
# The cases the pilot run asks, in order. A tuple is a set of alternatives: the first one the bank has is used.
PILOT_CASES = (("ATB-PAC-001",), ("PED-OMA-021", "ATB-FAR-004"), ("GRA-VPA-024",))
PILOT_SAMPLES = 2
PILOT_FOLDER = "piloto"
STOPPED = 3  # exit code of a run that stopped on purpose (ceiling, or another model served the call)
# The provider of the catalogue that each `--fornecedor` means, and the classes whose default model a bare
# `--fornecedor` stands for. `gemini` is the OpenAI-compatible endpoint the earlier trials used, as it always was;
# `google` is Google's own API, which reports the thinking tokens and the model version.
_CATALOG_PROVIDER = {
    "openai": "openai", "anthropic": "anthropic", "gemini": "gemini", "google": "gemini",
    "local-compativel": "openai_compativel",
}
_DEFAULT_MODEL_CLASSES = {"openai": OpenAIProvider, "anthropic": AnthropicProvider, "gemini": GeminiProvider}
PROVIDER_CHOICES = ("falso", "openai", "anthropic", "gemini", "google", "local", "local-compativel")
# The program does not check when a protocol was written, so the text does not claim it was early.
PROTOCOL_HELP = (
    "protocolo com o critério de aprovação, que deve ser escrito antes do ensaio; "
    "um protocolo avalia o banco inteiro, por isso não se combina com --limite"
)


def build_provider(
    kind: str, model: str | None, temperature: float = 0.0, max_tokens: int | None = None,
    timeout: float | None = None, entry: Model | None = None, base_url: str | None = None,
) -> Provider:
    """The provider for a `--fornecedor`; for a model the catalogue lists, `entry` says how to ask it.

    From `entry` come the id to request, the variable the key is read from, whether the temperature is sent, and
    (through `timeout`) the time limit. A model that does not take a temperature runs at its own, and asking for
    another is refused here, before anything is paid for, rather than sent to be answered with a 400.
    """
    if kind == "falso":
        return FakeProvider(name=f"falso:{model}" if model else "falso", temperature=temperature)
    kwargs: dict = {"temperature": temperature}
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    if timeout is not None:
        kwargs["timeout"] = timeout
    if entry is not None:
        model = entry.requested_id
        if entry.key_variable and kind in ("openai", "anthropic", "gemini", "google"):
            kwargs["key_variable"] = entry.key_variable
        if kind in ("openai", "anthropic", "google", "local-compativel"):
            kwargs["send_temperature"] = entry.temperature not in ("fixa_pelo_fornecedor", "nao_aceita")
        if entry.temperature == "fixa_pelo_fornecedor" and Decimal(str(temperature)) != entry.fixed_temperature:
            raise ProviderError(
                f"{entry.requested_id} não aceita temperatura e corre sempre a {entry.fixed_temperature}; foi pedida "
                f"{temperature}. Pedir --temperatura {entry.fixed_temperature}, que é o que o catálogo diz que se aplica"
            )
    if kind == "openai":
        return OpenAIProvider(model=model, **kwargs) if model else OpenAIProvider(**kwargs)
    if kind == "anthropic":
        return AnthropicProvider(model=model, **kwargs) if model else AnthropicProvider(**kwargs)
    if kind == "local":
        return LocalProvider(model=model, **kwargs) if model else LocalProvider(**kwargs)
    if kind == "gemini":
        return GeminiProvider(model=model, **kwargs) if model else GeminiProvider(**kwargs)
    if kind == "google":
        if not model:
            raise ProviderError("--fornecedor google precisa de --modelo, o id do modelo do catálogo")
        return GoogleProvider(model=model, **kwargs)
    if kind == "local-compativel":
        if not model:
            raise ProviderError("--fornecedor local-compativel precisa de --modelo")
        url = base_url or (entry.base_url if entry else None)
        if not url:
            raise ProviderError("--fornecedor local-compativel precisa de --base-url, o endereço do servidor, por exemplo http://localhost:8000/v1")
        tokens_param = entry.token_field if entry and entry.token_field in ("max_tokens", "max_completion_tokens") else "max_tokens"
        return OpenAICompatible(model=model, base_url=url, tokens_param=tokens_param, **kwargs)
    raise ValueError(f"fornecedor desconhecido {kind!r}")


def _euros(text: str) -> Decimal:
    try:
        amount = Decimal(text.replace(",", "."))
    except InvalidOperation:
        amount = Decimal(0)
    if not amount.is_finite() or amount <= 0:
        raise argparse.ArgumentTypeError("--teto-eur tem de ser um valor em euros maior que zero, por exemplo 25 ou 12,5")
    return amount


def _paid_model(kind: str, model: str | None) -> tuple[Catalog, Model] | None:
    """The catalogue entry of a model the catalogue lists, or None for one it does not list.

    A listed model goes through the ledger and the provenance. Without `--modelo` the id is the provider's own
    default, so a bare `--fornecedor gemini` is the catalogue's Gemini model. `--modelo` may be the id or the key.
    """
    provider = _CATALOG_PROVIDER.get(kind)
    if provider is None:
        return None
    catalog = load_catalog()
    default = _DEFAULT_MODEL_CLASSES.get(kind)
    wanted = model or (inspect.signature(default.__init__).parameters["model"].default if default else None)
    found = catalog.resolve(provider, wanted) if wanted else None
    return (catalog, found) if found else None


def _pilot_cases(cases: list[Case]) -> tuple[list[Case], list[str]]:
    """The pilot's cases and a line saying which were chosen and which alternatives the bank did not have."""
    by_id = {c.case_id: c for c in cases}
    chosen: list[Case] = []
    said: list[str] = []
    for options in PILOT_CASES:
        present = [o for o in options if o in by_id]
        if present:
            chosen.append(by_id[present[0]])
            absent = [o for o in options if o not in by_id]
            said.append(present[0] + (f" (e não {', '.join(absent)}, que o banco não tem)" if absent else ""))
        else:
            said.append(f"nenhum de {' ou '.join(options)} existe neste banco")
    return chosen, said


def parse_args(argv: list[str]) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aferidor", description="Banco de ensaio clínico")
    sub = parser.add_subparsers(dest="comando", required=True)

    # The options `executar` and `ensaio` share, in this order.
    run_options = argparse.ArgumentParser(add_help=False)
    run_options.add_argument("--fornecedor", choices=PROVIDER_CHOICES, default="falso")
    run_options.add_argument("--modelo", default=None, help="identificador do modelo (ou a chave dele no catálogo)")
    run_options.add_argument(
        "--base-url", default=None,
        help="endereço de um servidor compatível com a API da OpenAI, só com --fornecedor local-compativel, "
             "por exemplo http://localhost:8000/v1",
    )
    run_options.add_argument("--casos", type=Path, default=DEFAULT_CASES)
    run_options.add_argument("--saida", type=Path, default=DEFAULT_OUTPUT)
    run_options.add_argument(
        "--limite", type=int, default=0, help="usar só os primeiros N casos; 0 usa todos"
    )
    run_options.add_argument("--tentativas", type=int, default=3)
    run_options.add_argument(
        "--repeticoes", type=int, default=1, help="quantas vezes perguntar cada caso"
    )
    run_options.add_argument(
        "--temperatura", type=float, default=0.0, help="temperatura pedida ao fornecedor"
    )
    run_options.add_argument(
        "--tokens-max", type=int, default=DEFAULT_TOKENS_MAX,
        help="limite de tokens da resposta; um modelo que raciocina antes de responder precisa de mais",
    )
    run_options.add_argument(
        "--teto-eur", type=_euros, default=None, metavar="EUROS",
        help="gasto máximo do ensaio em euros, somando todos os modelos; obrigatório para um modelo pago, "
             "sem valor por omissão",
    )
    run_options.add_argument(
        "--a-seco", action="store_true",
        help="estimar o custo e sair, sem chamar nenhum fornecedor nem escrever nada",
    )
    run_options.add_argument(
        "--piloto", action="store_true",
        help=f"só 3 casos ({', '.join('/'.join(o) for o in PILOT_CASES)}), {PILOT_SAMPLES} amostras cada, "
             f"gravados à parte, numa subpasta '{PILOT_FOLDER}' ao lado de --saida",
    )
    run_options.add_argument(
        "--repetir-incertas", action="store_true",
        help="num modelo pago, pedir de novo as amostras sem resposta guardada cujo resultado ficou incerto "
             "(tempo limite, ou reservadas e nunca liquidadas); cada repetição custa de novo e as duas contam no teto",
    )
    run_options.add_argument(
        "--recomecar",
        action="store_true",
        help="ignorar respostas anteriores deste modelo e perguntar tudo de novo",
    )

    sub.add_parser("executar", help="enviar os casos a um modelo", parents=[run_options])

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
        "ensaio", help="executar, classificar e escrever o relatório numa só operação",
        parents=[run_options],
    )
    ensaio.add_argument(
        "--vereditos", type=Path, default=DEFAULT_VERDICTS,
        help="onde gravar os vereditos (por omissão, data/vereditos.json)",
    )
    ensaio.add_argument(
        "--relatorio", type=Path, default=DEFAULT_REPORT,
        help="onde escrever o relatório em Markdown (por omissão, relatorios/relatorio.md)",
    )
    ensaio.add_argument(
        "--protocolo", type=Path, default=None,
        help=PROTOCOL_HELP,
    )
    ensaio.add_argument(
        "--fontes-confirmadas", action="store_true",
        help="omitir o aviso de fontes por confirmar (apenas depois de confirmadas)",
    )

    modelos = sub.add_parser(
        "modelos", help="listar os modelos disponíveis no fornecedor"
    )
    modelos.add_argument("--fornecedor", choices=("openai", "anthropic", "gemini", "google", "local"), required=True)

    prot = sub.add_parser(
        "protocolo", help="escrever um protocolo com o critério de aprovação, antes do ensaio"
    )
    prot.add_argument("--nome", required=True)
    prot.add_argument("--casos", type=Path, default=DEFAULT_CASES)
    prot.add_argument("--saida", type=Path, required=True)
    freeze = prot.add_mutually_exclusive_group()
    freeze.add_argument(
        "--congelar-corretor", action="store_true",
        help="fixar no protocolo a versão do pacote inteiro (qualquer edição ao código a muda, incluindo "
        "o relatório e as traduções); o relatório assinala qualquer alteração. Para fixar só o que "
        "decide a correção, usar --congelar-correcao",
    )
    freeze.add_argument(
        "--congelar-correcao", action="store_true",
        help="fixar no protocolo a versão só dos ficheiros que decidem a correção (checks, grading, "
        "models, risk, storage e protocolo); editar o relatório, a interface ou as traduções não a "
        "muda. Não se usa com --congelar-corretor",
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
        help=PROTOCOL_HELP,
    )
    relatorio.add_argument(
        "--fontes-confirmadas",
        action="store_true",
        help="omitir o aviso de fontes por confirmar (apenas depois de confirmadas)",
    )

    return parser


def comando_executar(args: argparse.Namespace) -> int:
    return _executar(
        args.casos, args.fornecedor, args.modelo, args.saida, args.limite, args.tentativas,
        args.repeticoes, args.temperatura, args.tokens_max, args.recomecar,
        teto_eur=args.teto_eur, a_seco=args.a_seco, piloto=args.piloto, repetir_incertas=args.repetir_incertas,
        base_url=args.base_url,
    )


def _executar(
    casos: Path, fornecedor: str, modelo: str | None, saida: Path, limite: int, tentativas: int,
    repeticoes: int, temperatura: float, tokens_max: int, recomecar: bool,
    errors_out: dict[str, str] | None = None,
    *, teto_eur: Decimal | None = None, a_seco: bool = False, piloto: bool = False,
    repetir_incertas: bool = False, base_url: str | None = None,
) -> int:
    cases = read_cases(casos)
    if piloto:
        if limite > 0:
            print("erro: --piloto escolhe os casos e não se combina com --limite", file=sys.stderr)
            return 2
        cases, chosen = _pilot_cases(cases)
        if not cases:
            print(f"erro: {'; '.join(chosen)}", file=sys.stderr)
            return 2
        repeticoes = PILOT_SAMPLES
        saida = saida.parent / PILOT_FOLDER / saida.name
        print(f"piloto: {'; '.join(chosen)}; {PILOT_SAMPLES} amostras cada; tudo gravado em {saida.parent}")
    elif limite > 0:
        cases = cases[:limite]

    if base_url is not None and fornecedor != "local-compativel":
        print("erro: --base-url só se usa com --fornecedor local-compativel", file=sys.stderr)
        return 2
    paid_info = _paid_model(fornecedor, modelo)
    if a_seco:
        return _a_seco(paid_info, cases, repeticoes, tokens_max, teto_eur)
    if paid_info is not None and not paid_info[1].is_free and teto_eur is None:
        print(
            f"erro: {paid_info[1].requested_id} é um modelo pago (está em aferidor/catalogo.json) e não arranca sem "
            "--teto-eur, o gasto máximo do ensaio em euros; sem valor por omissão. Para ver o custo antes, "
            "usar --a-seco",
            file=sys.stderr,
        )
        return 2

    try:
        provider = build_provider(
            fornecedor, modelo, temperature=temperatura, max_tokens=tokens_max,
            timeout=paid_info[1].timeout_s if paid_info else None,
            entry=paid_info[1] if paid_info else None, base_url=base_url,
        )
        if fornecedor == "local-compativel":
            print(f"o servidor tem carregado: {provider.confirm_model()}")
    except ProviderError as error:
        print(f"erro: {error}", file=sys.stderr)
        return 2

    paid: PaidCalls | None = None
    if paid_info is not None:
        catalog, entry = paid_info
        preview = estimate(
            catalog, [entry.key], [build_prompt(c) for c in cases], day=date.today(), samples=repeticoes,
            tokens_max=tokens_max, ceiling_eur=teto_eur,
        )
        print(format_estimate(preview))
        ensaio = (f"{saida.resolve().parent.parent.name}/{PILOT_FOLDER}" if piloto else saida.resolve().parent.name)
        paid = PaidCalls(
            catalog=catalog, model_key=entry.key, ledger=Ledger(saida.with_name("custos.jsonl")),
            provenance_file=provenance_path(saida), ensaio=ensaio, ceiling_eur=teto_eur if teto_eur is not None else Decimal(0),
            retry_uncertain=repetir_incertas,
        )
    elif repetir_incertas:
        print("aviso: --repetir-incertas só tem efeito num modelo pago (do catálogo); este não tem livro de custos",
              file=sys.stderr)

    if recomecar and paid is not None and not _confirm_paid_restart(paid, provider.name, saida):
        return 2
    if recomecar and saida.exists():
        existing = read_answers(saida)
        kept = [a for a in existing if a.model != provider.name]
        discarded = len(existing) - len(kept)
        write_answers(kept, saida)
        if discarded:
            print(f"--recomecar: descartadas {discarded} respostas anteriores de {provider.name}")

    print(f"{len(cases)} casos x {repeticoes} amostra(s), modelo {provider.name}")

    def progress(case: Case, answer: Answer | None, status: str) -> None:
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
            paid=paid,
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
    if paid is not None:
        for line in _spend_lines(paid, saida, piloto, paid.ceiling_eur):
            print(line)
    if result.stopped:
        print(f"parada: {result.stopped}", file=sys.stderr)
        return STOPPED
    return 0 if result.complete else 1


def _ledgers_of(saida: Path, piloto: bool) -> tuple[Path, Path]:
    """The ledger of the trial and the ledger of its pilot, beside `saida` (which already is the pilot's, for a pilot)."""
    trial = saida.parent.parent if piloto else saida.parent
    return trial / "custos.jsonl", trial / PILOT_FOLDER / "custos.jsonl"


def _spend_lines(paid: PaidCalls, saida: Path, piloto: bool, ceiling: Decimal | None) -> list[str]:
    """What the trial and its pilot have spent, apart and together. They are two ledgers, each with its own ceiling."""
    trial_path, pilot_path = _ledgers_of(saida, piloto)
    name = paid.ensaio.split("/")[0]
    trial = Ledger(trial_path).summary(name)  # reading a ledger that is not there creates nothing
    pilot = Ledger(pilot_path).summary(f"{name}/{PILOT_FOLDER}")
    mine = pilot if piloto else trial
    lines = [
        f"gasto do ensaio: {trial['gasto_eur']:.4f} EUR em {trial['chamadas']} chamadas; "
        f"do piloto: {pilot['gasto_eur']:.4f} EUR em {pilot['chamadas']} chamadas; "
        f"soma: {trial['gasto_eur'] + pilot['gasto_eur']:.4f} EUR",
        f"o teto de {ceiling} EUR conta cada livro por si: o gasto efetivo máximo dos dois é o dobro, "
        f"{ceiling * 2} EUR (o pior caso conta onde não se sabe)",
    ]
    if mine["anterior_eur"]:
        lines.append(f"deste livro, {mine['anterior_eur']:.4f} EUR são de antes de um recomeço e {mine['novo_eur']:.4f} EUR de depois; "
                     "o teto conta os dois")
    if mine["sem_resultado"]:
        lines.append(f"por liquidar: {mine['sem_resultado']} chamadas reservadas e nunca liquidadas, {mine['por_liquidar_eur']:.4f} EUR "
                     "contados no pior caso; só se repetem com --repetir-incertas")
    return lines


def _confirm_paid_restart(paid: PaidCalls, model_name: str, saida: Path) -> bool:
    """Show what is already spent and ask, in writing, before the answers of a paid model are thrown away.

    The ledger keeps every line: what was spent stays in the total and the ceiling still counts it. Nothing is
    thrown away without a typed confirmation and a reason, so a script cannot do it by accident.
    """
    summary = paid.ledger.summary(paid.ensaio)
    if not summary["chamadas"] and not (saida.exists() and any(a.model == model_name for a in read_answers(saida))):
        return True
    print(
        f"--recomecar num modelo pago: neste ensaio já se gastaram {summary['gasto_eur']:.4f} EUR em {summary['chamadas']} "
        f"chamadas ({summary['anterior_eur']:.4f} EUR de antes de recomeços anteriores). O livro não se apaga e este "
        f"gasto continua a contar para o teto de {paid.ceiling_eur} EUR; só as respostas de {model_name} são apagadas."
    )
    try:
        typed = input("Para apagar as respostas e recomeçar escreve RECOMECAR: ")
        if typed.strip().lower() not in ("recomecar", "recomeçar"):
            print("erro: recomeço não confirmado; nada foi apagado", file=sys.stderr)
            return False
        reason = input("Razão do recomeço (uma linha): ").strip()
    except EOFError:
        print("erro: o recomeço de um modelo pago pede confirmação escrita e não há onde a ler; nada foi apagado",
              file=sys.stderr)
        return False
    if not reason:
        print("erro: um recomeço precisa de uma razão; nada foi apagado", file=sys.stderr)
        return False
    paid.ledger.restart(paid.ensaio, paid.model_key, reason)
    print("recomeço registado no livro de custos")
    return True


def _a_seco(
    paid_info: tuple[Catalog, Model] | None, cases: list[Case], samples: int, tokens_max: int, ceiling: Decimal | None
) -> int:
    """The dry run: the estimate on the screen, no request, no file."""
    if paid_info is None:
        print("este modelo não está no catálogo de modelos pagos: não há custo a estimar")
        return 0
    catalog, entry = paid_info
    print(format_estimate(estimate(
        catalog, [entry.key], [build_prompt(c) for c in cases], day=date.today(), samples=samples,
        tokens_max=tokens_max, ceiling_eur=ceiling,
    )))
    return 0


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
            print(f"  {counts.critical} respostas com falha crítica")
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
    if protocol.grader_id and protocol.grader_id != grader_id():
        found.append(
            f"o protocolo fixou o corretor na versão {protocol.grader_id}, mas esta é a {grader_id()} "
            "(mudou um dos seis ficheiros que decidem a correção ou a aprovação; ver docs/METODO.md)"
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
    data = protocolo.template(
        args.nome, args.casos, freeze_grader=args.congelar_corretor,
        freeze_correction=args.congelar_correcao,
    )
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"protocolo em {args.saida}, para {args.casos} (SHA-256 {data['banco_sha256'][:12]})")
    if "versao_corretor" in data:
        print(f"corretor fixado na versão {data['versao_corretor']}")
    if "corretor_id" in data:
        print(f"correção fixada na versão {data['corretor_id']}")
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
    if args.a_seco:
        return _executar(
            args.casos, args.fornecedor, args.modelo, args.saida, args.limite, args.tentativas,
            args.repeticoes, args.temperatura, args.tokens_max, args.recomecar,
            teto_eur=args.teto_eur, a_seco=True,
        )
    if args.piloto:
        print("erro: o piloto corre-se com 'executar --piloto'; 'ensaio' classificaria e escreveria o relatório de 3 casos", file=sys.stderr)
        return 2
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
        teto_eur=args.teto_eur, repetir_incertas=args.repetir_incertas,
    )
    if codigo in (2, STOPPED):
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
    "executar": comando_executar,
    "verificar": comando_verificar,
    "classificar": comando_classificar,
    "relatorio": comando_relatorio,
    "ensaio": comando_ensaio,
    "modelos": comando_modelos,
    "protocolo": comando_protocolo,
    "revisao": comando_revisao,
    "concordancia": comando_concordancia,
    "manifesto": comando_manifesto,
    "comparar-vereditos": comando_comparar,
}


def main(argv: list[str] | None = None) -> int:
    """Run one command; a missing or malformed file ends in a message, not a traceback."""
    args = parse_args(list(sys.argv[1:] if argv is None else argv))
    command = _COMMANDS[args.comando]  # the sub-command is required, so it is always one of these
    try:
        return command(args)
    except json.JSONDecodeError as error:
        print(f"erro: ficheiro JSON inválido, linha {error.lineno}, coluna {error.colno}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as error:
        print(f"erro: {error}", file=sys.stderr)
        return 2

__all__ = ["main", "build_parser", "build_provider", "parse_args"]
