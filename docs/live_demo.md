# Live demo: upload documents in front of the audience, then ask about them

Start from an empty index, upload five small files while everyone watches, and ask questions
that only those files can answer. This shows the full path: the document goes in, it is split
by section, and every answer cites a section from it.

The five files are in `data/demo_crime/`:

| File | What it is | Size |
|---|---|---|
| `ipc_theft.txt` | IPC Sections 378–382: theft | 5 sections |
| `ipc_murder_and_culpable_homicide.txt` | IPC Sections 299–311: murder, culpable homicide, death by negligence | 14 sections |
| `ipc_general_exceptions.txt` | IPC Sections 76–106: accident, child under seven, unsound mind, private defence | 31 sections |
| `crpc_arrest.txt` | CrPC Sections 41–60A: arrest | 23 sections |
| `ni_act_cheque_bounce.txt` | NI Act Sections 138–148: cheque bounce | 13 sections |

Total time: about 10 minutes.

## Before the audience arrives

1. Run `start.bat` and wait for the browser to open.
2. **Warm up the models.** Upload `ipc_theft.txt`, ask "What is the punishment for theft?" and
   wait for the answer. The first upload and the first question load the models and are slow
   (up to about 30 seconds); after that they are fast.
3. **Empty the index.** The web app has no delete button, so do it on disk: close the
   "Legal AI backend" window, delete the folder `data\lancedb_lc` (in cmd, from the project
   folder: `rmdir /s /q data\lancedb_lc`), and run `start.bat` again. Home should show
   0 documents and 0 chunks. Saved chats are in `data\chats_lc` and are not affected.
   (Do not use "Replace existing document" for this: Replace only swaps one document for a
   changed version of it.)
4. Open `data/demo_crime/` in File Explorer, and open `ipc_theft.txt` in Notepad.
5. Keep this page open on your phone or on paper, so you can copy the questions.

## Step 1: Show the document (1 minute)

Show `ipc_theft.txt` in Notepad and point at Section 379.

> "This is the actual text of the Indian Penal Code, sections 378 to 382, on theft. Section 379
> says theft is punished with up to three years, or fine, or both. Right now the system knows
> nothing; the index is empty."

Show Home: **0 documents, 0 chunks**.

## Step 2: Upload the five files (2 minutes)

On the Ingest page, upload the five files one by one and click **Ingest and index** each time.

> "Each file is split by Section and Clause, not by fixed-size pieces. Each piece gets an id
> like `ipc_theft::s379`, Section 379, which the AI must cite. Each piece is turned into an
> embedding for meaning search and added to the keyword index."

Point at the green "Indexed by legal structure" message and the chunk table after each upload.
Then show Home: **5 documents, 98 chunks**.

**Duplicate check:** upload `ipc_theft.txt` again.

> "The same file is refused, because we compare a SHA-256 fingerprint of the content. Nothing
> is stored twice. Replace is there for when the file has changed."

## Step 3: Ask about each document (5 minutes)

Use **New chat** for each question. On every Verified answer, **click the orange citation chip**
to open the proof: the quoted section, V1 citation exists, V2 entails, V3 fidelity.

| # | Question | Should answer | From |
|---|---|---|---|
| 1 | What is the punishment for theft? | **Verified**: up to three years, or fine, or both | `ipc_theft` s379 |
| 2 | If someone steals my mobile phone, how long can he be sent to jail? | **Verified**, though the question never says "theft" | `ipc_theft` s379 |
| 3 | What is the punishment for theft in a house? | **Verified**: up to seven years and fine | `ipc_theft` s380 |
| 4 | What is the punishment for murder? | **Verified**: death, or imprisonment for life, and fine | `ipc_murder_and_culpable_homicide` s302 |
| 5 | What is the punishment for causing death by negligence? | **Verified**: up to two years, or fine, or both | `ipc_murder_and_culpable_homicide` s304A |
| 6 | Can a child under seven years of age be punished for a crime? | **Verified**: no, nothing done by a child under seven is an offence | `ipc_general_exceptions` s82 |
| 7 | Is an act done by accident, without any criminal intention, an offence? | **Verified**: no, if done with proper care in a lawful act | `ipc_general_exceptions` s80 |
| 8 | How long can the police keep an arrested person in custody without the order of a Magistrate? | **Verified**: not more than twenty-four hours | `crpc_arrest` s57 |
| 9 | Must the police tell a person why he is being arrested without a warrant? | **Verified**: yes, immediately, with full particulars | `crpc_arrest` s50 |
| 10 | What is the punishment for dishonour of a cheque for insufficient funds? | **Verified**: up to two years, or fine up to twice the cheque amount, or both | `ni_act_cheque_bounce` s138 |

Say after question 2:

> "The question says 'steals my mobile phone', but the law says 'theft'. Meaning search found
> the right section anyway, and the proof shows the exact sentence from the file we uploaded."

## Step 4: Show what it refuses (1 minute)

| # | Question | Should happen |
|---|---|---|
| 11 | Why is the punishment for theft ten years of imprisonment? | **Abstained**, or corrected: the file says three years |
| 12 | What is the punishment for defamation? | **Abstained**: defamation was not uploaded |
| 13 | What is mens rea? | **General knowledge** (purple): not in the files, answered from the model's knowledge, clearly labelled, no citation |

> "Question 12 is real law, but we did not upload the defamation file, so the system refuses
> instead of answering from memory. It only vouches for what is in the uploaded documents."

## Step 5: Delete a document and ask again (1 minute)

Deleting is done through the backend's API page. Open http://localhost:8000/docs, find
**DELETE /documents/{source_id}**, click **Try it out**, type `ipc_theft`, and click **Execute**.
The response shows how many chunks were removed. Home goes to 4 documents. Then ask question 1
again in a new chat: **What is the punishment for theft?**

> "The same question now abstains, because the document it came from is gone. The answers come
> from the uploaded files, not from the AI's memory."

(Optional, to make the point stronger: upload `ipc_defamation.txt` now and ask question 12 again.
It should now be Verified, citing `ipc_defamation` s500.)

**After the demo:** upload the other 22 files from `data/demo_crime/` (the ones already in the
index will just show "Duplicate document", which is fine) to answer any question from
[`questions.md`](questions.md).

## If something goes wrong

| What happens | What to do or say |
|---|---|
| The first upload or question takes 20–30 seconds | The models are loading. Warm up before the audience arrives (see above). |
| A correct answer shows **Abstained** | Open the proof and say: "The checking model was not sure this sentence follows from the passage, so the score fell below 0.60. Our system is sometimes too strict, which is our main known limitation, but it never shows a wrong answer as Verified." Then ask the next question. |
| An answer cites a different section from the table | Open the proof and read the quoted passage; if it supports the answer, that is fine. |
| "Could not reach the Legal AI backend" | The backend window was closed. Run `start.bat` again. |
| The Groq API key or internet fails | Answers return an error (HTTP 503). Check `.env` and the connection, then restart the backend. |

More questions for every topic are in [`questions.md`](questions.md).
