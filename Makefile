PYTHON ?= python
DATASET ?= maize_plant_01
CONFIG ?= configs/pipeline.toml
CONDA_ENV ?= nerf

.PHONY: help bootstrap init check frames dry-run run run-live view-gui traits dense-cloud

help:
	@echo "Targets:"
	@echo "  make bootstrap                # Clone instant-ngp and pointnerf"
	@echo "  make init DATASET=<name>      # Create dataset scaffold and config"
	@echo "  make check DATASET=<name>     # Validate tools and data paths"
	@echo "  make frames DATASET=<name>    # Extract frames from raw video only"
	@echo "  make dry-run DATASET=<name>   # Print commands without execution"
	@echo "  make run DATASET=<name>       # Execute full pipeline"
	@echo "  make run-live DATASET=<name>  # Execute with unbuffered live logs via conda"
	@echo "  make view-gui DATASET=<name>  # Launch instant-ngp GUI with Chinese terminal UI"
	@echo "  make traits DATASET=<name>    # Re-run trait extraction only"
	@echo "  make dense-cloud DATASET=<name> # Re-export dense point cloud from mesh"

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

run-live:
	conda run --no-capture-output -n $(CONDA_ENV) $(PYTHON) scripts/pipeline.py --config $(CONFIG) run --dataset $(DATASET)

view-gui:
	$(PYTHON) scripts/launch_ngp_gui.py --config $(CONFIG) --dataset $(DATASET)

traits:
	$(PYTHON) scripts/extract_traits.py \
		--input outputs/$(DATASET)/mesh.ply \
		--output outputs/$(DATASET)/traits.csv \
		--vertical-axis z

dense-cloud:
	$(PYTHON) scripts/pipeline.py --config $(CONFIG) run --dataset $(DATASET) --stages extract_dense_point_cloud
