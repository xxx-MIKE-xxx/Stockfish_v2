#!/bin/bash
set -euo pipefail

source .env

python pgn_to_parquet.py \
  --pgn "$PGN_PATH" \
  --out-dir "$POSITIONS_OUT" \
  --workers "$WORKERS" \
  --batch-games 1000 \
  --flush-rows 100000 \
  --progress-every 1 \
  --live-progress-games 100 \
  --sf11-path "$SF11_PATH" \
  --disable-sf18