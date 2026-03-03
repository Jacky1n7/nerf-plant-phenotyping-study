<p align="center">
  <img src="assets/banner.svg" alt="NeRF 植物三维重建与表型提取" width="100%" />
</p>

<p align="center">
  <a href="./README.md"><img src="assets/lang-zh.svg" alt="中文" width="180" height="36"/></a>
  <a href="./README.en.md"><img src="assets/lang-en.svg" alt="English" width="180" height="36"/></a>
</p>

# NeRF 植物三维重建与表型提取

这个仓库现在有两部分内容：
- 论文草稿（`manuscript/`）
- 可运行的实验流水线（`configs/` + `scripts/` + `Makefile`）

目标很直接：你给 360 度环拍视频，我按配置抽帧并跑完整重建流程。

## 你需要准备什么

1. 安装 `COLMAP`
2. 安装 `ffmpeg`
3. 克隆第三方项目并安装 Python 依赖

```bash
make bootstrap
pip install -r requirements.txt
```

## 数据目录（视频优先）

初始化一个数据集：

```bash
make init DATASET=maize_plant_01
```

会创建这两个输入目录：

```text
data/raw/maize_plant_01/
├── video/      # 原始视频放这里
└── images/     # 抽帧结果放这里（可自动生成）
```

默认视频路径是：

```text
data/raw/<dataset_id>/video/capture.mp4
```

如果文件名不是 `capture.mp4`，改 `configs/datasets/<dataset_id>.toml` 里的 `dataset.video_input` 即可。  
也可以把 `video_input` 设成 `auto`，脚本会在 `video_dir` 下自动识别单个视频文件。

## 运行流程

### 1) 检查配置和环境

```bash
make check DATASET=maize_plant_01
```

### 2) 只做视频抽帧（可选）

```bash
make frames DATASET=maize_plant_01
```

### 3) 跑全流程

```bash
make run DATASET=maize_plant_01
```

只看命令不执行：

```bash
make dry-run DATASET=maize_plant_01
```

## 常用参数（按数据集配置）

配置文件：`configs/datasets/<dataset_id>.toml`

视频抽帧参数（`[video]`）：
- `fps`: 抽帧频率
- `start_time`: 起始时间（例如 `00:00:05`）
- `end_time`: 结束时间（`none` 表示到视频末尾）
- `max_frames`: 最多抽多少帧（`0` 表示不限制）
- `resize_width` / `resize_height`: 抽帧分辨率（`-1` 表示保持）
- `overwrite`: 是否覆盖重抽（`true/false`）

重建参数（`[reconstruction]`）：
- `aabb_scale`
- `ngp_steps`
- `marching_cubes_res`

表型参数（`[traits]`）：
- `vertical_axis`

## 输出位置

- 运行日志：`outputs/runs/<dataset_id>/pipeline.log`
- 模型快照：`outputs/<dataset_id>/instant-ngp.msgpack`
- 网格：`outputs/<dataset_id>/mesh.ply`
- 表型结果：`outputs/<dataset_id>/traits.csv`

## 实验记录

- 总日志：[docs/EXPERIMENT_LOG.md](./docs/EXPERIMENT_LOG.md)
- 单次模板：[docs/EXPERIMENT_RUN_TEMPLATE.md](./docs/EXPERIMENT_RUN_TEMPLATE.md)

每次实验后直接把参数、命令和结果填进去，后续复盘会省很多时间。

## 项目结构

```text
.
├── assets/
├── configs/
│   ├── pipeline.toml
│   └── datasets/
├── docs/
│   ├── EXPERIMENT_LOG.md
│   └── EXPERIMENT_RUN_TEMPLATE.md
├── manuscript/
├── scripts/
│   ├── bootstrap_third_party.sh
│   ├── pipeline.py
│   ├── extract_video_frames.py
│   └── extract_traits.py
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
