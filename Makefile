.PHONY: setup convert evals clean

setup:
	cp -n .env.example .env || true
	chmod +x scripts/*.sh

convert:
	./scripts/convert_positions.sh

eval:
	./scripts/compute_missing_evals.sh

clean:
	rm -rf data/processed/possitions data/processed/sf18_evals