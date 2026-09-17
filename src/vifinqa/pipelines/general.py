"""General ViFinQA pipeline for questions that are not ID-locked.

The competition release remains reproducible through ``benchmark-locked``.
This module extends the project with a usable path for new questions: parse,
retrieve number-masked context, optionally call a planner endpoint, ground the
returned plan, and emit auditable JSONL results.
"""

from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..auto_planner import build_prompt, validate_response
from ..financial_ir import FinancialPlanV2
from ..grounded_plans import GroundedBinder
from ..retrieval_context import RetrievalContextBuilder
from ..semantic_parser import QuestionSpec, parse_question


def _post_planner(url: str, prompt: str, timeout: float = 120.0) -> str:
    payload = json.dumps({"prompts": [prompt], "max_tokens": 2400}).encode("utf-8")
    request = Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - configured endpoint
            body = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as error:
        raise RuntimeError(f"Planner endpoint failed: {error}") from error
    responses = body.get("responses")
    if not isinstance(responses, list) or not responses or not isinstance(responses[0], str):
        raise ValueError("Planner response must contain responses[0] as JSON text")
    return responses[0]


def _spec_payload(spec: QuestionSpec) -> dict[str, Any]:
    return asdict(spec)


def _process_question(
    *,
    request_id: int,
    question: str,
    builder: RetrievalContextBuilder,
    database_path: Path,
    schema: dict[str, Any],
    modal_url: Optional[str],
) -> dict[str, Any]:
    spec = parse_question(question)
    tickers = {entity.ticker for entity in spec.entities if entity.ticker}
    record: dict[str, Any] = {
        "request_id": request_id,
        "question": question,
        "analysis": _spec_payload(spec),
        "status": "ANALYZED_ONLY",
    }

    if not tickers or not spec.periods:
        record["error"] = "Question must identify at least one company and year"
        return record

    try:
        context = builder.build(
            question_id=request_id,
            question=question,
            tickers=tickers,
            question_spec=spec,
        )
    except Exception as error:
        record["status"] = "RETRIEVAL_ERROR"
        record["error"] = str(error)
        return record

    record["retrieval"] = {
        "table_count": len(context.get("tables", [])),
        "table_ids": [table["table_id"] for table in context.get("tables", [])],
        "number_masked": True,
    }
    if not modal_url:
        return record

    prompt = build_prompt(
        question=question,
        tickers=sorted(tickers),
        schema=schema,
        context=context,
    )
    raw_response = _post_planner(modal_url, prompt)
    validated = validate_response(
        raw_response=raw_response,
        question=question,
        model=os.environ.get("PLANNER_MODEL", "remote-planner"),
    )
    if validated["status"] != "VALID":
        record["status"] = "PLAN_REJECTED"
        record["error"] = validated.get("error", "Invalid planner output")
        return record

    plan = FinancialPlanV2.from_dict(validated["plan"])
    missing_refs = [fact.id for fact in plan.facts if fact.row_ref is None]
    if missing_refs:
        record["status"] = "PLAN_REJECTED"
        record["error"] = f"Planner facts are missing row_ref: {missing_refs}"
        return record
    try:
        with GroundedBinder(database_path) as binder:
            result = binder.bind_plan(plan)
    except Exception as error:
        record["status"] = "GROUNDING_REJECTED"
        record["error"] = str(error)
        return record

    record.update(
        {
            "status": "ANSWERED",
            "answer": result.answer,
            "output_unit": plan.output_unit,
            "pandas_query": result.pandas_query,
            "bindings": [binding.__dict__ for binding in result.bindings],
            "plan": plan.to_dict(),
        }
    )
    return record


def run_general(
    questions_file: Optional[Path],
    output_dir: Path,
    database_path: Path,
) -> None:
    """Run batch or interactive analysis and persist every result as JSONL."""

    if not database_path.is_file():
        raise FileNotFoundError(
            f"ViFinQA database not found at {database_path}. Build it with vifinqa-corpus first."
        )
    schema_path = Path("analysis/financial_plan_v2.schema.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    modal_url = os.environ.get("MODAL_API_URL")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "general_results.jsonl"

    questions: list[str] = []
    if questions_file:
        for line in questions_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            questions.append(json.loads(line)["question"] if line.startswith("{") else line)

    records: list[dict[str, Any]] = []
    with RetrievalContextBuilder(database_path) as builder:
        if questions_file:
            for index, question in enumerate(questions, 1):
                records.append(
                    _process_question(
                        request_id=index,
                        question=question,
                        builder=builder,
                        database_path=database_path,
                        schema=schema,
                        modal_url=modal_url,
                    )
                )
        else:
            print("Interactive mode. Type 'exit' or 'quit' to stop.")
            while True:
                try:
                    question = input("Question: ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if question.lower() in {"exit", "quit"}:
                    break
                if not question:
                    continue
                record = _process_question(
                    request_id=len(records) + 1,
                    question=question,
                    builder=builder,
                    database_path=database_path,
                    schema=schema,
                    modal_url=modal_url,
                )
                records.append(record)
                print(json.dumps(record, ensure_ascii=False, indent=2))

    output_path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    print(json.dumps({"results": str(output_path), "count": len(records)}, ensure_ascii=False))
