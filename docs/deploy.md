# Host Legal AI online (free, Hugging Face Spaces)

The whole app (web pages and API) runs as one Docker container on a free Hugging Face
Space: 2 CPUs and 16 GB of memory, enough for the three local models. It gets a public
address like `https://<your-username>-legal-ai.hf.space`.

On start it loads the 27-file criminal-law demo pack (`data/demo_crime`) and the models
by itself, so visitors can ask questions straight away.

## What you need

- A free Hugging Face account: https://huggingface.co/join
- Your Groq API key (the one in your local `.env`)

## Create the Space (one time, about 10 minutes plus the build)

1. On Hugging Face, click your profile picture → **New Space**.
2. Fill in:
   - **Space name:** `legal-ai`
   - **License:** any (for example MIT)
   - **SDK:** **Docker**, template **Blank**
   - **Hardware:** **CPU basic · Free**
   - **Visibility:** **Public**, so your guide can open it without an account
3. Click **Create Space**.
4. In the new Space, open **Files** → **Add file** → **Upload files** and upload these two
   files from this repository's `deploy/huggingface/` folder:
   - `Dockerfile`
   - `README.md` (replaces the one Hugging Face created)

   Click **Commit changes to main**. The build starts.
5. Open **Settings** → **Variables and secrets** → **New secret**:
   - **Name:** `GROQ_API_KEY`
   - **Value:** your Groq key

   Never put the key in a file; a secret is hidden and only the running app can read it.
6. Open the **Logs** tab. The first build takes about 10–20 minutes: it installs the
   Python packages and downloads the models (about 2.5 GB). When the app starts you will see:

   ```
   INFO:     seeded 27 files: 27 documents, 493 chunks
   INFO:     models loaded; ready
   ```

7. Open the **App** tab, or the direct address `https://<your-username>-legal-ai.hf.space`.
   Home should show 27 documents and 493 chunks. Ask "What is the punishment for theft?":
   it should be Verified, citing `ipc_theft` Section 379.

## After you change the code

Push to `main` on GitHub as usual, then in the Space open **Settings** → **Factory
rebuild**. The build downloads the latest code from GitHub; nothing needs uploading again.

## Good to know

| | |
|---|---|
| **Sleep** | A free Space sleeps after about 48 hours with no visitors. The next visit wakes it, which takes a minute or two. Open it yourself shortly before a demo. |
| **Uploads** | Files uploaded on the Ingest page stay only until the Space restarts or rebuilds; the demo pack is always loaded again on start. |
| **Chat history** | Chats are saved on the server and listed on the Ask page for everyone who opens the Space, so visitors see each other's questions. They are cleared when the Space restarts. |
| **Groq quota** | Every question anyone asks uses your free Groq quota. Share the link with the people who need it rather than publicly. |
| **API docs** | The API is under `/api`, so the endpoint page is `https://<your-username>-legal-ai.hf.space/api/docs`. |
| **Legal status** | The demo pack is the IPC, CrPC and Evidence Act as they stood before 1 July 2024. The Space's page says it is a demo, not legal advice. |

## If something goes wrong

- **Build error:** the **Logs** tab names the failing step. A temporary network error usually passes on **Factory rebuild**.
- **Ask says the language model is not configured:** the `GROQ_API_KEY` secret is missing or misspelled. Fix it in **Settings**; the Space restarts by itself.
- **Home shows 0 documents:** wait a minute after start (seeding runs in the background), then reload. If it stays at 0, look for a `seeding … failed` line in the logs.

## How it works

`lc/hosted.py` serves the API under `/api` and the built React app at `/`, so the API's
routes never collide with page addresses such as `/ingest` and `/evaluation`. The
Dockerfile builds the web app with `VITE_API_BASE=/api`. Running locally is unchanged:
`start.bat`, or `uvicorn lc.api:app` with `npm run dev`.
