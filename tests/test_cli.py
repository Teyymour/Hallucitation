"""CLI tests. These monkey-patch verify_citations_sync so we don't hit the network."""

from pathlib import Path

import pytest

from citation_cleaner import cli, verify
from citation_cleaner.parse import Citation
from citation_cleaner.verify import VerificationResult


def _fake_verify_all_verified(citations):
    return [
        VerificationResult(citation=c, verdict="verified", confidence=1.0, notes="ok")
        for c in citations
    ]


def _fake_verify_all_hallucinated(citations):
    return [
        VerificationResult(citation=c, verdict="hallucinated", confidence=0.05, notes="no match")
        for c in citations
    ]


def test_cli_exits_1_on_hallucinations(monkeypatch, capsys, hallucinated_pdf):
    monkeypatch.setattr(
        cli, "verify_citations_sync",
        lambda cits, rate=5.0: _fake_verify_all_hallucinated(cits),
    )
    code = cli.main(["check", str(hallucinated_pdf)])
    assert code == 1
    out = capsys.readouterr().out
    assert "hallucinated" in out.lower()


def test_cli_exits_0_on_all_verified(monkeypatch, real_pdf):
    monkeypatch.setattr(
        cli, "verify_citations_sync",
        lambda cits, rate=5.0: _fake_verify_all_verified(cits),
    )
    code = cli.main(["check", str(real_pdf)])
    assert code == 0


def test_cli_exits_2_on_missing_file(tmp_path):
    code = cli.main(["check", str(tmp_path / "nope.pdf")])
    assert code == 2


def test_cli_writes_output_file(monkeypatch, tmp_path, real_pdf):
    monkeypatch.setattr(
        cli, "verify_citations_sync",
        lambda cits, rate=5.0: _fake_verify_all_verified(cits),
    )
    out = tmp_path / "report.md"
    js = tmp_path / "report.json"
    code = cli.main(["check", str(real_pdf), "--output", str(out), "--json", str(js)])
    assert code == 0
    assert out.exists()
    assert js.exists()
    assert "Citation Cleaner Report" in out.read_text()


def test_cli_writes_annotated_pdf(monkeypatch, tmp_path, hallucinated_pdf):
    monkeypatch.setattr(
        cli, "verify_citations_sync",
        lambda cits, rate=5.0: _fake_verify_all_hallucinated(cits),
    )
    out_pdf = tmp_path / "annotated.pdf"
    code = cli.main(
        ["check", str(hallucinated_pdf), "--annotate", str(out_pdf), "-o", str(tmp_path / "r.md")]
    )
    assert code == 1
    assert out_pdf.exists()
    assert out_pdf.read_bytes()[:4] == b"%PDF"


