"""Tests for the verification layer, with Crossref + OpenAlex mocked via respx."""

import httpx
import pytest
import respx

from hallucitation.parse import Citation
from hallucitation.verify import verify_citations, RateLimiter


CROSSREF_WORK_JSON = {
    "message": {
        "DOI": "10.1/abc",
        "title": ["Attention Is All You Need"],
        "author": [
            {"family": "Vaswani", "given": "Ashish"},
            {"family": "Shazeer", "given": "Noam"},
        ],
        "issued": {"date-parts": [[2017]]},
        "container-title": ["NeurIPS"],
        "URL": "https://doi.org/10.1/abc",
        "type": "proceedings-article",
    }
}

OPENALEX_WORK_JSON = {
    "doi": "https://doi.org/10.1/abc",
    "title": "Attention Is All You Need",
    "display_name": "Attention Is All You Need",
    "publication_year": 2017,
    "authorships": [
        {"author": {"display_name": "Ashish Vaswani"}},
        {"author": {"display_name": "Noam Shazeer"}},
    ],
    "primary_location": {"source": {"display_name": "NeurIPS"}},
    "id": "https://openalex.org/W1",
    "type": "article",
}


@pytest.mark.asyncio
@respx.mock
async def test_verify_one_verified_via_mocks():
    respx.get("https://api.crossref.org/works").mock(
        return_value=httpx.Response(
            200, json={"message": {"items": [CROSSREF_WORK_JSON["message"]]}}
        )
    )
    respx.get("https://api.openalex.org/works").mock(
        return_value=httpx.Response(200, json={"results": [OPENALEX_WORK_JSON]})
    )

    c = Citation(
        raw="Vaswani, A. (2017). Attention is all you need. NeurIPS.",
        authors=["Vaswani, A."],
        title="Attention is all you need",
        year=2017,
    )
    results = await verify_citations([c], rate=0)
    assert len(results) == 1
    r = results[0]
    assert r.verdict == "verified"
    assert r.confidence >= 0.95


@pytest.mark.asyncio
@respx.mock
async def test_verify_one_hallucinated_when_apis_empty():
    respx.get("https://api.crossref.org/works").mock(
        return_value=httpx.Response(200, json={"message": {"items": []}})
    )
    respx.get("https://api.openalex.org/works").mock(
        return_value=httpx.Response(200, json={"results": []})
    )

    c = Citation(
        raw="Smith, J. (2099). Invented paper.",
        authors=["Smith, J."],
        title="Invented paper",
        year=2099,
    )
    results = await verify_citations([c], rate=0)
    assert len(results) == 1
    assert results[0].verdict == "hallucinated"


@pytest.mark.asyncio
@respx.mock
async def test_verify_doi_lookup_short_circuits():
    respx.get("https://api.crossref.org/works/10.1/abc").mock(
        return_value=httpx.Response(200, json=CROSSREF_WORK_JSON)
    )
    respx.get("https://api.openalex.org/works/doi:10.1/abc").mock(
        return_value=httpx.Response(200, json=OPENALEX_WORK_JSON)
    )

    c = Citation(
        raw="x", authors=["Vaswani, A."], title="Attention is all you need",
        year=2017, doi="10.1/abc",
    )
    results = await verify_citations([c], rate=0)
    assert results[0].verdict == "verified"
    assert results[0].confidence == 1.0


@pytest.mark.asyncio
async def test_rate_limiter_spaces_calls():
    import asyncio, time

    rl = RateLimiter(10.0)  # 100 ms spacing
    start = time.monotonic()
    await rl.acquire()
    await rl.acquire()
    await rl.acquire()
    elapsed = time.monotonic() - start
    # Should take at least ~0.2s (two 100ms gaps).
    assert elapsed >= 0.15
