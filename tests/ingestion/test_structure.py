from src.ingestion.cleaning import clean_text
from src.ingestion.loaders import load_txt
from src.ingestion.pipeline import ingest_directory, ingest_file
from src.ingestion.structure import parse_document


def test_parses_known_structure_from_privacy_act(sample_data_dir):
    path = sample_data_dir / "data_privacy_act_2024.txt"
    document = parse_document(clean_text(load_txt(path)), source_id=path.stem)

    assert document.source_id == "data_privacy_act_2024"
    assert "DATA PRIVACY ACT" in document.title
    assert document.jurisdiction == "Republic of Veridia"
    assert document.enacted_date == "12 March 2024"

    # 4 chapters, in order.
    assert [c.number for c in document.chapters] == ["I", "II", "III", "IV"]
    assert document.chapters[0].name == "PRELIMINARY"

    # Chapter II holds sections 3 and 4.
    chapter_2 = document.chapters[1]
    assert [s.number for s in chapter_2.sections] == ["3", "4"]

    section_3 = chapter_2.sections[0]
    assert section_3.title == "Grounds for processing personal data"
    assert section_3.body_text.startswith("This section sets out the lawful grounds")
    assert [c.label for c in section_3.clauses] == ["a", "b", "c"]
    assert section_3.clauses[0].text.startswith("Processing is permitted where the data principal")


def test_numbered_subsections_parsed_as_clauses(sample_data_dir):
    path = sample_data_dir / "data_privacy_act_2024.txt"
    document = parse_document(clean_text(load_txt(path)), source_id=path.stem)

    section_1 = document.chapters[0].sections[0]
    assert section_1.number == "1"
    assert [c.label for c in section_1.clauses] == ["1", "2"]
    assert section_1.clauses[0].text.startswith("This Act may be called")


def test_section_without_clauses_keeps_single_body(sample_data_dir):
    path = sample_data_dir / "data_privacy_act_2024.txt"
    document = parse_document(clean_text(load_txt(path)), source_id=path.stem)

    # Section 9 (Grievance officer) is a single paragraph with no (n)/Clause markers.
    all_sections = [s for chapter in document.chapters for s in chapter.sections]
    section_9 = next(s for s in all_sections if s.number == "9")
    assert section_9.clauses == []
    assert section_9.body_text.startswith("This section requires every data fiduciary")


def test_ingest_file_matches_ingest_directory(sample_data_dir):
    documents = ingest_directory(sample_data_dir)
    assert len(documents) == 5

    single = ingest_file(sample_data_dir / "urban_tenancy_act_2019.txt")
    matching = next(d for d in documents if d.source_id == "urban_tenancy_act_2019")
    assert single.title == matching.title
    assert len(single.chapters) == len(matching.chapters)
