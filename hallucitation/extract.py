"""Extract the references section from a PDF and split it into raw citation strings."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import pdfplumber

# Common heading names for a bibliography section.
_REF_HEADINGS = [
    "references",
    "bibliography",
    "works cited",
    "literature cited",
    "citations",
]

# Anything that looks like a section heading that ENDS the references block.
_POST_REF_HEADINGS = [
    "appendix",
    "appendices",
    "acknowledgments",
    "acknowledgements",
    "author contributions",
    "supplementary",
    "supporting information",
]


def extract_text(pdf_path: str | Path) -> str:
    """Extract all text from a PDF as a single string.

    Uses ``x_tolerance=1`` instead of the pdfplumber default (3). Tighter-kerned
    PDFs (common in finance/stats journals) drop inter-word spaces at the
    default tolerance — "Stock Prices" → "StockPrices" — which breaks
    downstream title-matching against Crossref. A smaller tolerance preserves
    spaces without over-segmenting words.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)
    chunks: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=1) or ""
            chunks.append(text)
    return "\n".join(chunks)


def find_references_section(full_text: str) -> str | None:
    """Slice out the references block from full document text.

    Returns None if no references heading can be located.
    """
    if not full_text:
        return None

    lowered = full_text.lower()

    # Find the last occurrence of a references heading at line start (most robust for
    # papers that also contain the word "references" in running text).
    best_start = -1
    for heading in _REF_HEADINGS:
        # Match heading optionally preceded by a section number and followed by newline.
        pattern = re.compile(
            rf"(?im)^\s*(?:\d+\.?\s*)?{re.escape(heading)}\s*$",
        )
        for match in pattern.finditer(full_text):
            if match.start() > best_start:
                best_start = match.end()

    if best_start < 0:
        # Fallback: find the last simple occurrence of the word.
        for heading in _REF_HEADINGS:
            idx = lowered.rfind(heading)
            if idx > best_start:
                best_start = idx + len(heading)

    if best_start < 0:
        return None

    tail = full_text[best_start:]

    # Truncate at any post-references heading.
    lowered_tail = tail.lower()
    cut = len(tail)
    for heading in _POST_REF_HEADINGS:
        pattern = re.compile(rf"(?im)^\s*(?:\d+\.?\s*)?{re.escape(heading)}\s*$")
        m = pattern.search(tail)
        if m and m.start() < cut:
            cut = m.start()
        else:
            idx = lowered_tail.find("\n" + heading)
            if 0 <= idx < cut:
                cut = idx
    return tail[:cut].strip()


# Regexes used to detect the start of a new reference entry.
_NUMBERED_START = re.compile(r"^\s*(?:\[\d+\]|\(\d+\)|\d+\.)\s+")
_AUTHOR_YEAR_START = re.compile(
    r"^[A-Z][A-Za-z'`\-]+,\s*[A-Z]\.?"  # "Smith, J."
)


def split_references(ref_block: str) -> list[str]:
    """Split a reference block into individual raw citation strings.

    Handles both numbered references (``[1] ...``, ``1. ...``) and
    author-year style entries separated by blank lines or new author starts.
    """
    if not ref_block:
        return []

    lines = [ln.rstrip() for ln in ref_block.splitlines()]
    # Drop a leading line that is the heading itself, if present.
    while lines and lines[0].strip().lower() in _REF_HEADINGS:
        lines.pop(0)

    # Strategy 1: if we see numbered markers, split on them.
    if any(_NUMBERED_START.match(ln) for ln in lines if ln.strip()):
        return _split_numbered(lines)

    # Strategy 2: split on blank lines, then merge short continuations.
    return _split_by_blank_or_author(lines)


def _split_numbered(lines: list[str]) -> list[str]:
    entries: list[str] = []
    current: list[str] = []
    for ln in lines:
        if _NUMBERED_START.match(ln):
            if current:
                entries.append(" ".join(current).strip())
            # Strip the numeric marker itself.
            stripped = _NUMBERED_START.sub("", ln, count=1)
            current = [stripped]
        else:
            if ln.strip():
                current.append(ln.strip())
    if current:
        entries.append(" ".join(current).strip())
    return [e for e in entries if e]


def _split_by_blank_or_author(lines: list[str]) -> list[str]:
    entries: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            entries.append(" ".join(current).strip())
            current.clear()

    for ln in lines:
        if not ln.strip():
            flush()
            continue
        if current and _AUTHOR_YEAR_START.match(ln) and _looks_complete(current):
            flush()
        current.append(ln.strip())
    flush()
    return [e for e in entries if len(e) > 20]


def _looks_complete(current: list[str]) -> bool:
    """Heuristic: the running entry contains a year, so a new author start
    probably means a new reference."""
    joined = " ".join(current)
    return bool(re.search(r"(19|20)\d{2}", joined))


def extract_raw_citations(pdf_path: str | Path) -> list[str]:
    """Full pipeline: PDF path → list of raw reference strings."""
    text = extract_text(pdf_path)
    block = find_references_section(text)
    if not block:
        return []
    return split_references(block)
