from citation_cleaner.extract import (
    extract_raw_citations,
    extract_text,
    find_references_section,
    split_references,
)


def test_find_references_section_basic():
    text = (
        "Intro body\n\nWe discuss things.\n\nReferences\n\n"
        "Smith, J. (2020). A paper. Journal, 1(1), 1.\n"
        "Jones, K. (2021). Another paper. Journal, 2(2), 2.\n"
    )
    block = find_references_section(text)
    assert block is not None
    assert "Smith" in block
    assert "Jones" in block


def test_find_references_section_none():
    assert find_references_section("just some body text") is None


def test_find_references_section_stops_at_appendix():
    text = (
        "Body\n\nReferences\n"
        "Smith, J. (2020). A paper. Journal.\n"
        "\nAppendix\n"
        "Extra things that are not refs\n"
    )
    block = find_references_section(text)
    assert block is not None
    assert "Smith" in block
    assert "Extra things" not in block


def test_split_references_numbered():
    block = (
        "[1] Smith, J. (2020). First paper. Journal, 1, 1.\n"
        "[2] Jones, K. (2021). Second paper. Journal, 2, 2.\n"
        "[3] Lee, L. (2022). Third paper. Journal, 3, 3."
    )
    refs = split_references(block)
    assert len(refs) == 3
    assert refs[0].startswith("Smith")


def test_split_references_author_year():
    block = (
        "Smith, J. (2020). First paper. Journal.\n"
        "Jones, K. (2021). Second paper. Journal.\n"
        "Lee, L. (2022). Third paper. Journal."
    )
    refs = split_references(block)
    assert len(refs) == 3


def test_extract_raw_citations_real_fixture(real_pdf):
    raws = extract_raw_citations(real_pdf)
    assert len(raws) == 5
    assert any("Vaswani" in r for r in raws)
    assert any("BERT" in r for r in raws)


def test_extract_text_missing(tmp_path):
    import pytest

    with pytest.raises(FileNotFoundError):
        extract_text(tmp_path / "missing.pdf")
