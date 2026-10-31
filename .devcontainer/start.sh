#!/usr/bin/env bash
# Runs every time the codespace starts: starts Legal AI on port 7860 in the
# background (log: /tmp/legal-ai.log) and makes the port public, so the link
# works for people without a GitHub login.
cd "$(dirname "$0")/.."

# LLM_PROVIDER comes from devcontainer.json, but a codespace keeps the value it was
# created with until it is rebuilt. Use Claude whenever its key is present.
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  export LLM_PROVIDER=claude
fi
echo "Language model provider: ${LLM_PROVIDER:-claude}"
if [ "${LLM_PROVIDER:-claude}" = "claude" ] && [ -z "${ANTHROPIC_API_KEY:-}${LLM_API_KEY:-}" ]; then
  echo "WARNING: no ANTHROPIC_API_KEY secret. Add it (docs/deploy.md, step 1), then stop and start the codespace."
fi

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

if [ -n "${CODESPACE_NAME:-}" ]; then
  gh codespace ports visibility 7860:public -c "$CODESPACE_NAME" >/dev/null 2>&1 \
    && echo "Port 7860 is public: https://${CODESPACE_NAME}-7860.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}" \
    || echo "Make port 7860 public yourself: Ports tab, right-click 7860, Port visibility, Public."
fi
