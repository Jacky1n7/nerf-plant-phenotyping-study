PYTHON ?= python
DATASET ?= maize_plant_01
CONFIG ?= configs/pipeline.toml

.PHONY: help bootstrap init check frames dry-run run traits

help:
	@echo "Targets:"
	@echo "  make bootstrap                # Clone instant-ngp and pointnerf"
	@echo "  make init DATASET=<name>      # Create dataset scaffold and config"
	@echo "  make check DATASET=<name>     # Validate tools and data paths"
	@echo "  make frames DATASET=<name>    # Extract frames from raw video only"
	@echo "  make dry-run DATASET=<name>   # Print commands without execution"
	@echo "  make run DATASET=<name>       # Execute full pipeline"
	@echo "  make traits DATASET=<name>    # Re-run trait extraction only"

bootstrap:
	bash scripts/bootstrap_third_party.sh

init:
	$(PYTHON) scripts/pipeline.py --config $(CONFIG) init-dataset --dataset $(DATASET)

check:
	$(PYTHON) scripts/pipeline.py --config $(CONFIG) check --dataset $(DATASET)

frames:
	$(PYTHON) scripts/pipeline.py --config $(CONFIG) run --dataset $(DATASET) --stages prepare_dirs,extract_video_frames

dry-run:
	$(PYTHON) scripts/pipeline.py --config $(CONFIG) run --dataset $(DATASET) --dry-run

run:
	$(PYTHON) scripts/pipeline.py --config $(CONFIG) run --dataset $(DATASET)

traits:
	$(PYTHON) scripts/extract_traits.py \
		--input outputs/$(DATASET)/mesh.ply \
		--output outputs/$(DATASET)/traits.csv \
		--vertical-axis z
