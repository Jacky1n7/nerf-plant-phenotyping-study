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
