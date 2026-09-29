"""Reading and writing cases, answers and verdicts as JSON.

Cases are edited by hand, so the reader is strict and its errors name the file
and the case. A malformed case that loads quietly becomes a measurement nobody
can trust.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from .models import Alternative, Answer, Case, Criterion, CriterionResult, Source, Verdict
from .risk import failure_from_label


def _require(data: dict, key: str, where: str) -> object:
    if key not in data:
        raise ValueError(f"{where}: falta o campo {key!r}")
    return data[key]


def source_from_dict(data: dict, where: str) -> Source:
    consulted = data.get("consultada")
    return Source(
        name=str(_require(data, "nome", where)),
        reference=str(_require(data, "referencia", where)),
        url=str(data.get("url", "")),
        consulted=date.fromisoformat(consulted) if consulted else None,
    )


def source_to_dict(source: Source) -> dict:
    out: dict = {"nome": source.name, "referencia": source.reference}
    if source.url:
        out["url"] = source.url
    if source.consulted:
        out["consultada"] = source.consulted.isoformat()
    return out


def criterion_from_dict(data: dict, where: str) -> Criterion:
    terms = _require(data, "termos", where)
    if isinstance(terms, str):
        terms = [terms]
    if not isinstance(terms, list):
        raise ValueError(f"{where}: 'termos' tem de ser um texto ou uma lista")
    return Criterion(
        kind=str(_require(data, "tipo", where)),
        terms=tuple(str(t) for t in terms),
        failure=failure_from_label(str(_require(data, "falha", where))),
        description=str(data.get("descricao", "")),
    )


def criterion_to_dict(criterion: Criterion) -> dict:
    out: dict = {
        "tipo": criterion.kind,
        "termos": list(criterion.terms),
        "falha": criterion.failure.value,
    }
    if criterion.description:
        out["descricao"] = criterion.description
    return out


def case_from_dict(data: dict, where: str) -> Case:
    case_id = str(_require(data, "id", where))
    at = f"{where}, caso {case_id}"
    criteria = _require(data, "criterios", at)
    if not isinstance(criteria, list):
        raise ValueError(f"{at}: 'criterios' tem de ser uma lista")
    alternatives = data.get("alternativas", [])
    if not isinstance(alternatives, list):
        raise ValueError(f"{at}: 'alternativas' tem de ser uma lista")
    return Case(
        case_id=case_id,
        category=str(_require(data, "categoria", at)),
        question=str(_require(data, "pergunta", at)),
        reference=str(_require(data, "referencia", at)),
        source=source_from_dict(dict(_require(data, "fonte", at)), at),
        criteria=tuple(criterion_from_dict(dict(c), at) for c in criteria),
        notes=str(data.get("notas", "")),
        alternatives=tuple(alternative_from_dict(dict(a), at) for a in alternatives),
    )


def alternative_from_dict(data: dict, where: str) -> Alternative:
    description = str(_require(data, "descricao", where))
    at = f"{where}, alternativa {description!r}"
    criteria = _require(data, "criterios", at)
    if not isinstance(criteria, list):
        raise ValueError(f"{at}: 'criterios' tem de ser uma lista")
    return Alternative(
        description=description,
        reference=str(_require(data, "referencia", at)),
        criteria=tuple(criterion_from_dict(dict(c), at) for c in criteria),
    )


def alternative_to_dict(alternative: Alternative) -> dict:
    return {
        "descricao": alternative.description,
        "referencia": alternative.reference,
        "criterios": [criterion_to_dict(c) for c in alternative.criteria],
    }


def case_to_dict(case: Case) -> dict:
    out: dict = {
        "id": case.case_id,
        "categoria": case.category,
        "pergunta": case.question,
        "referencia": case.reference,
        "fonte": source_to_dict(case.source),
        "criterios": [criterion_to_dict(c) for c in case.criteria],
    }
    if case.notes:
        out["notas"] = case.notes
    if case.alternatives:
        out["alternativas"] = [alternative_to_dict(a) for a in case.alternatives]
    return out


# The review states the annotated bank format defines. Only a reviewed case
# may score.
REVIEW_STATES = ("revisto_fonte", "por_verificar")
NO_SOURCE_PLACE = "sem versão nem secção indicadas"


def _bank_case_to_legacy(data: dict, where: str) -> dict:
    """Map one case from the annotated bank format onto the format `case_from_dict` reads.

    The bank format (version 1.1 onwards) keeps, next to the checkable criteria,
    what a human reviewer needs: risk level, review state, source version and
    section, and the prose lists of required elements and critical errors. Only
    the parts the grader uses are carried across; the rest stays in the file for
    people to read. The risk level and any grading note travel in `notas` so the
    report can still show them.

    The review state is enforced, not just carried. The bank itself says a
    case marked `por_verificar` has no confirmed source and must not be used
    to score, so such a case is refused with its id, rather than loaded and
    counted like any other. An unknown state is refused too: a typo there
    would otherwise decide silently whether a case counts.

    A case with neither a source version nor a section keeps that gap in
    plain sight: its reference reads "sem versão nem secção indicadas", not a
    placeholder that looks like a place in a document.
    """
    case_id = str(_require(data, "id", where))
    at = f"{where}, caso {case_id}"
    reference = " ".join(
        part for part in (data.get("fonte_versao", ""), data.get("fonte_seccao", "")) if part
    ) or NO_SOURCE_PLACE
    source: dict = {"nome": _require(data, "fonte", at), "referencia": reference}
    if data.get("data_verificacao"):
        source["consultada"] = data["data_verificacao"]
    notes = " ".join(
        part for part in (f"Risco {data.get('risco', '')}.", data.get("nota_avaliacao", "")) if part
    )
    mapped = {
        "id": case_id,
        "categoria": _require(data, "area", at),
        "pergunta": _require(data, "pergunta", at),
        "referencia": _require(data, "resposta_referencia", at),
        "fonte": source,
        "criterios": _require(data, "criterios", at),
        "notas": notes,
    }
    if "alternativas" in data:
        mapped["alternativas"] = data["alternativas"]
    state = str(_require(data, "estado", at))
    if state not in REVIEW_STATES:
        raise ValueError(
            f"{at}: estado {state!r} desconhecido; esperava um de {', '.join(REVIEW_STATES)}"
        )
    if state == "por_verificar":
        raise ValueError(
            f"{at}: marcado por_verificar, sem fonte confirmada; não pode pontuar."
            " Retirá-lo do ficheiro ou confirmar a fonte antes de correr este banco"
        )
    return mapped


def read_cases(path: Path) -> list[Case]:
    """Load every case in a JSON file, refusing duplicates and empty sets."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "casos" in raw:
        raw = [_bank_case_to_legacy(dict(item), str(path)) for item in raw["casos"]]
    if not isinstance(raw, list):
        raise ValueError(f"{path}: esperava uma lista de casos no nível de topo")
    if not raw:
        raise ValueError(f"{path}: nenhum caso encontrado")

    cases = [case_from_dict(dict(item), str(path)) for item in raw]
    seen: set[str] = set()
    for case in cases:
        if case.case_id in seen:
            raise ValueError(f"{path}: identificador de caso repetido {case.case_id!r}")
        seen.add(case.case_id)
    return cases


def write_cases(cases: list[Case], path: Path) -> int:
    payload = [case_to_dict(c) for c in cases]
    Path(path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return len(payload)


def answer_to_dict(answer: Answer) -> dict:
    return {
        "caso": answer.case_id,
        "modelo": answer.model,
        "texto": answer.text,
        "perguntada_em": answer.asked_at.isoformat(),
        "latencia_ms": answer.latency_ms,
        "execucao": answer.run_id,
        "amostra": answer.sample,
        "temperatura": answer.temperature,
        "fim": answer.finish_reason,
        "prompt_sha256": answer.prompt_sha256,
        "tokens_max": answer.max_tokens,
        "versao": answer.build,
    }


def answer_from_dict(data: dict, where: str) -> Answer:
    return Answer(
        case_id=str(_require(data, "caso", where)),
        model=str(_require(data, "modelo", where)),
        text=str(_require(data, "texto", where)),
        asked_at=datetime.fromisoformat(str(_require(data, "perguntada_em", where))),
        latency_ms=int(data.get("latencia_ms", 0)),
        run_id=str(data.get("execucao", "")),
        sample=int(data.get("amostra", 1)),
        temperature=float(data.get("temperatura", 0.0)),
        finish_reason=str(data.get("fim", "stop")),
        prompt_sha256=str(data.get("prompt_sha256", "")),
        max_tokens=int(data["tokens_max"]) if data.get("tokens_max") is not None else None,
        build=str(data.get("versao", "")),
    )


def write_answers(answers: list[Answer], path: Path) -> int:
    """One JSON object per line, so a long run can be appended to and resumed."""
    with Path(path).open("w", encoding="utf-8") as handle:
        for answer in answers:
            handle.write(json.dumps(answer_to_dict(answer), ensure_ascii=False) + "\n")
    return len(answers)


def append_answer(answer: Answer, path: Path) -> None:
    """Add one answer to the file as soon as it arrives.

    A run interrupted halfway leaves every answer it already got, so it is
    resumed instead of paid for twice.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(answer_to_dict(answer), ensure_ascii=False) + "\n")


def read_answers(path: Path) -> list[Answer]:
    answers: list[Answer] = []
    with Path(path).open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            if line.strip():
                answers.append(answer_from_dict(json.loads(line), f"{path}:{number}"))
    return answers


def verdict_to_dict(verdict: Verdict) -> dict:
    return {
        "caso": verdict.case_id,
        "modelo": verdict.model,
        "passou": verdict.passed,
        "falhas": [f.value for f in verdict.failures],
        "risco": str(verdict.worst_risk) if verdict.worst_risk else "",
        "alternativa": verdict.alternative,
        "criterios": [
            {
                "tipo": r.criterion.kind,
                "termos": list(r.criterion.terms),
                "passou": r.passed,
                "evidencia": r.evidence,
            }
            for r in verdict.results
        ],
    }


def write_verdicts(verdicts: list[Verdict], path: Path) -> int:
    payload = [verdict_to_dict(v) for v in verdicts]
    Path(path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return len(payload)


__all__ = [
    "read_cases",
    "write_cases",
    "read_answers",
    "write_answers",
    "append_answer",
    "write_verdicts",
    "case_from_dict",
    "case_to_dict",
    "answer_from_dict",
    "answer_to_dict",
    "verdict_to_dict",
    "CriterionResult",
]
