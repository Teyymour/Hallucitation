"""Smoke test for the Streamlit webapp module.

We don't run the full Streamlit server; we just import the module and sanity-
check that the top-level helper function runs end-to-end with a monkey-patched
verifier. This ensures no import-time errors slip into the web entry point.
"""

from hallucitation import webapp
from hallucitation.parse import Citation
from hallucitation.verify import VerificationResult


def test_webapp_module_imports():
    assert hasattr(webapp, "main")


def test_webapp_run_helper(monkeypatch, real_pdf):
    """The internal `_run` helper should return (results, md, json) given a PDF."""

    def fake_verify_sync(citations, rate=5.0):
        return [
            VerificationResult(
                citation=c, verdict="verified", confidence=1.0, notes="stubbed"
            )
            for c in citations
        ]

    monkeypatch.setattr(webapp, "verify_citations_sync", fake_verify_sync)

    results, md, js = webapp._run(real_pdf)
    assert len(results) >= 1
    assert "Hallucitation Report" in md
    assert '"verdict": "verified"' in js
