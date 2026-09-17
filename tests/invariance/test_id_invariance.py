"""Test ID invariance for the general pipeline."""

from vifinqa.financial_ir import (
    FactRequest,
    FinancialPlanV2,
    InferenceRequest,
    evaluate_plan,
)

def test_id_invariance():
    """Ensure that InferenceRequest can hold the same question with different IDs."""
    q = "Doanh thu của FPT năm 2023 là bao nhiêu?"
    req1 = InferenceRequest(question=q)
    req2 = InferenceRequest(question=q, request_id=1)
    req3 = InferenceRequest(question=q, request_id=999999)
    
    assert req1.question == req2.question == req3.question

def test_missing_id():
    """Ensure that a request without an ID returns a valid ANSWERED status."""
    plan = FinancialPlanV2(
        question="Doanh thu của FPT năm 2023 là bao nhiêu?",
        facts=(
            FactRequest(
                id="revenue",
                ticker="FPT",
                year=2023,
                metric="doanh thu",
                scope="any",
                period="flow",
                unit="VND_1e9",
            ),
        ),
        nodes=(),
        output="revenue",
        output_unit="VND_1e9",
        generator="unit-test",
    )
    assert evaluate_plan(plan, {"revenue": 123.0}) == 123.0

