"""Dependency-light project diagnostics for local development and CI."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path
from typing import Any, Optional


ROOT = Path(__file__).resolve().parents[2]


def normalized_sha256(path: Path) -> str:
    """Hash text with LF endings so the locked plan is portable on Windows."""

    payload = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(payload).hexdigest()


def execution_plan_stats(path: Path) -> dict[str, Any]:
    question_ids: list[int] = []
    evidence_count = 0
    tables: set[str] = set()
    documents: set[str] = set()
    answer_types: dict[str, int] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid execution plan JSON at line {line_number}") from error
        question_ids.append(int(item["id"]))
        evidence_count += len(item["evidence"])
        tables.update(item["relevant_tables"])
        documents.update(item["relevant_docs"])
        answer_type = str(item.get("answer_type", "unknown"))
        answer_types[answer_type] = answer_types.get(answer_type, 0) + 1
    return {
        "questions": len(question_ids),
        "id_range": [min(question_ids), max(question_ids)] if question_ids else [],
        "sequential_ids": question_ids == list(range(1, len(question_ids) + 1)),
        "evidence_files": evidence_count,
        "source_tables": len(tables),
        "source_documents": len(documents),
        "answer_types": answer_types,
    }


def project_health(root: Path = ROOT) -> dict[str, Any]:
    config_path = root / "configs" / "release.json"
    plan_path = root / "configs" / "release_plan.jsonl"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    expected_hash = config["expected"]["execution_plan_sha256"]
    actual_hash = normalized_sha256(plan_path)
    paths = config["paths"]
    optional_files = {
        "questions": root / paths["questions"],
        "companies": root / paths["companies"],
        "database": root / paths["database"],
        "golden_submission": root / paths["golden_submission"],
    }
    missing = [name for name, path in optional_files.items() if not path.is_file()]
    return {
        "status": "ready" if not missing and actual_hash == expected_hash else "source-ready",
        "runtime": {"python": platform.python_version(), "platform": platform.platform()},
        "execution_plan": {
            **execution_plan_stats(plan_path),
            "checksum_matches": actual_hash == expected_hash,
            "sha256": actual_hash,
        },
        "artifacts": {
            name: {"path": str(path), "available": path.is_file()}
            for name, path in optional_files.items()
        },
        "missing_optional_artifacts": missing,
        "leaderboard": config["expected"]["leaderboard"],
        "models": [model["id"] for model in config["models"]],
    }


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--strict", action="store_true", help="Fail when private artifacts are absent")
    args = parser.parse_args(argv)
    result = project_health(args.root.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["execution_plan"]["checksum_matches"]:
        raise SystemExit(2)
    if args.strict and result["missing_optional_artifacts"]:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
