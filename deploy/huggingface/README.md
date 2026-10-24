---
title: Legal AI
emoji: ⚖️
colorFrom: yellow
colorTo: red
sdk: docker
app_port: 7860
pinned: false
short_description: Legal question answering that verifies every claim
---

# Legal AI

Retrieval-augmented legal question answering with a gated verification chain: every
claim in an answer must cite a passage, every citation is checked, and the system
abstains when the Verification Confidence Score is below 0.60.

This Space is built from the code at
[github.com/vvvvvivekkk/LEGAL-AI-PROG](https://github.com/vvvvvivekkk/LEGAL-AI-PROG).
On start it loads a demo pack of 27 files of Indian criminal law (IPC, CrPC, Evidence
Act and NI Act as they stood before 1 July 2024).

**Demo only, not legal advice.** Uploaded files are kept only until the Space restarts.
