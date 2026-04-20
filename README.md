# Hallucitation

**Find hallucinated citations in research PDFs.**

`hallucitation` takes a research PDF, extracts every entry in its references
section, and verifies each one against two public scholarly metadata
services — [Crossref][crossref] and [OpenAlex][openalex]. Citations with
no match in either database are flagged as possible **hallucinations** —
a known failure mode of large language models that fabricate plausible-
sounding references to non-existent papers.

The tool runs entirely locally. No data leaves your machine except for
requests to the two public APIs above, both of which only see public
bibliographic metadata.

[crossref]: https://www.crossref.org/
[openalex]: https://openalex.org/

## Why this exists

Recent studies have documented that LLMs fabricate references at
non-trivial rates. Walters & Wilder (2023) found 47% of ChatGPT-generated
references in a sample were entirely invented; Chelli et al. (2024)
reported similar rates in medical prompts and even documented
hallucinations in submitted and published manuscripts. As LLMs become
routine drafting assistants, a low-cost tool answering *"is this
reference real?"* is a straightforward public good.

## Install

```bash
git clone https://github.com/Teyymour/Hallucitation.git
cd Hallucitation
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .
```

Requires **Python 3.11+**.

## Quick start — CLI

```bash
# Check a PDF, print a Markdown report to stdout
python -m citation_cleaner.cli check paper.pdf

# Write a Markdown report + JSON + annotated PDF
python -m citation_cleaner.cli check paper.pdf \
    --output report.md \
    --json report.json \
    --annotate annotated.pdf
```

Exit codes:

| Code | Meaning |
| ---: | --- |
| `0` | All references verified. |
| `1` | One or more references flagged as hallucinated. |
| `2` | A parse error prevented the check from completing. |

Rate-limit the external APIs with `--rate N` (default 5 requests/sec).

## Quick start — web UI (Streamlit)

```bash
streamlit run citation_cleaner/webapp.py
```

A browser tab opens at `http://localhost:8501`. Drop a PDF onto the
uploader, wait for the progress bar, then review the per-citation report
underneath. Verified references show green; hallucinated ones show red
with a reason.

## How it works

1. **Extract.** `pdfplumber` + `pypdf` pull the references section from
   the PDF, handling multi-column layouts and common footnote styles.
2. **Parse.** Each reference is parsed into structured fields (authors,
   title, year, venue, DOI where available) with regex and heuristic
   fallbacks.
3. **Verify.** Each parsed reference is queried against **both**
   Crossref and OpenAlex. A reference is flagged as hallucinated only if
   **neither** source returns a match above the confidence threshold.
4. **Score.** Match confidence combines DOI exact-match (if present),
   title fuzzy similarity via `rapidfuzz`, first-author surname match,
   and year proximity.
5. **Report.** Produces Markdown (human), JSON (programmatic), and an
   annotated PDF with per-citation verdict badges for quick review.

## What it can and can't detect

**Can detect:**
- Completely fabricated references (the dominant LLM failure mode).
- References with nonsensical venue / year combinations.
- References where the parsed DOI does not resolve.

**Cannot detect (documented limitations):**
- Citations to real-but-retracted papers.
- Citations where the LLM returned a real paper's metadata for the wrong
  claim (the *citation content* is wrong, but the reference itself exists).
- References in languages with poor Crossref/OpenAlex indexing coverage.
- References to extremely obscure venues.

The tool is a **flagging assistant** — it shows you which references
warrant closer review. Every verdict is accompanied by the evidence so
you can audit the tool's reasoning yourself. It does not edit, delete,
or auto-rewrite your bibliography.

## Development

Run the test suite:

```bash
pytest
```

Tests are hermetic: all Crossref and OpenAlex calls in tests are
replayed from fixtures under `tests/fixtures/`, so the suite runs offline
and deterministically. Continuous integration (GitHub Actions) runs the
full suite on Python 3.11 and 3.12 on every push.

## License

MIT — see [`LICENSE`](./LICENSE).

## AI Use Disclosure

This README was generated with Claude Opus 4.7 (Anthropic) assistance.
The underlying implementation (CLI, Streamlit UI, Crossref + OpenAlex
verification, test suite, CI workflow) was also built with Claude
assistance, under my direction as the product owner. All design
decisions — choosing Crossref + OpenAlex as dual independent sources,
keeping the runtime free of any LLM dependencies to avoid using AI to
audit AI, scoping the tool to flag-only rather than auto-delete,
selecting the NIST AI Risk Management Framework as the primary ethical
grounding — are my own. This disclosure is provided in accordance with
the DSCI 305 AI Use Policy at Rice University (Spring 2026).
