"""Streamlit web UI for hallucitation.

Run with:
    streamlit run hallucitation/webapp.py
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import streamlit as st

from hallucitation.extract import extract_raw_citations
from hallucitation.parse import parse_many
from hallucitation.report import to_markdown, to_json, annotate_pdf, count_verdicts
from hallucitation.verify import verify_citations_sync


def _run(pdf_path: Path) -> tuple[list, str, str]:
    raws = extract_raw_citations(pdf_path)
    citations = parse_many(raws)
    results = verify_citations_sync(citations)
    md = to_markdown(results, source=pdf_path.name)
    js = to_json(results)
    return results, md, js


def main() -> None:  # pragma: no cover - interactive
    st.set_page_config(
        page_title="Hallucitation",
        page_icon="*",
        layout="wide",
    )

    st.title("Hallucitation")
    st.caption("Find hallucinated citations in research PDFs.")

    with st.sidebar:
        st.header("About this tool")
        st.write(
            "Hallucitation extracts every reference from a research PDF, "
            "then verifies each one against Crossref and OpenAlex. "
            "References with no match in either database are flagged as "
            "possible hallucinations."
        )
        st.markdown(
            "- Source: [GitHub](https://github.com/Teyymour/Hallucitation)"
        )
        st.info(
            "Human-in-the-loop: this tool flags suspects. It does not delete, "
            "edit, or judge. Always review results yourself."
        )

    uploaded = st.file_uploader("Drop a research PDF here", type=["pdf"])

    if uploaded is None:
        st.info("Upload a PDF to begin.")
        return

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(uploaded.read())
        tmp_path = Path(tmp.name)

    progress = st.progress(0, text="Extracting references from PDF...")
    raws = extract_raw_citations(tmp_path)
    progress.progress(25, text=f"Found {len(raws)} raw references; parsing...")

    citations = parse_many(raws)
    progress.progress(50, text=f"Verifying {len(citations)} citations...")

    results = verify_citations_sync(citations)
    progress.progress(90, text="Building report...")

    md = to_markdown(results, source=uploaded.name)
    js = to_json(results)
    progress.progress(100, text="Done.")

    counts = count_verdicts(results)
    cols = st.columns(4)
    cols[0].metric("Verified", counts["verified"])
    cols[1].metric("Partial", counts["partial_match"])
    cols[2].metric("Mangled", counts["mangled"])
    cols[3].metric("Hallucinated", counts["hallucinated"])

    st.markdown(md)

    st.download_button(
        "Download JSON report",
        data=js,
        file_name=f"{uploaded.name}.hallucitation.json",
        mime="application/json",
    )
    st.download_button(
        "Download Markdown report",
        data=md,
        file_name=f"{uploaded.name}.hallucitation.md",
        mime="text/markdown",
    )

    annotated_path = tmp_path.with_suffix(".annotated.pdf")
    try:
        annotate_pdf(tmp_path, results, annotated_path)
        with open(annotated_path, "rb") as f:
            st.download_button(
                "Download annotated PDF",
                data=f.read(),
                file_name=f"{uploaded.name}.annotated.pdf",
                mime="application/pdf",
            )
    except Exception as exc:  # pragma: no cover
        st.warning(f"Could not build annotated PDF: {exc}")


if __name__ == "__main__":  # pragma: no cover
    main()
