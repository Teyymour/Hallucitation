"""Pytest configuration: ensure fixtures exist before tests run."""

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="session", autouse=True)
def _ensure_fixtures_built():
    needed = ["real_paper.pdf", "hallucinated.pdf", "mixed.pdf"]
    if not all((FIXTURES / n).exists() for n in needed):
        sys.path.insert(0, str(ROOT / "scripts"))
        import build_fixtures  # type: ignore
        build_fixtures.build_all()


@pytest.fixture()
def real_pdf():
    return FIXTURES / "real_paper.pdf"


@pytest.fixture()
def hallucinated_pdf():
    return FIXTURES / "hallucinated.pdf"


@pytest.fixture()
def mixed_pdf():
    return FIXTURES / "mixed.pdf"
