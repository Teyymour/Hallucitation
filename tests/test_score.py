from citation_cleaner.parse import Citation
from citation_cleaner.score import (
    aggregate,
    author_overlap,
    doi_match,
    first_author_match,
    score_single_match,
    title_similarity,
    year_close,
)


def test_title_similarity_exact():
    assert title_similarity("Attention Is All You Need", "Attention is all you need") > 0.95


def test_title_similarity_zero():
    assert title_similarity(None, "x") == 0.0
    assert title_similarity("x", None) == 0.0


def test_author_overlap_basic():
    assert author_overlap(["Vaswani, A."], ["Vaswani, Ashish"]) == 1.0
    assert author_overlap(["Smith, J."], ["Jones, K."]) == 0.0


def test_year_close():
    assert year_close(2020, 2021)
    assert not year_close(2020, 2023)
    assert not year_close(None, 2020)


def test_doi_match_positive():
    c = Citation(raw="x", doi="10.1038/nature12345")
    match = {"doi": "10.1038/NATURE12345"}
    assert doi_match(c, match)


def test_first_author_match():
    c = Citation(raw="x", authors=["Vaswani, A."])
    match = {"authors": ["Vaswani, Ashish", "Shazeer, Noam"]}
    assert first_author_match(c, match)


def test_score_verified_by_doi():
    c = Citation(raw="x", doi="10.1/abc", title="Foo", authors=["Smith, J."], year=2020)
    match = {"doi": "10.1/abc", "title": "something", "authors": [], "year": None}
    verdict, conf, _ = score_single_match(c, match)
    assert verdict == "verified"
    assert conf >= 0.95


def test_score_verified_by_title_and_author():
    c = Citation(
        raw="x", title="Attention is all you need",
        authors=["Vaswani, A."], year=2017,
    )
    match = {
        "doi": "10.1/ok", "title": "Attention Is All You Need",
        "authors": ["Vaswani, Ashish"], "year": 2017,
    }
    verdict, conf, _ = score_single_match(c, match)
    assert verdict == "verified"


def test_score_hallucinated_no_match():
    c = Citation(raw="x", title="Unicorn riding handbook", authors=["Fake, F."], year=2099)
    verdict, _, _ = score_single_match(c, None)
    assert verdict == "hallucinated"


def test_score_hallucinated_weak_similarity():
    c = Citation(raw="x", title="Quantum toaster dynamics", authors=["Zz, Z."], year=2023)
    match = {"title": "Quantum computing primer", "authors": ["Smith, J."], "year": 1999}
    verdict, _, _ = score_single_match(c, match)
    assert verdict == "hallucinated"


def test_aggregate_dual_confirmation_bumps_confidence():
    c = Citation(
        raw="x", title="Attention Is All You Need",
        authors=["Vaswani, A."], year=2017,
    )
    match = {
        "title": "Attention Is All You Need",
        "authors": ["Vaswani, Ashish"], "year": 2017,
    }
    v, conf, note = aggregate(c, match, match)
    assert v == "verified"
    assert conf >= 0.95
    assert "both sources" in note or "crossref" in note


def test_aggregate_dual_none_is_hallucinated():
    c = Citation(raw="x", title="Fake", authors=["Nope, N."], year=2099)
    v, conf, _ = aggregate(c, None, None)
    assert v == "hallucinated"
    assert conf <= 0.1
