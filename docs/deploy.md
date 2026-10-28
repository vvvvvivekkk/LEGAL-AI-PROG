# Host Legal AI online

The app needs about 4 GB of memory for its three local models (embeddings, reranker,
NLI), so free plans with 512 MB (Render, Koyeb) cannot run it. The free way that fits
is **GitHub Codespaces**: a cloud machine with 2 CPUs and 8 GB of memory, a public link,
and no card needed.

In both setups below the web app and the API run as one server: the pages at `/`, the
API under `/api`. On start the 27-file criminal-law demo pack (`data/demo_crime`) is
loaded by itself, so visitors can ask questions straight away.

## GitHub Codespaces (free)

**Free allowance (personal accounts):** 120 core-hours a month, about 60 hours on this
2-core machine, and 15 GB of storage. The app uses about 5 GB of disk.

### One-time setup

1. **Add your Claude API key as a secret.** Create a key at
   https://console.anthropic.com/settings/keys (the account needs credits under
   **Billing**). Then on GitHub: profile picture → **Settings** → **Codespaces** →
   **Secrets** → **New secret**.
   - **Name:** `ANTHROPIC_API_KEY`
   - **Value:** your Anthropic key (it starts with `sk-ant-`)
   - **Repository access:** select `LEGAL-AI-PROG`
2. **Give it longer before it sleeps (optional).** Same page, **Default idle timeout**: set
   240 minutes (the default is 30).
3. **Create the codespace.** On the repository page: **Code** → **Codespaces** → **⋯** →
   **New with options**. Machine type **2-core**, then **Create codespace**.
4. **Wait for the first setup (about 10–15 minutes).** The terminal shows it installing
   the Python packages, building the web app and downloading the models. When it ends:

   ```
   Legal AI is starting on port 7860 (log: /tmp/legal-ai.log).
   Port 7860 is public: https://<codespace-name>-7860.app.github.dev
   ```

5. **Check the port is public.** Open the **Ports** tab. Port 7860 ("Legal AI") should say
   **Public**. If it says Private: right-click it → **Port visibility** → **Public**.
   Private links ask visitors to sign in to GitHub.
6. **Open the link** in the Ports tab (the globe icon), or the address the terminal printed.
   Home should show 27 documents and 493 chunks (give it a minute after start). Ask
   "What is the punishment for theft?": it should be Verified, citing `ipc_theft` Section 379.

Send that link to your guide. It stays the same for this codespace.

### Before a demo, and after

- **Start it:** go to https://github.com/codespaces and open your codespace. The app starts
  by itself. Open the link once yourself to check it answers.
- **Stop it when done:** https://github.com/codespaces → **⋯** → **Stop codespace**. A running
  codespace uses your free hours even when nobody visits.
- **It stops by itself** after the idle timeout without activity in the codespace window,
  so start it shortly before the demo.
- **It is deleted after 30 days unused** (GitHub's default). Create a new one the same way;
  the link will change.

### After you change the code

In the codespace's terminal:

```bash
git pull
bash .devcontainer/setup.sh                 # only if packages or the web app changed
pkill -f "uvicorn lc.hosted:app"; bash .devcontainer/start.sh
```

### Good to know

| | |
|---|---|
| **Your documents** | Files uploaded on the Ingest page stay in the codespace until it is deleted. |
| **Chat history** | Chats are saved on the server and listed on the Ask page for everyone who opens the link, so visitors see each other's questions. |
| **Claude API cost** | Answers are written by Claude Haiku 5.5 (`claude-haiku-5-5`, $0.10 per million input tokens and $0.50 per million output tokens, about 0.2 cents a question). Every question anyone asks is billed to your Anthropic account, so share the link only with the people who need it, and set a monthly spend limit under **Limits** in the Anthropic console. |
| **Another model** | Add a Codespaces secret or variable `LLM_MODEL`, for example `claude-sonnet-5-5` for a stronger but costlier model ($2 / $10 per million tokens), then restart the codespace. |
| **API docs** | `https://<codespace-name>-7860.app.github.dev/api/docs` |
| **Legal status** | The demo pack is the IPC, CrPC and Evidence Act as they stood before 1 July 2024. It is a demo, not legal advice. |

### If something goes wrong

- **Ask says the language model is not configured:** the `ANTHROPIC_API_KEY` secret is missing,
  misspelled or not given access to this repository. Fix it, then stop and start the
  codespace so it reads the secret.
- **The link shows nothing:** in the terminal, `tail -f /tmp/legal-ai.log` shows what the app
  is doing. `bash .devcontainer/start.sh` starts it again.
- **Home shows 0 documents:** loading runs in the background for about a minute after start;
  reload. If it stays at 0, look for a `seeding … failed` line in the log.

## Docker (any host with about 4 GB of memory)

`deploy/huggingface/Dockerfile` builds the same app as one container listening on port
7860. It downloads the code from GitHub during the build, so it needs no other files, and
it downloads the models into the image. Set `ANTHROPIC_API_KEY` as a secret environment variable
on the host.

- **Hugging Face Spaces:** Docker Spaces now need a PRO plan. With one: create a Docker
  Space, upload `deploy/huggingface/Dockerfile` and `deploy/huggingface/README.md`, add the
  `ANTHROPIC_API_KEY` secret. **Factory rebuild** picks up new pushes.
- **Oracle Cloud Always Free** (a free server with 24 GB of memory; sign-up needs a card for
  identity checks), **Google Cloud Run** (free tier, needs billing set up), or any other
  container host:

  ```bash
  docker build -t legal-ai deploy/huggingface
  docker run -p 7860:7860 -e ANTHROPIC_API_KEY=your_key legal-ai
  ```

## How it works

`lc/hosted.py` serves the API under `/api` and the built React app at `/`, so the API's
routes never collide with page addresses such as `/ingest` and `/evaluation`. The web app is
built with `VITE_API_BASE=/api`. `python -m lc.hosted` downloads the models ahead of the
first start. Running locally is unchanged: `start.bat`, or `uvicorn lc.api:app` with
`npm run dev`.
