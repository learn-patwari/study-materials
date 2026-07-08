#!/usr/bin/env bash
# Validates every YAML manifest in this directory: parses as valid YAML
# (potentially multi-document, `---`-separated) and confirms each document
# carries the required top-level Kubernetes object keys. This sandbox has no
# live cluster or kubectl/helm binary, so this is the strongest verification
# available offline; if kubectl is available in your environment, prefer
# `kubectl apply --dry-run=client -f <file>` for real API-server-side schema
# validation on top of this.
set -euo pipefail
cd "$(dirname "$0")"

PY=python3
command -v python3.12 >/dev/null 2>&1 && PY=python3.12

for f in *.yaml; do
  "$PY" -c "
import sys, yaml
with open('$f') as fh:
    docs = list(yaml.safe_load_all(fh))
for i, d in enumerate(docs):
    missing = [k for k in ('apiVersion', 'kind', 'metadata') if k not in d]
    if missing:
        print(f'$f document {i}: missing required keys {missing}', file=sys.stderr)
        sys.exit(1)
print(f'$f: {len(docs)} document(s) OK')
"
done
echo "All manifests valid."
