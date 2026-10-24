#!/usr/bin/env bash
# One-time setup when the codespace is created (about 10 minutes): the Python
# packages, the web app built to call the API on the same address, and the models.
set -euo pipefail
cd "$(dirname "$0")/.."

# CPU-only PyTorch: the default wheel bundles GPU libraries a codespace has no use for.
python -m pip install --no-cache-dir torch --index-url "${TORCH_INDEX:-https://download.pytorch.org/whl/cpu}"
python -m pip install --no-cache-dir -r lc/requirements.txt

(cd web && npm ci --no-audit --no-fund && VITE_API_BASE=/api npm run build)

python -m lc.hosted || echo "Model download did not finish; the models will download when the app first needs them."
