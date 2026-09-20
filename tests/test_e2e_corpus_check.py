"""Rerunnable end-to-end check of the ingestion + retrieval path on two real
corpus files (one CUAD PDF, one MAUD merger agreement), using the hashing
FakeEmbedder so it runs offline in seconds. The real-model run is
`python scripts/e2e_corpus_check.py --limit 2`; its report lands in
experiments/. Skipped when the corpus has not been downloaded."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import e2e_corpus_check as e2e  # noqa: E402
from api.conftest import FakeEmbedder  # noqa: E402  (tests/ is a rootdir-relative package here)

CORPUS = REPO / "data" / "corpus" / "civil_law"
FILES = [
    CORPUS / "cuad/CUAD_v1/full_contract_pdf/Part_I/License_Agreements"
    / "CytodynInc_20200109_10-Q_EX-10.5_11941634_EX-10.5_License Agreement.pdf",
    CORPUS / "maud/contracts/contract_0.txt",
]

pytestmark = pytest.mark.skipif(not all(f.exists() for f in FILES), reason="civil-law corpus not downloaded")


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    db = tmp_path_factory.mktemp("lancedb")
    embedder = FakeEmbedder()
    ingested = [e2e.ingest_one(f, db, embedder) for f in FILES]
    queries = e2e.run_queries(db, embedder, e2e.QUERIES, k=3)
    return ingested, queries


def test_both_real_files_ingest_through_the_ingest_path(run):
    ingested, _ = run
    assert [r["status"] for r in ingested] == ["ok", "ok"], ingested
    assert all(r["chunks"] > 50 for r in ingested)
    # Contracts have no Act/Section hierarchy, so both must go through fallback chunking.
    assert {r["chunking"] for r in ingested} == {"fallback"}


def test_every_query_returns_all_three_variants_with_sources(run):
    _, queries = run
    assert len(queries) == len(e2e.QUERIES)
    for q in queries:
        for name in ("dense", "fts", "hybrid"):
            assert q["counts"][name] == 3, (q["query"], name, q["counts"])
            assert q["top"][name]["source_id"] in {"contract_0", FILES[0].stem}


def test_keyword_queries_are_lexically_grounded(run):
    """FTS is deterministic regardless of embedder: its top hit for a clause
    that literally exists in the corpus must contain the query's key terms."""
    _, queries = run
    by_query = {q["query"]: q for q in queries}
    assert {"assignment", "consent", "written"} <= set(by_query["assignment of the contract without prior written consent"]["top"]["fts"]["overlap"])
    assert {"governing", "jurisdiction", "law"} <= set(by_query["governing law and jurisdiction for disputes"]["top"]["fts"]["overlap"])
    assert {"breach", "cure", "termination"} <= set(by_query["termination of the agreement for material breach and cure period"]["top"]["fts"]["overlap"])


def test_report_is_written_and_lists_failures(run, tmp_path):
    ingested, queries = run
    ns = e2e.argparse.Namespace(corpus=CORPUS, db="tmp", k=3, _embedder=FakeEmbedder())
    path = e2e.write_report(tmp_path, ns, ingested, queries)
    results = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert path.exists()
    assert results["totals"]["indexed"] == 2 and results["totals"]["failed"] == []
    assert "## Retrieval" in path.read_text(encoding="utf-8")
