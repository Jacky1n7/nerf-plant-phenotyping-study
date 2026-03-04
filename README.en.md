<p align="center">
  <img src="assets/banner.svg" alt="NeRF Plant 3D Reconstruction and Phenotyping" width="100%" />
</p>

<p align="center">
  <a href="./README.md"><img src="assets/lang-zh.svg" alt="中文" width="180" height="36"/></a>
  <a href="./README.en.md"><img src="assets/lang-en.svg" alt="English" width="180" height="36"/></a>
</p>

# NeRF Plant 3D Reconstruction & Phenotyping

This repository contains:
- manuscript files (`manuscript/`)
- a runnable pipeline (`configs/`, `scripts/`, `Makefile`)

Core goal: take a 360-degree plant video and produce:
- an instant-ngp snapshot
- a mesh
- basic phenotypic traits

## Current Status (March 4, 2026)

`maize_plant_01` has been run repeatedly with updated videos, and the workflow is now stable for:
- frame extraction from 360-degree video
- COLMAP + transforms generation
- instant-ngp training and mesh export

Note: current `traits.csv` values are still relative reconstruction units before physical scale calibration.

## Result Preview (Updated Video)

| View 1 | View 2 |
| --- | --- |
| ![maize_plant_01 result view 1](assets/results/maize_plant_01_result_view_01.png) | ![maize_plant_01 result view 2](assets/results/maize_plant_01_result_view_02.png) |

## Recommended Conda Setup

Use Python 3.11:

```bash
conda create -n nerf python=3.11 -y
conda activate nerf
pip install -r requirements.txt
make bootstrap
```

Required system tools:
- `COLMAP`
- `ffmpeg`

For instant-ngp GUI (`--gui`) on Linux:

```bash
conda install -n nerf -c conda-forge \
  libgl-devel libglu xorg-libx11 xorg-libxext \
  xorg-libxrandr xorg-libxi xorg-libxinerama xorg-libxcursor
```

## Dataset Layout (Video First)

```bash
make init DATASET=maize_plant_01
```

Creates:

```text
data/raw/maize_plant_01/
├── video/
└── images/
```

Default video path:

```text
data/raw/<dataset_id>/video/capture.mp4
```

If your video name differs, edit `dataset.video_input` in `configs/datasets/<dataset_id>.toml`.

## Pipeline Commands

Recommended full rerun:

```bash
make check DATASET=maize_plant_01
make run DATASET=maize_plant_01
```

Run pose/transforms stages only:

```bash
python scripts/pipeline.py \
  --config configs/pipeline.toml run \
  --dataset maize_plant_01 \
  --stages colmap,colmap_to_text,transforms
```

Resume from training stage only:

```bash
python scripts/pipeline.py \
  --config configs/pipeline.toml run \
  --dataset maize_plant_01 \
  --stages train_instant_ngp,export_geometry,extract_traits
```

`colmap` stage now clears stale `colmap/`, `colmap_text/`, and `transforms.json` automatically before reconstruction, which prevents mismatched-frame errors after replacing videos.

## Viewing Results

View traits:

```bash
cat outputs/maize_plant_01/traits.csv
```

Open NeRF viewer:

```bash
python third_party/instant-ngp/scripts/run.py \
  --scene data/processed/maize_plant_01 \
  --load_snapshot outputs/maize_plant_01/instant-ngp.msgpack \
  --gui
```

Open mesh:

```bash
meshlab outputs/maize_plant_01/mesh.ply
```

## Common Issues

1. `ModuleNotFoundError: No module named 'pyngp'`
- Build the instant-ngp Python binding and re-run `make check`.

2. `No training images were found for NeRF training`
- Fix `transforms.json` paths:

```bash
python scripts/fix_transforms_paths.py \
  --transforms data/processed/<dataset_id>/transforms.json \
  --project-root .
```

3. `NGP was built without GUI support`
- Rebuild instant-ngp with GUI enabled and OpenGL/X11 dependencies installed.

4. Progress bar seems frozen under `conda run`
- Run directly in activated env (`python ...`) for proper `tqdm` rendering.

5. `imread(...frame_xxxxxx.jpg)` + OpenCV `!_src.empty()` in `colmap2nerf.py`
- Cause: stale COLMAP text index does not match current extracted frames.
- Fix: re-run `colmap,colmap_to_text,transforms` (or full `make run`).

## Outputs

- `outputs/runs/<dataset_id>/pipeline.log`
- `outputs/<dataset_id>/instant-ngp.msgpack`
- `outputs/<dataset_id>/mesh.ply`
- `outputs/<dataset_id>/traits.csv`

## Experiment Tracking

- [docs/EXPERIMENT_LOG.md](./docs/EXPERIMENT_LOG.md)
- [docs/EXPERIMENT_RUN_TEMPLATE.md](./docs/EXPERIMENT_RUN_TEMPLATE.md)
- [docs/COMMANDS.md](./docs/COMMANDS.md) (Chinese command cheat sheet)
