<p align="center">
  <img src="assets/banner.svg" alt="NeRF Plant 3D Reconstruction and Phenotyping" width="100%" />
</p>

<p align="center">
  <a href="./README.md"><img src="assets/lang-zh.svg" alt="中文" width="180" height="36"/></a>
  <a href="./README.en.md"><img src="assets/lang-en.svg" alt="English" width="180" height="36"/></a>
</p>

# NeRF Plant 3D Reconstruction & Phenotyping

A research draft and reproducible manuscript workflow for crop 3D reconstruction and phenotypic trait extraction, aligned with:
- [NVlabs/instant-ngp](https://github.com/NVlabs/instant-ngp)
- [Xharlie/pointnerf](https://github.com/Xharlie/pointnerf)

## What This Repo Contains

- A polished Chinese LaTeX manuscript (`manuscript/nerf_plant_reconstruction.tex`)
- Compiled PDF output (`manuscript/nerf_plant_reconstruction.pdf`)
- Packaged archive for sharing (`manuscript_package.tar.gz`)
- Bilingual project documentation (Chinese default + this English page)

## Method Positioning

This draft maps the pipeline to practical open-source implementation details:
- **Instant-NGP branch**: hash-encoded NeRF for fast training/inference, COLMAP-to-`transforms.json` preprocessing, and density-field export.
- **Point-NeRF branch**: neural point representation for sparse-view and heavy-occlusion scenes, with point pruning/growing for geometry refinement.

## Engineering Setup (Ready to Run Once Data Arrives)

The repo now includes a runnable pipeline so you can drop a dataset and execute it end-to-end.

### 1) Environment

```bash
make bootstrap
pip install -r requirements.txt
```

Notes:
- `make bootstrap` clones `third_party/instant-ngp` and `third_party/pointnerf`.
- Install `COLMAP` first, and build `instant-ngp` following upstream docs.

### 2) Initialize Dataset

```bash
make init DATASET=maize_plant_01
```

This creates:
- `configs/datasets/maize_plant_01.toml`
- `data/raw/maize_plant_01/images/`

Put your captured images under `images/`.

### 3) Validate and Run

```bash
make check DATASET=maize_plant_01
make run DATASET=maize_plant_01
```

For command preview only:

```bash
make dry-run DATASET=maize_plant_01
```

### 4) Data Handoff Contract

```text
data/raw/<dataset_id>/
└── images/
    ├── 0001.jpg
    ├── 0002.jpg
    └── ...
```

Tune per-dataset settings in `configs/datasets/<dataset_id>.toml`:
- `aabb_scale`
- `ngp_steps`
- `marching_cubes_res`
- `vertical_axis`

## Experiment Tracking

The repo now includes built-in experiment tracking docs:
- Master log: [docs/EXPERIMENT_LOG.md](./docs/EXPERIMENT_LOG.md)
- Per-run template: [docs/EXPERIMENT_RUN_TEMPLATE.md](./docs/EXPERIMENT_RUN_TEMPLATE.md)

After each run, append parameter changes, commands, and key metrics to keep a reproducible trail.

## Project Structure

```text
.
├── assets/
│   ├── banner.svg
│   ├── lang-en.svg
│   └── lang-zh.svg
├── manuscript/
│   ├── nerf_plant_reconstruction.tex
│   ├── nerf_plant_reconstruction.pdf
│   ├── nerf_plant_reconstruction.aux
│   ├── nerf_plant_reconstruction.log
│   └── nerf_plant_reconstruction.out
├── configs/
│   ├── pipeline.toml
│   └── datasets/
├── scripts/
│   ├── bootstrap_third_party.sh
│   ├── pipeline.py
│   └── extract_traits.py
├── docs/
│   ├── EXPERIMENT_LOG.md
│   └── EXPERIMENT_RUN_TEMPLATE.md
├── src/
│   └── nerf_plant_pipeline/
├── Makefile
├── requirements.txt
├── README.md
├── README.en.md
└── manuscript_package.tar.gz
```

## Build the Manuscript

```bash
cd manuscript
/Library/TeX/texbin/xelatex -interaction=nonstopmode nerf_plant_reconstruction.tex
/Library/TeX/texbin/xelatex -interaction=nonstopmode nerf_plant_reconstruction.tex
```

## Notes on Upstream Projects

- `instant-ngp` is used as the main engineering baseline for real-time NeRF workflows.
- `pointnerf` is used as an enhancement reference for sparse-view robustness.
- Please follow each upstream repository license and usage restrictions (Point-NeRF is marked for non-commercial use in its repository).

## Author

- Xiaoran Li (李肖然)
