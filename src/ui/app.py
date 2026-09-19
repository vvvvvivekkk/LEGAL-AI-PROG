"""Legal-RAG Streamlit app entry point.

Run with: streamlit run src/ui/app.py

Additional pages live in src/ui/pages/ (Streamlit's native multipage
convention). Each page calls the real pipeline code under src/ -- no mocks.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Streamlit executes this file as a standalone script, so only its own
# directory (src/ui) lands on sys.path by default -- add the repo root too,
# so `from src...` imports used by this app and its pages/ scripts work.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import streamlit as st

st.set_page_config(page_title="Legal-RAG", page_icon="⚖️")

st.title("Legal-RAG")
st.write(
    "Hallucination-resistant Legal RAG system. Full pipeline detail: "
    "`docs/architecture.md`."
)
st.markdown(
    """
Use the pages in the sidebar:

- **Ingestion** -- upload a `.txt`/`.pdf` statute, run it through the real
  ingestion + SAC chunking + embedding pipeline, and append it to the
  LanceDB hybrid index.
"""
)
