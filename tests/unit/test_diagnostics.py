from pathlib import Path

from vifinqa.diagnostics import ROOT, normalized_sha256, project_health


def test_locked_plan_hash_is_cross_platform():
    health = project_health(ROOT)
    assert health["execution_plan"]["checksum_matches"] is True
    assert health["execution_plan"]["questions"] == 1012
    assert health["execution_plan"]["sequential_ids"] is True


def test_normalized_hash_ignores_crlf(tmp_path: Path):
    lf = tmp_path / "lf.txt"
    crlf = tmp_path / "crlf.txt"
    lf.write_bytes(b"one\ntwo\n")
    crlf.write_bytes(b"one\r\ntwo\r\n")
    assert normalized_sha256(lf) == normalized_sha256(crlf)
