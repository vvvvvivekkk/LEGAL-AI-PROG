

def test_source_id_strips_surrounding_whitespace(tmp_path):
    """A filename with a leading space must not leak into chunk ids.

    The model cites ids copied from the prompt; an invisible leading space is
    not reproducible, so V1 would read every citation to that document as
    fabricated.
    """
    from src.ingestion.pipeline import ingest_file

    path = tmp_path / " 064-19 Non Disclosure Agreement 2019.txt"
    path.write_text("1. Remedies.\nThe Parties shall be entitled to injunctive relief.", encoding="utf-8")

    document = ingest_file(path)
    assert document.source_id == "064-19 Non Disclosure Agreement 2019"
    assert not document.source_id.startswith(" ")
