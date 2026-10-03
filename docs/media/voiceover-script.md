# Voice-over script for the Legal AI explainer (2:12)

Read each part while its scene is on screen. Speak at a calm, normal pace; each part fits its time slot with a little room to spare. To add your voice: record it on your phone while the video plays, then combine the two in any video editor (CapCut, Clipchamp or the Windows Photos editor), and lower the music volume to about 30%.

| Time | Scene | Say |
|---|---|---|
| 0:00–0:07 | Title | "This is Legal AI, our mini project in the Department of Artificial Intelligence at Anurag University." |
| 0:07–0:21 | 01 · The problem | "AI chatbots sound confident, but sometimes they invent the law. In 2023, in Mata versus Avianca, a US court sanctioned lawyers who filed cases a chatbot had made up. The usual fix is retrieval-augmented generation, or RAG, which gives the AI real passages to answer from. But nobody checks the answer it finally writes." |
| 0:21–0:29 | 02 · Our idea | "Our idea is simple: check every sentence against its source before anyone sees it. Every claim must cite a passage, every claim is verified, and if the system isn't sure, it refuses." |
| 0:29–0:45 | 03 · How it works | "It works in six steps. You upload a document, and it is split by section. When you ask a question, the system searches the documents, the AI writes an answer with a citation on every sentence, every claim is verified, and the answer is shown only if its score is at least 0.60." |
| 0:45–0:57 | 04 · Reading the law | "Here is the Indian Penal Code's chapter on theft. Each section becomes one piece with its own id, like ipc_theft s379. Each piece carries its section's heading, is turned into 384 numbers called an embedding, and is stored in LanceDB." |
| 0:57–1:08 | 05 · Searching | "To answer a question, we run two searches. Meaning search finds paraphrases; keyword search finds exact legal terms. We merge them with Reciprocal Rank Fusion, rerank the top 100, and give only the best 12 passages to the AI." |
| 1:08–1:20 | 06 · Writing and checking | "The AI must write one claim per line, each ending with the passage it came from. Then four checks run. V1: is the citation real? V2: does an inference model agree the passage supports the claim? V3: is every small fact in it supported? V4 asks again and checks the claim comes back." |
| 1:20–1:32 | 06 · Deciding | "V5 combines these into one score, the Verification Confidence Score. If it's at least 0.60, the answer is Verified, with a clickable proof. If not, it abstains instead of guessing. General concept questions get a clearly labelled general-knowledge answer." |
| 1:32–1:48 | 07 · Live demo | "Here's the real app. I ask in plain words: if my landlord throws me out by force, how much am I owed? It answers six months' rent, Verified, with a score of 1.00, citing Section 7(a), even though I never said 'eviction'. Clicking the citation shows the exact clause and every check." |
| 1:48–2:04 | 08 · Results | "Our section-wise chunking raised retrieval F1 from 0.333 to 0.417. We planted 28 false claims: none reached the user, but with the gate removed, all 28 did. And in our end-to-end test, no wrong answer was ever shown as Verified. Our main limitation is that it's sometimes too strict, and refuses a correct answer." |
| 2:04–2:12 | Outro | "Legal AI: retrieve, cite, verify. Thank you." |
