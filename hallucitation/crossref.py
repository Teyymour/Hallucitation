"""Minimal async client for the Crossref REST API (https://api.crossref.org)."""

from __future__ import annotations

from typing import Any

import httpx

from hallucitation.parse import Citation

CROSSREF_BASE = "https://api.crossref.org"
USER_AGENT = "hallucitation/0.1 (https://github.com/Teyymour/Hallucitation; mailto:noreply@example.com)"


def _extract_work(doc: dict[str, Any]) -> dict[str, Any]:
    """Flatten a Crossref ``message`` item into the fields we care about."""
    titles = doc.get("title") or []
    authors_raw = doc.get("author") or []
    authors: list[str] = []
    for a in authors_raw:
        family = a.get("family")
        given = a.get("given")
        if family and given:
            authors.append(f"{family}, {given}")
        elif family:
            authors.append(family)
    year = None
    for key in ("published-print", "published-online", "issued", "created"):
        parts = doc.get(key, {}).get("date-parts")
        if parts and parts[0] and parts[0][0]:
            year = int(parts[0][0])
            break
    container = doc.get("container-title") or []
    return {
        "doi": doc.get("DOI"),
        "title": titles[0] if titles else None,
        "authors": authors,
        "year": year,
        "journal": container[0] if container else None,
        "url": doc.get("URL"),
        "type": doc.get("type"),
    }


async def lookup_by_doi(client: httpx.AsyncClient, doi: str) -> dict[str, Any] | None:
    url = f"{CROSSREF_BASE}/works/{doi}"
    try:
        resp = await client.get(url, headers={"User-Agent": USER_AGENT}, timeout=15.0)
    except httpx.HTTPError:
        return None
    if resp.status_code != 200:
        return None
    try:
        data = resp.json()
    except ValueError:
        return None
    msg = data.get("message")
    if not isinstance(msg, dict):
        return None
    return _extract_work(msg)


async def search_by_citation(
    client: httpx.AsyncClient, citation: Citation
) -> dict[str, Any] | None:
    """Bibliographic free-text search against Crossref."""
    if not citation.title:
        return None

    # Use query.title for the main signal; use query.author as a filter.
    params: dict[str, Any] = {
        "query.title": citation.title,
        "rows": 5,
    }
    if citation.first_author_surname:
        params["query.author"] = citation.first_author_surname

    url = f"{CROSSREF_BASE}/works"
    try:
        resp = await client.get(
            url, params=params, headers={"User-Agent": USER_AGENT}, timeout=20.0
        )
    except httpx.HTTPError:
        return None
    if resp.status_code != 200:
        return None
    try:
        data = resp.json()
    except ValueError:
        return None
    items = data.get("message", {}).get("items") or []
    if not items:
        return None

    # Pick the best of the top results by title similarity + author match.
    from rapidfuzz import fuzz

    want_title = (citation.title or "").lower()
    want_surname = (citation.first_author_surname or "").lower()
    best = None
    best_score = -1.0
    for item in items:
        titles = item.get("title") or []
        item_title = (titles[0] if titles else "").lower()
        sim = fuzz.token_sort_ratio(want_title, item_title) / 100.0 if want_title else 0.0
        surnames = [
            (a.get("family") or "").lower() for a in (item.get("author") or [])
        ]
        surname_bonus = 0.3 if want_surname and want_surname in surnames else 0.0
        score = sim + surname_bonus
        if score > best_score:
            best_score = score
            best = item
    return _extract_work(best) if best else None


async def find(
    client: httpx.AsyncClient, citation: Citation
) -> dict[str, Any] | None:
    """DOI-first lookup, with fallback to bibliographic search."""
    if citation.doi:
        hit = await lookup_by_doi(client, citation.doi)
        if hit:
            return hit
    return await search_by_citation(client, citation)
