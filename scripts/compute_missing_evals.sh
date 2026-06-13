#!/bin/bash
set -euo pipefail

source .env

python computing_missing_evals.py \
  --input "$POSITIONS_OUT" \
  --out-dir "$SF18_EVALS_OUT" \
  --sf18-path "$SF18_PATH" \
  --depth 8 \
  --threads 1 \
  --hash-mb 256 \
  --flush-every 500