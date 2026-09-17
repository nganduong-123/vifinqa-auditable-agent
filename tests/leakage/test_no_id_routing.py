"""Test that the general pipeline does not import locked benchmark assets."""

from pathlib import Path

def test_no_id_registry():
    """Ensure that general pipeline modules do not import release_plan.jsonl or other locked assets."""
    root = Path(__file__).resolve().parents[2]
    source = (root / "src" / "vifinqa" / "pipelines" / "general.py").read_text(
        encoding="utf-8"
    )
    forbidden = ("release_plan.jsonl", "benchmark_locked", "golden_submission")
    assert all(value not in source for value in forbidden)
