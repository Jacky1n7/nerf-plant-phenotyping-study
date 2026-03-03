<p align="center">
  <img src="assets/banner.svg" alt="NeRF Plant 3D Reconstruction and Phenotyping" width="100%" />
</p>

<p align="center">
  <a href="./README.md"><img src="assets/lang-zh.svg" alt="中文" width="180" height="36"/></a>
  <a href="./README.en.md"><img src="assets/lang-en.svg" alt="English" width="180" height="36"/></a>
</p>

# NeRF Plant 3D Reconstruction & Phenotyping

This repo contains:
- Manuscript files (`manuscript/`)
- A runnable pipeline (`configs/`, `scripts/`, `Makefile`)

Primary workflow: provide a 360 plant video, extract frames, then run reconstruction.

## Setup

1. Install `COLMAP`
2. Install `ffmpeg`
3. Pull third-party repos and Python deps

```bash
make bootstrap
pip install -r requirements.txt
```

## Dataset Layout (Video First)

```bash
make init DATASET=maize_plant_01
```

This creates:

```text
data/raw/maize_plant_01/
├── video/
└── images/
```

Default input video path:

```text
data/raw/<dataset_id>/video/capture.mp4
```

If your filename differs, update `dataset.video_input` in `configs/datasets/<dataset_id>.toml`.

## Commands

```bash
make check DATASET=maize_plant_01    # validate env + paths
make frames DATASET=maize_plant_01   # extract video frames only
make run DATASET=maize_plant_01      # full pipeline
make dry-run DATASET=maize_plant_01  # print commands only
```

## Key Config Fields

File: `configs/datasets/<dataset_id>.toml`

- `[video]`: `fps`, `start_time`, `end_time`, `max_frames`, `resize_width`, `resize_height`, `overwrite`
- `[reconstruction]`: `aabb_scale`, `ngp_steps`, `marching_cubes_res`
- `[traits]`: `vertical_axis`

## Outputs

- `outputs/runs/<dataset_id>/pipeline.log`
- `outputs/<dataset_id>/instant-ngp.msgpack`
- `outputs/<dataset_id>/mesh.ply`
- `outputs/<dataset_id>/traits.csv`

## Experiment Tracking

- [docs/EXPERIMENT_LOG.md](./docs/EXPERIMENT_LOG.md)
- [docs/EXPERIMENT_RUN_TEMPLATE.md](./docs/EXPERIMENT_RUN_TEMPLATE.md)
