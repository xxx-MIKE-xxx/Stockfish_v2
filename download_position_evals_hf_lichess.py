from pathlib import Path
from huggingface_hub import hf_hub_download, list_repo_files

REPO_ID = "Lichess/chess-position-evaluations"
OUTPUT_DIR = Path("data/raw")
data_prefix = "data/"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
all_files = list_repo_files(REPO_ID, repo_type="dataset")
parquet_files = sorted([f for f in all_files if f.startswith(data_prefix) and f.endswith(".parquet")])

downloaded_files = [str(f.relative_to(OUTPUT_DIR)) for f in Path(OUTPUT_DIR).rglob("*.parquet")]

print(f"downloaded {len(downloaded_files)} files - {len(parquet_files) - len(downloaded_files)} left")

for file in parquet_files:
    if file not in downloaded_files:
        hf_hub_download(
            repo_id=REPO_ID,
            filename=file,
            repo_type="dataset",
            local_dir=OUTPUT_DIR
        )

