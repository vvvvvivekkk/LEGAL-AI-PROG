# Legal AI on Hugging Face Spaces (Docker Space, free CPU hardware).
#
# The Space holds only this file and README.md: the build downloads the code from
# GitHub, so "Factory rebuild" in the Space's settings picks up the latest push.
# Steps: docs/deploy.md.

ARG SRC_URL=https://github.com/vvvvvivekkk/LEGAL-AI-PROG/archive/refs/heads/main.tar.gz

# --- the source code ---------------------------------------------------------
FROM python:3.11-slim AS src
ARG SRC_URL
ADD ${SRC_URL} /tmp/src.tar.gz
RUN mkdir /src && tar -xzf /tmp/src.tar.gz -C /src --strip-components=1

# --- the web app, built to call the API on the same site under /api -----------
FROM node:20-slim AS web
COPY --from=src /src/web /web
WORKDIR /web
RUN npm ci --no-audit --no-fund && VITE_API_BASE=/api npm run build

# --- the backend, serving the API and the built web app ----------------------
FROM python:3.11-slim

# Spaces run the container as user 1000.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    LLM_PROVIDER=groq
WORKDIR /home/user/app

# CPU-only PyTorch first: the default wheel bundles GPU libraries a free Space has no use for.
ARG TORCH_INDEX=https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir --user torch --index-url ${TORCH_INDEX}
COPY --from=src --chown=user /src/requirements.txt ./requirements.txt
COPY --from=src --chown=user /src/lc/requirements.txt ./lc/requirements.txt
RUN pip install --no-cache-dir --user -r lc/requirements.txt

COPY --from=src --chown=user /src/src ./src
COPY --from=src --chown=user /src/lc ./lc
COPY --from=src --chown=user /src/experiments ./experiments
COPY --from=src --chown=user /src/data/demo_crime ./data/demo_crime
COPY --from=web --chown=user /web/dist ./web/dist

# Download the three local models into the image (about 2.5 GB), so a Space
# waking from sleep does not fetch them again. PRELOAD_MODELS=0 skips it.
ARG PRELOAD_MODELS=1
RUN if [ "$PRELOAD_MODELS" = "1" ]; then python -c "\
from lc.embeddings import default_embeddings; default_embeddings().embed_query('warm up'); \
from lc.retrieval import default_cross_encoder_compressor; default_cross_encoder_compressor(); \
from src.verification.nli import RobertaMNLI; RobertaMNLI().classify('a', 'a')"; fi

EXPOSE 7860
CMD ["uvicorn", "lc.hosted:app", "--host", "0.0.0.0", "--port", "7860"]
