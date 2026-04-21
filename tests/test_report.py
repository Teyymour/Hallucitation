import json
from pathlib import Path

from hallucitation.parse import Citation
from hallucitation.report import (
    annotate_pdf,
    count_verdicts,
    to_json,
    to_markdown,
    write_json,
    write_markdown,
)
from hallucitation.verify import VerificationResult


def _mkresult(verdict, title="Foo", year=2020, author="Smith, J."):
    return VerificationResult(
        citation=Citation(raw=f"{author} ({year}). {title}.", authors=[author], title=title, year=year),
        verdict=verdict,
        confidence={"verified": 1.0, "partial_match": 0.7, "mangled": 0.4, "hallucinated": 0.05}[verdict],
        notes=f"test {verdict}",
    )


def test_count_verdicts():
    results = [_mkresult("verified"), _mkresult("hallucinated"), _mkresult("hallucinated")]
    counts = count_verdicts(results)
    assert counts["verified"] == 1
    assert counts["hallucinated"] == 2


def test_to_json_contains_expected_keys():
    results = [_mkresult("verified")]
    payload = json.loads(to_json(results))
    assert "summary" in payload
    assert payload["total"] == 1
    assert payload["results"][0]["verdict"] == "verified"


def test_to_markdown_headline():
    results = [_mkresult("hallucinated"), _mkresult("verified")]
    md = to_markdown(results, source="paper.pdf")
    assert "1 of 2" in md
    assert "hallucinated" in md
    assert "paper.pdf" in md


def test_write_json_and_markdown(tmp_path):
    results = [_mkresult("verified"), _mkresult("hallucinated")]
    jpath = write_json(results, tmp_path / "out.json")
    mpath = write_markdown(results, tmp_path / "out.md")
    assert jpath.exists()
    assert mpath.exists()
    data = json.loads(jpath.read_text())
    assert data["total"] == 2


def test_annotate_pdf_produces_valid_file(tmp_path, real_pdf):
    results = [_mkresult("hallucinated", title="Fake Paper")]
    out = tmp_path / "annotated.pdf"
    annotate_pdf(real_pdf, results, out)
    assert out.exists()
    assert out.stat().st_size > 0
    # Quick sanity check the file starts with the PDF magic.
    assert out.read_bytes()[:4] == b"%PDF"
