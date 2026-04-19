"""Reproducibly build the PDF fixtures used by the test suite.

Generates three files under tests/fixtures/:
  - real_paper.pdf        A synthetic paper listing real, well-known citations
                          (Vaswani "Attention Is All You Need", LeCun et al.
                          "Deep learning", etc.) so the verifier should return
                          `verified` for each.
  - hallucinated.pdf      A paper whose bibliography is entirely fabricated.
  - mixed.pdf             The real paper with two fabricated references
                          injected into the bibliography.

We deliberately build `real_paper.pdf` ourselves rather than downloading an
arXiv PDF; this keeps the test suite hermetic and free of network / licensing
concerns. The *citations listed inside it* are real, which is what matters
for verification.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.units import inch


FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


REAL_BODY = """
<b>Notes on Transformer Models</b><br/>
<i>An exposition for test fixtures.</i><br/><br/>

<b>Abstract.</b> This short note summarises several widely cited results in
modern machine learning. It exists only as a test fixture for the
citation-cleaner tool.<br/><br/>

<b>1. Introduction.</b> The Transformer architecture (Vaswani et al., 2017)
revolutionised sequence modelling. Earlier work established the foundations of
deep learning (LeCun, Bengio, and Hinton, 2015) and ImageNet-scale image
classification (Krizhevsky, Sutskever, and Hinton, 2012).<br/><br/>

<b>2. Discussion.</b> Later work on BERT (Devlin et al., 2019) showed that
Transformer encoders transfer well to many NLP tasks.
"""

REAL_REFS = [
    "Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., "
    "Kaiser, L., and Polosukhin, I. (2017). Attention is all you need. "
    "Advances in Neural Information Processing Systems 30.",
    "LeCun, Y., Bengio, Y., and Hinton, G. (2015). Deep learning. Nature, 521(7553), 436-444.",
    "Krizhevsky, A., Sutskever, I., and Hinton, G. E. (2012). ImageNet classification "
    "with deep convolutional neural networks. Advances in Neural Information "
    "Processing Systems 25.",
    "Devlin, J., Chang, M.-W., Lee, K., and Toutanova, K. (2019). BERT: Pre-training "
    "of deep bidirectional transformers for language understanding. "
    "Proceedings of NAACL-HLT 2019.",
    "He, K., Zhang, X., Ren, S., and Sun, J. (2016). Deep residual learning for "
    "image recognition. Proceedings of the IEEE Conference on Computer Vision "
    "and Pattern Recognition (CVPR).",
]

FAKE_REFS = [
    "Smith, J. and Jones, K. (2024). A unified theory of toaster cognition. "
    "Journal of Imaginary Sciences, 42(7), 999-1013.",
    "Doe, J., Roe, R., and Moe, M. (2023). Quantum entanglement of breakfast cereals. "
    "Proceedings of the International Conference on Nonexistent Results, 17-29.",
    "Alderaan, L. and Tatooine, O. (2022). Self-supervised learning on synthetic "
    "galaxies. Journal of Make-Believe AI, 8(2), 55-72.",
    "Fabricatus, M. (2024). Large language models dream of electric references. "
    "Hallucination Quarterly, 3(1), 1-9.",
    "Mirage, P. and Phantom, Q. (2025). Towards zero-shot citation manufacturing. "
    "Fictional Transactions on Scholarly Fraud, 11(4), 200-215.",
]


def _build_pdf(path: Path, body_html: str, references: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(path),
        pagesize=letter,
        leftMargin=1 * inch,
        rightMargin=1 * inch,
        topMargin=1 * inch,
        bottomMargin=1 * inch,
    )
    styles = getSampleStyleSheet()
    normal = styles["BodyText"]
    heading = ParagraphStyle(
        "refheading",
        parent=styles["Heading1"],
        spaceBefore=18,
        spaceAfter=12,
    )
    ref_style = ParagraphStyle(
        "ref",
        parent=styles["BodyText"],
        leftIndent=18,
        firstLineIndent=-18,
        spaceAfter=6,
    )

    story = [
        Paragraph(body_html, normal),
        Spacer(1, 0.2 * inch),
        Paragraph("References", heading),
    ]
    for ref in references:
        story.append(Paragraph(ref, ref_style))

    doc.build(story)


def build_real(path: Path | None = None) -> Path:
    path = path or (FIXTURES / "real_paper.pdf")
    _build_pdf(path, REAL_BODY, REAL_REFS)
    return path


def build_hallucinated(path: Path | None = None) -> Path:
    path = path or (FIXTURES / "hallucinated.pdf")
    fake_body = (
        "<b>An Entirely Fabricated Research Note</b><br/><br/>"
        "<b>Abstract.</b> This document exists solely to exercise the "
        "citation-cleaner tool against a bibliography full of invented "
        "references.<br/><br/>"
        "<b>1. Introduction.</b> Prior work on imaginary subjects "
        "(Smith and Jones, 2024; Doe et al., 2023) has laid the groundwork."
    )
    _build_pdf(path, fake_body, FAKE_REFS)
    return path


def build_mixed(path: Path | None = None) -> Path:
    path = path or (FIXTURES / "mixed.pdf")
    mixed_refs = REAL_REFS + FAKE_REFS[:2]
    _build_pdf(path, REAL_BODY, mixed_refs)
    return path


def build_all() -> None:
    build_real()
    build_hallucinated()
    build_mixed()
    print(f"built fixtures in {FIXTURES}")


if __name__ == "__main__":
    build_all()
