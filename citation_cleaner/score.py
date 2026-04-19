"""Scoring logic: compare a Citation against matched records and return a verdict."""

from __future__ import annotations

import re
from typing import Any

from rapidfuzz import fuzz

from citation_cleaner.parse import Citation


def _normalise(s: str | None) -> str:
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def title_similarity(a: str | None, b: str | None) -> float:
    na, nb = _normalise(a), _normalise(b)
    if not na or not nb:
        return 0.0
    return fuzz.token_sort_ratio(na, nb) / 100.0


def surname(name: str) -> str:
    name = name.strip()
    if "," in name:
        return _normalise(name.split(",", 1)[0])
    parts = name.split()
    return _normalise(parts[-1]) if parts else ""


def author_overlap(citation_authors: list[str], match_authors: list[str]) -> float:
    """Jaccard overlap of surnames."""
    a = {surname(x) for x in citation_authors if x}
    b = {surname(x) for x in match_authors if x}
    a.discard("")
    b.discard("")
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def first_author_match(citation: Citation, match: dict[str, Any]) -> bool:
    csurname = citation.first_author_surname
    if not csurname:
        return False
    match_authors = match.get("authors") or []
    if not match_authors:
        return False
    return _normalise(csurname) == surname(match_authors[0])


def year_close(c_year: int | None, m_year: int | None, tol: int = 1) -> bool:
    if c_year is None or m_year is None:
        return False
    return abs(c_year - m_year) <= tol


def doi_match(citation: Citation, match: dict[str, Any]) -> bool:
    if not citation.doi or not match.get("doi"):
        return False
    return citation.doi.lower().strip(".,;)]") == match["doi"].lower().strip(".,;)]")


def score_single_match(
    citation: Citation, match: dict[str, Any] | None
) -> tuple[str, float, str]:
    """Return (verdict, confidence, note) for a single source match."""
    if not match:
        return "hallucinated", 0.0, "no match in source"

    sim = title_similarity(citation.title, match.get("title"))
    fa_match = first_author_match(citation, match)
    yr_close = year_close(citation.year, match.get("year"))
    overlap = author_overlap(citation.authors, match.get("authors") or [])

    if doi_match(citation, match):
        return "verified", 1.0, f"DOI exact match ({match.get('doi')})"

    if sim >= 0.95 and (fa_match or overlap >= 0.5):
        return "verified", 0.95, f"title sim={sim:.2f}, author match"

    if sim >= 0.70:
        if fa_match and yr_close:
            return "partial_match", 0.8, f"title sim={sim:.2f}, author+year ok"
        if fa_match or yr_close or overlap >= 0.3:
            return "partial_match", 0.65, f"title sim={sim:.2f}, partial metadata"
        return "mangled", 0.4, f"title sim={sim:.2f} but author/year off"

    # Weak title similarity is only credible if author *and* year also match;
    # otherwise Crossref has just returned coincidental junk for a common surname.
    if sim >= 0.5 and fa_match and yr_close:
        return "mangled", 0.3, f"weak title sim={sim:.2f}, author+year ok"

    return "hallucinated", 0.1, f"title sim={sim:.2f} too low, no corroborating metadata"


_VERDICT_RANK = {
    "verified": 3,
    "partial_match": 2,
    "mangled": 1,
    "hallucinated": 0,
}


def aggregate(
    citation: Citation,
    crossref_match: dict[str, Any] | None,
    openalex_match: dict[str, Any] | None,
) -> tuple[str, float, str]:
    """Combine per-source verdicts into a final verdict."""
    cr_verdict, cr_conf, cr_note = score_single_match(citation, crossref_match)
    oa_verdict, oa_conf, oa_note = score_single_match(citation, openalex_match)

    # Pick the stronger of the two. If they disagree sharply, prefer the strongest
    # (dual confirmation) but bump confidence when both agree.
    cr_rank = _VERDICT_RANK[cr_verdict]
    oa_rank = _VERDICT_RANK[oa_verdict]

    if cr_rank >= oa_rank:
        final_verdict, final_conf, final_note = cr_verdict, cr_conf, f"crossref: {cr_note}"
    else:
        final_verdict, final_conf, final_note = oa_verdict, oa_conf, f"openalex: {oa_note}"

    # Dual confirmation bonus.
    if cr_verdict == oa_verdict and cr_verdict in ("verified", "partial_match"):
        final_conf = min(1.0, final_conf + 0.05)
        final_note = f"both sources agree ({cr_verdict}); " + final_note

    # Dual nothing: hard hallucination.
    if cr_verdict == "hallucinated" and oa_verdict == "hallucinated":
        final_verdict = "hallucinated"
        final_conf = 0.05
        final_note = "no matches in Crossref or OpenAlex"

    return final_verdict, round(final_conf, 3), final_note
