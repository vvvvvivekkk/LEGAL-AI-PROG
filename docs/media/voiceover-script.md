# Narration of the Legal AI explainer (2:12)

The explainer video is narrated with a synthetic voice (the open Kokoro text-to-speech model, run offline). This is the text it speaks, scene by scene. Retrieval F1 is rounded for speech; the exact values are 0.333 and 0.417.

To record your own voice instead, read each line while its scene is on screen, then replace the audio track in any video editor and keep the music at about 30%.

| Time | Scene | Narration |
|---|---|---|
| 0:00–0:07 | Title | "This is Legal AI, our mini project from the Department of Artificial Intelligence, Anurag University." |
| 0:07–0:21 | 01 · The problem | "AI chatbots sound confident, but they sometimes invent the law. A US court sanctioned lawyers for citing cases a chatbot made up. Retrieval-augmented generation gives real passages, but nobody checks the final answer." |
| 0:21–0:29 | 02 · Our idea | "Our idea: check every sentence against its source before anyone sees it. And if the system isn't sure, it refuses." |
| 0:29–0:45 | 03 · How it works | "It works in six steps. Upload a document, and it's split by section. Ask a question, and the system searches. The AI answers with a citation on every sentence. Every claim is checked, and the answer is shown only if it scores at least 0.60." |
| 0:45–0:57 | 04 · Reading the law | "Here is the Indian Penal Code's chapter on theft. Each section becomes one chunk, keeps its heading, is turned into 384 numbers called an embedding, and is stored in LanceDB." |
| 0:57–1:08 | 05 · Searching | "We run two searches: meaning search for paraphrases, and keyword search for exact legal terms. We merge them, rerank the top 100, and give the best 12 to the AI." |
| 1:08–1:20 | 06 · Writing and checking | "Each claim must cite its passage. Then four checks run. V1: is the citation real? V2: does the passage support it? V3: is each fact supported? V4: does it hold up when asked again?" |
| 1:20–1:32 | 06 · Deciding | "V5 combines them into one Verification Confidence Score. At 0.60 or above, the answer is Verified, with a clickable proof. Below that, it refuses instead of guessing." |
| 1:32–1:48 | 07 · Live demo | "Here's the real app. I ask: if my landlord throws me out by force, what am I owed? Six months' rent. Verified, citing Section 7(a), though I never said eviction. Click the citation, and you see the exact clause and every check." |
| 1:48–2:04 | 08 · Results | "Our section-wise chunking raised retrieval F1 from 0.33 to 0.42. Of 28 planted false claims, none reached the user; without the gate, all 28 did. No wrong answer was shown as Verified. Its main limitation: it can refuse a correct answer." |
| 2:04–2:12 | Outro | "Legal AI. Retrieve, cite, verify. Thank you." |
