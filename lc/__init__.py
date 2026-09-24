"""LangChain port of the Legal AI backend (experiment).

Mirrors src/ stage by stage on LangChain primitives: document loaders, custom
TextSplitters, HuggingFaceEmbeddings, the langchain_community LanceDB store,
retrievers + a cross-encoder compressor, an LCEL generation chain, and the
V1-V6 verification chain wrapped as Runnables. The plain-Python version in
src/ is untouched; experiments/langchain_port/report.md compares the two.

Run the API with:  uvicorn lc.api:app   (or start.bat at the repo root)
"""
