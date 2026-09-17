from vifinqa.semantic_parser import parse_question


def test_ratio_question_is_structured():
    spec = parse_question(
        "Tỷ trọng lợi nhuận sau thuế trên doanh thu của FPT năm 2023 là bao nhiêu phần trăm?"
    )
    assert spec.entities[0].ticker == "FPT"
    assert spec.periods[0].year == 2023
    assert spec.operation == "ratio_percent"
    assert spec.output_unit == "percent"
    assert spec.requested_metrics == ("lợi nhuận sau thuế", "doanh thu")
    assert spec.ambiguities == ()


def test_missing_fields_are_reported():
    spec = parse_question("Chỉ tiêu này là bao nhiêu?")
    assert set(spec.ambiguities) == {
        "missing_entity",
        "missing_period",
        "metric_requires_semantic_planner",
    }


def test_constraint_detection():
    spec = parse_question(
        "Bao nhiêu mã có nợ ngắn hạn trên mức trung vị và lợi nhuận dương năm 2023?"
    )
    assert spec.operation == "count"
    assert {(item.type, item.value) for item in spec.constraints} == {
        ("greater_than", "median"),
        ("sign", "positive"),
    }


def test_total_assets_is_a_metric_not_a_sum_request():
    spec = parse_question("Tổng tài sản của FPT năm 2023 là bao nhiêu tỷ đồng?")
    assert spec.operation == "lookup"
    assert spec.requested_metrics == ("tổng tài sản",)
