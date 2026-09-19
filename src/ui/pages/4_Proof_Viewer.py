"""Proof viewer / hallucination-check page (placeholder).

Requires phases 4-5 (citation-forced generation + the V1-V6 verification/
proof chain) to produce an answer and a Proof Object. Not implemented yet
-- this page states that plainly rather than faking a proof trace.
"""

from __future__ import annotations

import streamlit as st

st.title("Proof Viewer")
st.info(
    "Requires phases 4-5 (generation + verification), not yet implemented. "
    "See docs/phases/phase-04-generation.md and "
    "docs/phases/phase-05-verification-proof.md."
)
