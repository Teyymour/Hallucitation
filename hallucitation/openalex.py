"""Minimal async client for the OpenAlex API (https://api.openalex.org)."""

from __future__ import annotations

from typing import Any

import httpx

from hallucitation.parse import Citation

OPENALEX_BASE = "https://api.openalex.org"
USER_AGENT = "hallucitation/0.1 (https://github.com/Teyymour/Hallucitation; mailto:noreply@example.com)"


def _extract_work(doc: dict[str, Any]) -> dict[str, Any]:
    authorships = doc.get("authorships") or []
    authors: list[str] = []
    for a in authorships:
        name = (a.get("author") or {}).get("display_name")
        if name:
            authors.append(name)
    venue = (doc.get("primary_location") or {}).get("source") or {}
    return {
        "doi": (doc.get("doi") or "").replace("https://doi.org/", "") or None,
        "title": doc.get("title") or doc.get("display_name"),
        "authors": authors,
        "year": doc.get("publication_year"),
        "journal": venue.get("display_name"),
        "url": doc.get("id"),
        "type": doc.get("type"),
    }


async def lookup_by_doi(client: httpx.AsyncClient, doi: str) -> dict[str, Any] | None:
    url = f"{OPENALEX_BASE}/works/doi:{doi}"
    try:
        resp = await client.get(url, headers={"User-Agent": USER_AGENT}, timeout=15.0)
    except httpx.HTTPError:
        return None
    if resp.status_code != 200:
        return None
    try:
        return _extract_work(resp.json())
    except ValueError:
        return None


async def search_by_citation(
    client: httpx.AsyncClient, citation: Citation
) -> dict[str, Any] | None:
    if not citation.title:
        return None
    # Use a title.search filter rather than generic `search` — much more precise.
    params: dict[str, Any] = {
        "filter": f"title.search:{citation.title}",
        "per-page": 5,
    }
    try:
        resp = await client.get(
            f"{OPENALEX_BASE}/works",
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=20.0,
        )
    except httpx.HTTPError:
        return None
    if resp.status_code != 200:
        return None
    try:
        data = resp.json()
    except ValueError:
        return None
    results = data.get("results") or []
    if not results:
        return None
    # Pick the best of the top 5 by simple scoring: title similarity + author surname presence.
    return _pick_best(results, citation)


def _pick_best(results: list, citation: Citation) -> dict[str, Any] | None:
    from rapidfuzz import fuzz

    best = None
    best_score = -1.0
    want_title = (citation.title or "").lower()
    want_surname = (citation.first_author_surname or "").lower()
    for item in results:
        item_title = (item.get("title") or item.get("display_name") or "").lower()
        sim = fuzz.token_sort_ratio(want_title, item_title) / 100.0 if want_title else 0.0
        authors = [
            ((a.get("author") or {}).get("display_name") or "").lower()
            for a in (item.get("authorships") or [])
        ]
        surname_bonus = 0.3 if want_surname and any(want_surname in a for a in authors) else 0.0
        score = sim + surname_bonus
        if score > best_score:
            best_score = score
            best = item
    return _extract_work(best) if best else None


async def find(
    client: httpx.AsyncClient, citation: Citation
) -> dict[str, Any] | None:
    if citation.doi:
        hit = await lookup_by_doi(client, citation.doi)
        if hit:
            return hit
    return await search_by_citation(client, citation)
