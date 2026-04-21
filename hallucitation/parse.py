"""Parse raw reference strings into structured ``Citation`` records."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Any


# Soft hyphen artifact from PDFs: a word split across a line break is extracted
# as "<lower>- <lower>" (e.g. "Allo- cation"). Legitimate compound hyphens
# (e.g. "High-Frequency", "co-integration", "state-of-the-art") have NO space
# between the hyphen and the next word, so the lowercase-hyphen-space-lowercase
# pattern is a safe marker for line-break artifacts only.
_SOFT_HYPHEN_BREAK = re.compile(r"([a-z])- ([a-z])")


def _rejoin_soft_hyphens(text: str | None) -> str | None:
    if not text:
        return text
    return _SOFT_HYPHEN_BREAK.sub(r"\1\2", text)


_DOI_RE = re.compile(r"\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", re.IGNORECASE)
_ARXIV_RE = re.compile(
    r"\barXiv[:\s]*([0-9]{4}\.[0-9]{4,5}(?:v\d+)?)\b", re.IGNORECASE
)
_ARXIV_OLD_RE = re.compile(r"\barXiv[:\s]*([a-z\-]+/\d{7})\b", re.IGNORECASE)
_YEAR_RE = re.compile(r"\((19|20)\d{2}[a-z]?\)|\b(19|20)\d{2}[a-z]?\b")


@dataclass
class Citation:
    """Structured representation of one reference entry."""

    raw: str
    authors: list[str] = field(default_factory=list)
    title: str | None = None
    year: int | None = None
    journal: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def first_author_surname(self) -> str | None:
        if not self.authors:
            return None
        first = self.authors[0]
        # "Vaswani, Ashish" → "Vaswani"; "Ashish Vaswani" → "Vaswani"
        if "," in first:
            return first.split(",", 1)[0].strip()
        parts = first.strip().split()
        return parts[-1] if parts else None


def parse_citation(raw: str) -> Citation:
    """Parse one raw reference string into a Citation using regex heuristics."""
    text = " ".join(raw.split())  # collapse whitespace
    cit = Citation(raw=text)

    # --- DOI ---
    m = _DOI_RE.search(text)
    if m:
        # Strip trailing punctuation from DOI capture.
        cit.doi = m.group(1).rstrip(".,;)]")

    # --- arXiv ID ---
    m = _ARXIV_RE.search(text) or _ARXIV_OLD_RE.search(text)
    if m:
        cit.arxiv_id = m.group(1)

    # --- Year (prefer parenthesised) ---
    years = [
        int(match.group(0).strip("()")[:4])
        for match in _YEAR_RE.finditer(text)
    ]
    if years:
        cit.year = years[0]

    # --- Authors + title ---
    authors, title, journal = _split_authors_title_journal(text)
    cit.authors = authors
    cit.title = _rejoin_soft_hyphens(title)
    cit.journal = _rejoin_soft_hyphens(journal)
    return cit


def _split_authors_title_journal(
    text: str,
) -> tuple[list[str], str | None, str | None]:
    """Split a reference string into (authors, title, journal).

    Supports two dominant styles:
      1. "Smith, J., and Jones, K. (2020). Title of work. Journal Name, 12(3), 1-2."
      2. "Smith J, Jones K. Title of work. Journal Name. 2020;12(3):1-2."
    """
    # Style 1: year in parentheses separates authors from title.
    paren_year = re.search(r"\((19|20)\d{2}[a-z]?\)\.?", text)
    if paren_year:
        authors_str = text[: paren_year.start()].rstrip(" ,.")
        after = text[paren_year.end() :].strip(" .")
        authors = _parse_author_list(authors_str)
        title, journal = _split_title_journal(after)
        return authors, title, journal

    # Style 2: authors terminated by period before the title; year somewhere later.
    # Take everything up to the first period-space that is followed by a capital letter.
    m = re.match(r"(?P<authors>.+?\.)\s+(?P<rest>[A-Z“\"'].+)$", text)
    if m:
        authors_str = m.group("authors").rstrip(".")
        rest = m.group("rest")
        authors = _parse_author_list(authors_str)
        title, journal = _split_title_journal(rest)
        return authors, title, journal

    return [], None, None


def _parse_author_list(chunk: str) -> list[str]:
    """Return a list of author names from a raw chunk.

    Accepts forms like:
      "Smith, J., Jones, K., and Lee, M."
      "Smith J, Jones K, Lee M"
      "Smith, John and Jones, Katherine"
    """
    chunk = chunk.strip().strip(",.")
    if not chunk:
        return []
    # Normalise "and" / "&" separators to commas.
    chunk = re.sub(r"\s+&\s+", ", ", chunk)
    chunk = re.sub(r",?\s+and\s+", ", ", chunk, flags=re.IGNORECASE)

    # If the chunk contains commas that look like "Surname, Initial" pairs,
    # we need a smarter split: combine each (Surname, Initial) pair.
    parts = [p.strip() for p in chunk.split(",") if p.strip()]
    authors: list[str] = []
    i = 0
    while i < len(parts):
        p = parts[i]
        # Heuristic: if next part is a very short initials-only token, glue them.
        if (
            i + 1 < len(parts)
            and re.fullmatch(r"[A-Z]\.?(?:\s*[A-Z]\.?)*", parts[i + 1])
        ):
            authors.append(f"{p}, {parts[i + 1]}")
            i += 2
        else:
            authors.append(p)
            i += 1
    # Drop obvious non-author junk.
    return [a for a in authors if len(a) >= 2 and not re.fullmatch(r"\d+", a)]


def _split_title_journal(chunk: str) -> tuple[str | None, str | None]:
    """Split "Title of work. Journal Name, 12(3), 1-2." into (title, journal)."""
    chunk = chunk.strip()
    if not chunk:
        return None, None

    # If title is quoted, use the quoted span.
    m = re.search(r"[“\"'](?P<title>[^”\"']{3,})[”\"']", chunk)
    if m:
        title = m.group("title")
        rest = chunk[m.end() :].strip(" .,")
        journal = _first_sentence(rest) if rest else None
        return title, journal

    # Otherwise: split on ". " and take the first chunk as the title.
    pieces = re.split(r"\.\s+", chunk, maxsplit=2)
    if not pieces:
        return None, None
    title = pieces[0].strip().rstrip(".")
    journal = pieces[1].strip().rstrip(".") if len(pieces) > 1 else None
    # Journal cleanup: drop volume/issue/page tail.
    if journal:
        journal = re.split(r",\s*\d", journal, maxsplit=1)[0]
        journal = journal.strip().rstrip(",.")
    return title or None, journal or None


def _first_sentence(s: str) -> str:
    return re.split(r"\.\s", s, maxsplit=1)[0].strip().rstrip(".")


def parse_many(raws: list[str]) -> list[Citation]:
    return [parse_citation(r) for r in raws if r and r.strip()]
