# Stockfish_v2

Stockfish_v2 is a chess position dataset and modeling pipeline for predicting human game WDL outcomes from sequences of positions.

The goal is to train a time-sequence neural network that predicts WDL probabilities as an offset from vanilla Stockfish WDL, using human-context features such as clock time, rating, game metadata, and Stockfish position breakdowns.

## Project idea

Vanilla Stockfish evaluates a board position assuming near-optimal play. This project adds human-game context:

* player rating
* opponent rating
* clock time
* time spent on move
* game time control
* UTC date/time metadata
* Lichess metadata
* Stockfish 11 static position breakdown
* Stockfish 18 WDL / centipawn evals
* sequence of previous positions

The final model is intended to predict:

```text
P(win), P(draw), P(loss)
```

for the active player in real human games.

## Data pipeline

The pipeline has three main stages:

```text
1. PGN -> position parquet
2. Join existing ready evals with positions
3. Compute missing Stockfish 18 evals
```

## Repository structure

```text
stockfish_v2/
  data/
    raw/
      pgn/
    processed/
      possitions/
      sf18_evals/
      joined/
  scripts/
  stockfish-11-mac/
  stockfish-18/
  pgn_to_parquet.py
  computing_missing_evals.py
  README.md
```

## Setup

Create and activate the virtual environment:

```bash
python -m venv stockfish-v2
source stockfish-v2/bin/activate
pip install -r requirements.txt
```

Build Stockfish 11 with the custom `evaljson` command:

```bash
cd stockfish-11-mac/src
make clean
make build ARCH=x86-64-modern
cd ../../
```

Build Stockfish 18:

```bash
cd stockfish-18/src
make clean
make -j build ARCH=apple-silicon
cd ../../
```

## 1. Download Lichess PGN

Place the raw PGN file here:

```text
data/raw/pgn/lichess_db_standard_rated_2026-05.pgn
```

Example:

```bash
mkdir -p data/raw/pgn

# replace URL if using a different month
wget -O data/raw/pgn/lichess_db_standard_rated_2026-05.pgn.zst \
  https://database.lichess.org/standard/lichess_db_standard_rated_2026-05.pgn.zst

unzstd data/raw/pgn/lichess_db_standard_rated_2026-05.pgn.zst
```

## 2. Convert PGN to position parquet

This creates one row per position / ply.

```bash
python pgn_to_parquet.py \
  --pgn data/raw/pgn/lichess_db_standard_rated_2026-05.pgn \
  --out-dir data/processed/possitions \
  --workers 6 \
  --batch-games 1000 \
  --flush-rows 100000 \
  --progress-every 1 \
  --live-progress-games 100 \
  --sf11-path stockfish-11-mac/src/stockfish \
  --disable-sf18
```

The conversion is resumable. If interrupted, rerun the same command without deleting the output directory.

Use `--force-restart` only when intentionally starting from scratch.

## Position parquet format

Each row represents one board position before a move.

Important columns:

```text
game_id
ply
game_ply_count
position_key
fen_before
move_uci
color_to_move
time_left_perc
opp_time_left_perc
time_spent_s
active_elo
opp_elo
elo_diff
base_rating_type
result
game_result_numeric
active_player_wdl
stockfish11 breakdown fields
stockfish18 fields
```

`fen_before` is the exact FEN before the move.

`position_key` is a normalized FEN key used for joining evaluations. It removes move counters so repeated equivalent positions can share the same engine eval.

`game_ply_count` is the total number of plies in the game and is useful for sequence modeling.

## 3. Download ready Stockfish 18 evaluations

Place externally computed evaluation files in:

```text
data/processed/sf18_evals/
```

Expected join key:

```text
position_key
```

Expected eval columns:

```text
stockfish18_score_cp_white
stockfish18_wdl_white_win
stockfish18_wdl_draw
stockfish18_wdl_black_win
stockfish18_depth
```

## 4. Compute missing Stockfish 18 evaluations

For positions that do not already have ready evaluations:

```bash
python computing_missing_evals.py \
  --input data/processed/possitions \
  --out-dir data/processed/sf18_evals \
  --sf18-path stockfish-18/src/stockfish \
  --depth 8 \
  --threads 1 \
  --hash-mb 256 \
  --flush-every 500
```

This step is also resumable and skips already-computed positions.

## 5. Join positions with evaluations

After both position parquet and SF18 eval parquet exist, join them by:

```text
position_key
```

The joined dataset should be written to:

```text
data/processed/joined/
```

## Sequence modeling

Training should use sequences grouped by:

```text
game_id
```

and ordered by:

```text
ply
```

Recommended sequence setup:

```text
seq_len = 32
stride = 4
target = active_player_wdl at target ply
```

Example training sample:

```text
positions from ply 1-32 -> predict active_player_wdl at ply 32
positions from ply 5-36 -> predict active_player_wdl at ply 36
positions from ply 9-40 -> predict active_player_wdl at ply 40
```

Do not include future positions when predicting the current position outcome.

## Notes

Stockfish 11 static breakdown is not available for positions where the side to move is in check. These rows should keep SF11 breakdown fields as null.

Stockfish 18 search evaluation can still be computed for checked positions.

Recommended behavior:

```text
normal positions: SF11 breakdown + SF18 eval
checked positions: null SF11 breakdown + SF18 eval
```

## Goal

The final model should learn human-specific WDL probabilities by combining:

```text
Stockfish position quality
time pressure
rating strength
game phase
historical position sequence
metadata
```

This should allow the model to outperform raw deep Stockfish WDL when predicting actual human game outcomes.
