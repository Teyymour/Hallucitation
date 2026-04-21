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

Requires **Python 3.10+**. If `python --version` reports anything older (e.g. on a default Anaconda install), create the venv explicitly with a newer interpreter: `python3.10 -m venv .venv` (or `python3.11`, `python3.12`).

## Quick start — CLI

```bash
# Check a PDF, print a Markdown report to stdout
python -m hallucitation check paper.pdf

# Write a Markdown report + JSON + annotated PDF
python -m hallucitation check paper.pdf \
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
streamlit run hallucitation/webapp.py
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

### 1. Tools used

- **Claude** (Anthropic): primarily Claude Opus 4.6 and Claude Opus 4.7, with some use of Claude Sonnet 4.6 for faster iteration on small edits

### 2. How AI was used

Claude wrote all code for this project in accordance with my specific instructions/prompts. I manually verified each file/component's functionality and iterated as needed. Claude also wrote this `README.md` (though I myself am writing this AI disclosure section). Additionally, while I wrote the written component myself, I initially did it in a word doc. Claude reformatted it for markdown (turning comma separated lists into bullet points, bolding where necessary, etc.), but did NOT change any of the wording/content that I wrote. I figured having it as an md file in the repo was appropriate rather than turning it in as a separate doc.

### 3. Key prompt examples

"I want to build a tool that takes a research pdf / academic paper and checks its references against crossref/openalex to detect hallucinated citations. Discuss with me the architecture."

"Write a function that for a given citation queries Crossref first, then OpenAlex, returning a confidence score based on DOI exact match, title fuzzy similarity, first-author match, and year proximity."

"Ok, let's build a test suite where we have different cases to reveal strengths and limitations with the tool. I want a bib with several all real citations, a bib with all hallucinated citations, and then a bib with some real and some hallucinated."

"Now that the cli is done and verified, let's make it webapp compatible by wrapping the cli in a streamlit ui."

"Create a brief readme that discusses the purpose of the project, setup instructions, output interpretation, and strengths/limitations."
