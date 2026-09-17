import pytest

from vifinqa.web_demo import analyze_question


def test_demo_analyzes_question():
    result = analyze_question("Lợi nhuận sau thuế của FPT năm 2023 là bao nhiêu tỷ đồng?")
    assert result["entities"][0]["ticker"] == "FPT"
    assert result["periods"][0]["year"] == 2023
    assert result["output_unit"] == "VND_1e9"


def test_demo_rejects_empty_question():
    with pytest.raises(ValueError, match="non-empty"):
        analyze_question(" ")
