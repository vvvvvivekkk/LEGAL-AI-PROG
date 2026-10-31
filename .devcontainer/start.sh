#!/usr/bin/env bash
# Runs every time the codespace starts: starts Legal AI on port 7860 in the
# background (log: /tmp/legal-ai.log) and makes the port public, so the link
# works for people without a GitHub login.
cd "$(dirname "$0")/.."

# A key saved in the repo-root .env (gitignored) survives restarts and takes
# priority over a Codespaces secret, so a stale secret cannot shadow it.
# Strip quotes and spaces a paste can leave around it.
if [ -f .env ]; then
  k=$(grep -E '^ANTHROPIC_API_KEY=' .env | tail -1 | cut -d= -f2- | tr -d "\"' \r")
  # A key pasted twice in a row: keep only the first copy.
  rest="${k#sk-ant-}"
  case "$rest" in *sk-ant-*) k="sk-ant-${rest%%sk-ant-*}";; esac
  [ -n "$k" ] && export ANTHROPIC_API_KEY="$k" && unset LLM_API_KEY
fi
[ -n "${ANTHROPIC_API_KEY:-}" ] && echo "Claude key in use: ${ANTHROPIC_API_KEY:0:11}...${ANTHROPIC_API_KEY: -4} (${#ANTHROPIC_API_KEY} characters)"

# LLM_PROVIDER comes from devcontainer.json, but a codespace keeps the value it was
# created with until it is rebuilt. Use Claude whenever its key is present.
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  export LLM_PROVIDER=claude
fi
echo "Language model provider: ${LLM_PROVIDER:-claude}"
if [ "${LLM_PROVIDER:-claude}" = "claude" ] && [ -z "${ANTHROPIC_API_KEY:-}${LLM_API_KEY:-}" ]; then
  echo "WARNING: no ANTHROPIC_API_KEY secret. Add it (docs/deploy.md, step 1), then stop and start the codespace."
fi

# Reranking 100 candidates is slow on the 2-core machine; 40 keeps answers fast.
export LEGAL_AI_RERANK_POOL="${LEGAL_AI_RERANK_POOL:-40}"
# The demo pack is Indian law, so uncited general answers should be too.
export LEGAL_AI_JURISDICTION="${LEGAL_AI_JURISDICTION:-India}"

if pgrep -f "uvicorn lc.hosted:app" >/dev/null; then
  echo "Legal AI is already running."
else
  setsid nohup python -m uvicorn lc.hosted:app --host 0.0.0.0 --port 7860 > /tmp/legal-ai.log 2>&1 < /dev/null &
  echo "Legal AI is starting on port 7860 (log: /tmp/legal-ai.log)."
fi

for _ in $(seq 1 90); do
  curl -sf http://localhost:7860/api/health >/dev/null && break
  sleep 2
done

# Health answers before the models finish loading; the first question would
# then wait for them. Wait for the warm-up to finish (up to 4 minutes).
echo "Loading the models (1-3 minutes)..."
for _ in $(seq 1 120); do
  grep -q "models loaded; ready\|warm-up failed" /tmp/legal-ai.log 2>/dev/null && break
  sleep 2
done
grep -q "models loaded; ready" /tmp/legal-ai.log 2>/dev/null && echo "Models loaded; Legal AI is ready."

if [ -n "${CODESPACE_NAME:-}" ]; then
  gh codespace ports visibility 7860:public -c "$CODESPACE_NAME" >/dev/null 2>&1 \
    && echo "Port 7860 is public: https://${CODESPACE_NAME}-7860.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}" \
    || echo "Make port 7860 public yourself: Ports tab, right-click 7860, Port visibility, Public."
fi
