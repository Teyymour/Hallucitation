from citation_cleaner.parse import Citation, parse_citation, parse_many


def test_parse_style1_author_year():
    raw = (
        "Vaswani, A., Shazeer, N., Parmar, N. (2017). Attention is all you need. "
        "Advances in Neural Information Processing Systems 30."
    )
    c = parse_citation(raw)
    assert c.year == 2017
    assert c.title == "Attention is all you need"
    assert c.first_author_surname == "Vaswani"
    assert len(c.authors) >= 1


def test_parse_doi_extraction():
    raw = "Smith, J. (2020). A title. Journal. https://doi.org/10.1038/nature12345"
    c = parse_citation(raw)
    assert c.doi == "10.1038/nature12345"


def test_parse_doi_trailing_punctuation():
    raw = "Smith, J. (2020). A title. Journal. DOI: 10.1038/nature12345."
    c = parse_citation(raw)
    assert c.doi == "10.1038/nature12345"


def test_parse_arxiv_id():
    raw = "Smith, J. (2020). A title. arXiv:2301.12345"
    c = parse_citation(raw)
    assert c.arxiv_id == "2301.12345"


def test_parse_year_in_text():
    raw = "Smith J, Jones K. Title here. Nature. 2020;521:10."
    c = parse_citation(raw)
    assert c.year == 2020


def test_citation_to_dict_roundtrip():
    c = parse_citation("Smith, J. (2020). A title. Journal.")
    d = c.to_dict()
    assert d["year"] == 2020
    assert d["title"] == "A title"


def test_parse_many_skips_empty():
    out = parse_many(["", "   ", "Smith, J. (2020). A title. Journal."])
    assert len(out) == 1


def test_first_author_surname_from_initials_only():
    c = Citation(raw="x", authors=["Vaswani, A."])
    assert c.first_author_surname == "Vaswani"


def test_first_author_surname_spacefmt():
    c = Citation(raw="x", authors=["Ashish Vaswani"])
    assert c.first_author_surname == "Vaswani"
