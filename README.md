<p align="center">
  <img src="assets/banner.svg" alt="NeRF 植物三维重建与表型提取" width="100%" />
</p>

<p align="center">
  <a href="./README.md"><img src="assets/lang-zh.svg" alt="中文" width="180" height="36"/></a>
  <a href="./README.en.md"><img src="assets/lang-en.svg" alt="English" width="180" height="36"/></a>
</p>

# NeRF植物三维重建与表型提取

这是一个面向作物三维重建与表型参数提取的研究草稿仓库，并与以下开源项目做了工程对齐：
- [NVlabs/instant-ngp](https://github.com/NVlabs/instant-ngp)
- [Xharlie/pointnerf](https://github.com/Xharlie/pointnerf)

## 仓库内容

- 完整润色后的中文 LaTeX 草稿（`manuscript/nerf_plant_reconstruction.tex`）
- 编译后的 PDF（`manuscript/nerf_plant_reconstruction.pdf`）
- 便于分享的打包文件（`manuscript_package.tar.gz`）
- 中英文双语说明文档（本页 + 英文页）

## 方法定位（与开源项目关系）

草稿中的流程已补充为可复现的工程路径：
- **Instant-NGP分支**：以哈希编码 NeRF 为主干，包含 COLMAP 到 `transforms.json` 的预处理与密度场几何导出。
- **Point-NeRF分支**：以神经点表示增强稀疏视角/强遮挡场景，通过点剪枝与增殖提高局部几何稳定性。

## 工程落地（数据就绪即可运行）

仓库已补充可执行流水线，目标是你把采集数据放进来后即可直接运行。

### 1) 环境准备

```bash
make bootstrap
pip install -r requirements.txt
```

说明：
- `make bootstrap` 会克隆 `third_party/instant-ngp` 与 `third_party/pointnerf`。
- 需要提前安装 `COLMAP`，并按 `instant-ngp` 官方说明完成编译。

### 2) 初始化数据集

```bash
make init DATASET=maize_plant_01
```

执行后会创建：
- `configs/datasets/maize_plant_01.toml`
- `data/raw/maize_plant_01/images/`

你只需要把采集图像放到 `images/` 目录。

### 3) 检查并运行

```bash
make check DATASET=maize_plant_01
make run DATASET=maize_plant_01
```

如果只想先看执行计划，不实际运行：

```bash
make dry-run DATASET=maize_plant_01
```

### 4) 数据交付规范（给我数据时按这个结构）

```text
data/raw/<dataset_id>/
└── images/
    ├── 0001.jpg
    ├── 0002.jpg
    └── ...
```

可选参数在 `configs/datasets/<dataset_id>.toml` 调整：
- `aabb_scale`
- `ngp_steps`
- `marching_cubes_res`
- `vertical_axis`

流水线默认阶段：
1. `colmap`
2. `colmap_to_text`
3. `transforms`（生成 `transforms.json`）
4. `train_instant_ngp`
5. `export_geometry`（导出 `mesh.ply`）
6. `extract_traits`（输出 `traits.csv`）

## 实验进程记录

为便于你持续记录实验过程，仓库内已提供：
- 实验总日志：[docs/EXPERIMENT_LOG.md](./docs/EXPERIMENT_LOG.md)
- 单次实验模板：[docs/EXPERIMENT_RUN_TEMPLATE.md](./docs/EXPERIMENT_RUN_TEMPLATE.md)

建议每次运行后把关键参数、命令和指标追加到日志里，形成可复现的实验轨迹。

## 项目结构

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
│       ├── template.toml
│       └── maize_plant_01.toml
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

## 论文本地编译

```bash
cd manuscript
/Library/TeX/texbin/xelatex -interaction=nonstopmode nerf_plant_reconstruction.tex
/Library/TeX/texbin/xelatex -interaction=nonstopmode nerf_plant_reconstruction.tex
```

## 依赖说明

- `instant-ngp` 作为高效 NeRF 工程主线参考。
- `pointnerf` 作为稀疏视角鲁棒性增强参考。
- 使用时请遵循上游仓库许可与使用限制（Point-NeRF 仓库标注为非商用用途）。

## 作者

- 李肖然（Xiaoran Li）
