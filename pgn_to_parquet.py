from pathlib import Path

import chess.pgn
import pyarrow as pa
import pyarrow.parquet as pq


PGN_PATH = Path("data/raw/lichess_db_standard_rated_2026-05.pgn")
OUT_PATH = Path("data/parquet/moves.parquet")
FLUSH_EVERY = 100_000

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)


schema = pa.schema([
    ("game_id", pa.string()),
    ("ply", pa.int32()),
    ("move_number", pa.int32()),
    ("color", pa.string()),
    ("san", pa.string()),
    ("uci", pa.string()),
    ("fen_before", pa.string()),
    ("fen_after", pa.string()),
    ("result", pa.string()),
    ("white", pa.string()),
    ("black", pa.string()),
    ("white_elo", pa.int32()),
    ("black_elo", pa.int32()),
])


def safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def flush(writer, rows):
    if not rows:
        return

    table = pa.Table.from_pylist(rows, schema=schema)
    writer.write_table(table)
    rows.clear()


rows = []
games_done = 0

with open(PGN_PATH, encoding="utf-8", errors="replace") as f, pq.ParquetWriter(
    OUT_PATH,
    schema,
    compression="zstd",
) as writer:

    while True:
        game = chess.pgn.read_game(f)  # reads one game at a time
        if game is None:
            break

        games_done += 1

        game_id = game.headers.get("Site", f"game_{games_done}")
        result = game.headers.get("Result")
        white = game.headers.get("White")
        black = game.headers.get("Black")
        white_elo = safe_int(game.headers.get("WhiteElo"))
        black_elo = safe_int(game.headers.get("BlackElo"))

        board = game.board()

        for ply, move in enumerate(game.mainline_moves(), start=1):
            fen_before = board.fen()
            san = board.san(move)
            uci = move.uci()
            color = "white" if board.turn == chess.WHITE else "black"
            move_number = board.fullmove_number

            board.push(move)
            fen_after = board.fen()

            rows.append({
                "game_id": game_id,
                "ply": ply,
                "move_number": move_number,
                "color": color,
                "san": san,
                "uci": uci,
                "fen_before": fen_before,
                "fen_after": fen_after,
                "result": result,
                "white": white,
                "black": black,
                "white_elo": white_elo,
                "black_elo": black_elo,
            })

            if len(rows) >= FLUSH_EVERY:
                flush(writer, rows)
                print(f"games={games_done:,}")

    flush(writer, rows)

print("Done:", OUT_PATH)