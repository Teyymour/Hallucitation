"""Command-line interface for citation-cleaner."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from citation_cleaner.extract import extract_raw_citations
from citation_cleaner.parse import parse_many
from citation_cleaner.report import to_markdown, write_json, annotate_pdf
from citation_cleaner.verify import verify_citations_sync

EXIT_OK = 0
EXIT_HALLUCINATED = 1
EXIT_PARSE_ERROR = 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="citation-cleaner",
        description="Find hallucinated citations in research PDFs.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="Check a PDF for hallucinated citations.")
    check.add_argument("pdf", type=Path, help="Path to the PDF to check.")
    check.add_argument(
        "--output", "-o", type=Path, default=None,
        help="Path for the Markdown report (default: stdout).",
    )
    check.add_argument(
        "--json", dest="json_path", type=Path, default=None,
        help="Path for the JSON report.",
    )
    check.add_argument(
        "--annotate", dest="annotate_path", type=Path, default=None,
        help="Path for an annotated PDF summarising hallucinations.",
    )
    check.add_argument(
        "--rate", type=float, default=5.0,
        help="Max requests per second to each API (default 5).",
    )
    check.add_argument("--verbose", "-v", action="store_true")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command != "check":
        parser.error("unknown command")
        return EXIT_PARSE_ERROR

    pdf_path: Path = args.pdf
    if not pdf_path.exists():
        print(f"error: no such file: {pdf_path}", file=sys.stderr)
        return EXIT_PARSE_ERROR

    if args.verbose:
        print(f"[info] extracting references from {pdf_path}", file=sys.stderr)

    try:
        raws = extract_raw_citations(pdf_path)
    except Exception as exc:  # pragma: no cover
        print(f"error: failed to read PDF: {exc}", file=sys.stderr)
        return EXIT_PARSE_ERROR

    if not raws:
        print(
            "error: no references section detected in PDF",
            file=sys.stderr,
        )
        return EXIT_PARSE_ERROR

    if args.verbose:
        print(f"[info] found {len(raws)} raw references", file=sys.stderr)

    citations = parse_many(raws)

    if args.verbose:
        print(
            f"[info] verifying {len(citations)} citations against Crossref + OpenAlex",
            file=sys.stderr,
        )

    results = verify_citations_sync(citations, rate=args.rate)

    md = to_markdown(results, source=str(pdf_path))
    if args.output:
        args.output.write_text(md)
        if args.verbose:
            print(f"[info] wrote Markdown report to {args.output}", file=sys.stderr)
    else:
        print(md)

    if args.json_path:
        write_json(results, args.json_path)
        if args.verbose:
            print(f"[info] wrote JSON report to {args.json_path}", file=sys.stderr)

    if args.annotate_path:
        annotate_pdf(pdf_path, results, args.annotate_path)
        if args.verbose:
            print(f"[info] wrote annotated PDF to {args.annotate_path}", file=sys.stderr)

    any_halluc = any(r.verdict == "hallucinated" for r in results)
    return EXIT_HALLUCINATED if any_halluc else EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
