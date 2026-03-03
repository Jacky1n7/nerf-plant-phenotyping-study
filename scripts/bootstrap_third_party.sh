#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
THIRD_PARTY_DIR="${ROOT_DIR}/third_party"

mkdir -p "${THIRD_PARTY_DIR}"

if [[ ! -d "${THIRD_PARTY_DIR}/instant-ngp/.git" ]]; then
  git clone https://github.com/NVlabs/instant-ngp.git "${THIRD_PARTY_DIR}/instant-ngp"
else
  echo "[skip] instant-ngp already exists."
fi

if [[ ! -d "${THIRD_PARTY_DIR}/pointnerf/.git" ]]; then
  git clone https://github.com/Xharlie/pointnerf.git "${THIRD_PARTY_DIR}/pointnerf"
else
  echo "[skip] pointnerf already exists."
fi

cat <<'EOF'
Third-party repos are ready.

Next:
1) Build instant-ngp following upstream docs.
2) Install Python deps: pip install -r requirements.txt
3) Run:
   make init DATASET=<dataset_id>
   make check DATASET=<dataset_id>
   make run DATASET=<dataset_id>
EOF
