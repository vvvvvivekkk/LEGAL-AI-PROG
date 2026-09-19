"""Ingestion page.

Upload a .txt or .pdf statute. On submit it runs the real phase-1 pipeline
(load -> clean -> structural parse -> SAC chunk) and the real phase-2
pipeline (embed -> append into the LanceDB hybrid index), then shows the
new chunks + a running total of what's indexed. No mocked data.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# Streamlit executes this file as a standalone script, so only its own
# directory lands on sys.path by default -- add the repo root too.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import streamlit as st

from src.chunking.sac import chunk_document
from src.indexing.build import DEFAULT_DB_PATH, append_chunks, open_table, table_exists
from src.ingestion.pipeline import ingest_file

st.title("Ingestion")
st.caption(
    "Upload a statute file. It runs the real ingestion + Summary-Augmented "
    "Chunking pipeline (src/ingestion, src/chunking), then embeds and "
    "appends the chunks into the LanceDB hybrid index (src/indexing)."
)


def _indexed_totals() -> tuple[int, int]:
    """(total chunks, total distinct documents) currently in the index."""
    if not table_exists(DEFAULT_DB_PATH):
        return 0, 0
    table = open_table(DEFAULT_DB_PATH)
    df = table.to_pandas()
    if df.empty:
        return 0, 0
    source_ids = df["metadata"].apply(lambda m: json.loads(m).get("source_id"))
    return len(df), source_ids.nunique()


total_chunks, total_docs = _indexed_totals()
st.metric("Indexed chunks", total_chunks)
st.metric("Indexed documents", total_docs)

uploaded = st.file_uploader("Statute file", type=["txt", "pdf"])

if uploaded is not None and st.button("Ingest and index", type="primary"):
    with st.spinner("Running ingestion, SAC chunking, embedding, and indexing..."):
        tmp_dir = Path(tempfile.mkdtemp())
        tmp_path = tmp_dir / uploaded.name
        tmp_path.write_bytes(uploaded.getvalue())

        try:
            document = ingest_file(tmp_path)
            chunk_records = chunk_document(document)
            chunk_dicts = [c.to_dict() for c in chunk_records]

            if not chunk_dicts:
                st.warning(
                    "No chunks were produced -- the file may not follow the "
                    "expected Act/Chapter/Section/Clause structure."
                )
            else:
                append_chunks(chunk_dicts, db_path=DEFAULT_DB_PATH)
                st.success(f"Indexed {len(chunk_dicts)} new chunks from '{uploaded.name}'.")

                rows = [
                    {
                        "chunk_id": c["chunk_id"],
                        "text": c["text"],
                        "contextual_summary": c["contextual_summary"],
                        **c["metadata"],
                    }
                    for c in chunk_dicts
                ]
                st.dataframe(rows, use_container_width=True)
        except NotImplementedError as exc:
            st.error(str(exc))
        except Exception as exc:  # noqa: BLE001 - surface embedding/indexing failures clearly
            st.error(f"Ingestion/indexing failed: {exc}")
        finally:
            tmp_path.unlink(missing_ok=True)
            tmp_dir.rmdir()

    st.rerun()
