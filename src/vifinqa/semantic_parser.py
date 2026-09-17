"""Semantic Parser module for ViFinQA.

This module parses natural language questions into structured QuestionSpec objects,
separating entities, periods, metrics, scope, operation, and units.
"""

import csv
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class EntityRef:
    ticker: Optional[str]
    name: Optional[str]
    alias: Optional[str]

@dataclass(frozen=True)
class PeriodRef:
    year: Optional[int]
    is_comparative: bool = False
    is_flow: bool = False

@dataclass(frozen=True)
class Constraint:
    type: str
    value: str

@dataclass(frozen=True)
class QuestionSpec:
    entities: tuple[EntityRef, ...]
    periods: tuple[PeriodRef, ...]
    scope: str
    requested_metrics: tuple[str, ...]
    operation: str
    output_unit: str
    constraints: tuple[Constraint, ...]
    ambiguities: tuple[str, ...]

BUILTIN_COMPANIES = {
    "ngân hàng tmcp ngoại thương việt nam": "VCB",
    "công ty cổ phần fpt": "FPT",
    "tập đoàn fpt": "FPT",
    "công ty cổ phần sữa việt nam": "VNM",
    "ngân hàng tmcp á châu": "ACB",
    "ngân hàng tmcp việt nam thịnh vượng": "VPB",
}


METRIC_ALIASES = {
    "lợi nhuận sau thuế": "lợi nhuận sau thuế",
    "lợi nhuận trước thuế": "lợi nhuận trước thuế",
    "doanh thu thuần": "doanh thu thuần",
    "doanh thu": "doanh thu",
    "tổng tài sản": "tổng tài sản",
    "nợ ngắn hạn": "nợ ngắn hạn",
    "tổng nợ": "tổng nợ",
    "vốn chủ sở hữu": "vốn chủ sở hữu",
    "hàng tồn kho": "hàng tồn kho",
    "lưu chuyển tiền thuần từ hoạt động kinh doanh": "lưu chuyển tiền thuần từ hoạt động kinh doanh",
    "dòng tiền từ hoạt động kinh doanh": "lưu chuyển tiền thuần từ hoạt động kinh doanh",
    "tiền và các khoản tương đương tiền": "tiền và các khoản tương đương tiền",
    "các khoản tương đương tiền": "các khoản tương đương tiền",
    "chi phí tài chính": "chi phí tài chính",
    "chi phí bán hàng": "chi phí bán hàng",
    "chi phí quản lý": "chi phí quản lý doanh nghiệp",
    "lợi nhuận gộp": "lợi nhuận gộp",
}


def load_stock_codes(path: Path | None = None) -> dict[str, str]:
    """Load the official company catalogue with a small offline fallback.

    The fallback keeps the parser and portfolio demo useful before the private
    competition dataset is downloaded.  Official data always wins when an
    alias appears in both sources.
    """

    mapping = dict(BUILTIN_COMPANIES)
    path = path or Path("ViFinQA/code_stock.csv")
    if path.exists():
        with open(path, encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader) # skip header
            for row in reader:
                if len(row) >= 2:
                    mapping[row[1].strip().lower()] = row[0].strip()
    return mapping

STOCK_CODES = load_stock_codes()

def parse_entities(question: str) -> tuple[EntityRef, ...]:
    entities = []
    tickers = set(re.findall(r'\b[A-Z]{3}\b', question))
    for t in tickers:
        entities.append(EntityRef(ticker=t, name=None, alias=None))
    
    lower_q = question.lower()
    for name, ticker in STOCK_CODES.items():
        if name in lower_q:
            if ticker not in tickers:
                entities.append(EntityRef(ticker=ticker, name=name, alias=None))
                tickers.add(ticker)
    return tuple(entities)

def parse_periods(question: str) -> tuple[PeriodRef, ...]:
    years = {int(y) for y in re.findall(r"\b(20[1-2][0-9])\b", question)}
    for start_text, end_text in re.findall(
        r"\b(20[1-2][0-9])\s*[-–—]\s*(20[1-2][0-9])\b", question
    ):
        start, end = int(start_text), int(end_text)
        if start <= end and end - start <= 15:
            years.update(range(start, end + 1))
    ordered = sorted(years)
    lower_q = question.lower()
    is_flow = any(
        phrase in lower_q
        for phrase in ("trong năm", "doanh thu", "chi phí", "lợi nhuận", "dòng tiền")
    )
    return tuple(
        PeriodRef(year=year, is_comparative=len(ordered) > 1, is_flow=is_flow)
        for year in ordered
    )

def parse_scope(question: str) -> str:
    lower_q = question.lower()
    if "công ty mẹ" in lower_q or "riêng lẻ" in lower_q:
        return "separate"
    if "hợp nhất" in lower_q:
        return "consolidated"
    return "any"

def parse_unit(question: str) -> str:
    lower_q = question.lower()
    if "tỷ đồng" in lower_q:
        return "VND_1e9"
    if "triệu đồng" in lower_q:
        return "VND_1e6"
    if "nghìn đồng" in lower_q or "ngàn đồng" in lower_q:
        return "VND_1e3"
    if "đồng" in lower_q and "tỷ đồng" not in lower_q and "triệu đồng" not in lower_q and "nghìn đồng" not in lower_q and "ngàn đồng" not in lower_q:
        return "VND_1"
    if "phần trăm" in lower_q or "%" in lower_q:
        return "percent"
    if "lần" in lower_q:
        return "ratio"
    return "number"


def parse_operation(question: str) -> str:
    """Infer the requested calculation without introducing numeric values."""

    value = question.lower()
    rules = (
        (("tăng trưởng", "thay đổi bao nhiêu phần trăm", "tăng bao nhiêu phần trăm"), "percent_change"),
        (("tỷ trọng", "chiếm bao nhiêu phần trăm"), "ratio_percent"),
        (("chênh lệch", "trừ đi"), "subtract"),
        (("bao nhiêu mã", "bao nhiêu năm", "số lượng"), "count"),
        (("cao nhất", "lớn nhất"), "argmax"),
        (("thấp nhất", "nhỏ nhất"), "argmin"),
        (("trung bình", "bình quân"), "mean"),
        (("trung vị",), "median"),
        (("tổng cộng", "tổng số", "tính tổng"), "sum"),
        (("tỷ lệ", "tỷ số", "hệ số", "gấp bao nhiêu lần"), "ratio"),
    )
    for phrases, operation in rules:
        if any(phrase in value for phrase in phrases):
            return operation
    return "lookup"


def parse_metrics(question: str) -> tuple[str, ...]:
    """Return canonical financial metrics explicitly mentioned by the user."""

    value = question.lower()
    found: list[str] = []
    for alias in sorted(METRIC_ALIASES, key=len, reverse=True):
        canonical = METRIC_ALIASES[alias]
        if alias in value and canonical not in found:
            found.append(canonical)
    return tuple(found)


def parse_constraints(question: str) -> tuple[Constraint, ...]:
    value = question.lower()
    result: list[Constraint] = []
    rules = (
        ("trên mức trung vị", "greater_than", "median"),
        ("dưới mức trung vị", "less_than", "median"),
        ("dương", "sign", "positive"),
        ("âm", "sign", "negative"),
    )
    for phrase, kind, target in rules:
        if phrase in value:
            result.append(Constraint(type=kind, value=target))
    return tuple(result)

def parse_question(question: str) -> QuestionSpec:
    """Parse a question into a QuestionSpec."""
    entities = parse_entities(question)
    periods = parse_periods(question)
    scope = parse_scope(question)
    unit = parse_unit(question)
    metrics = parse_metrics(question)
    ambiguities = []
    if not entities:
        ambiguities.append("missing_entity")
    if not periods:
        ambiguities.append("missing_period")
    if not metrics:
        ambiguities.append("metric_requires_semantic_planner")
    return QuestionSpec(
        entities=entities,
        periods=periods,
        scope=scope,
        requested_metrics=metrics,
        operation=parse_operation(question),
        output_unit=unit,
        constraints=parse_constraints(question),
        ambiguities=tuple(ambiguities),
    )

