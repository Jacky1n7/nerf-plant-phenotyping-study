<p align="center">
  <img src="assets/banner.svg" alt="NeRF 植物三维重建与表型提取" width="100%" />
</p>

<p align="center">
  <a href="./README.md"><img src="assets/lang-zh.svg" alt="中文" width="180" height="36"/></a>
  <a href="./README.en.md"><img src="assets/lang-en.svg" alt="English" width="180" height="36"/></a>
</p>

# NeRF 植物三维重建与表型提取

这个仓库用于把植株环拍视频重建为 3D 几何，并提取基础表型指标。

核心产物：
- `outputs/<dataset_id>/instant-ngp.msgpack`
- `outputs/<dataset_id>/mesh.ply`
- `outputs/<dataset_id>/dense_point_cloud.ply`
- `outputs/<dataset_id>/traits.csv`

## 当前状态（2026-03-04）

- 当前推荐与默认流程：`instant-ngp`
- `maize_plant_01` 已完成多轮优化，当前配置重点是：
  - 裁剪 + 模糊帧筛选（尽量保留有效帧）
  - COLMAP 自动选择注册帧最多的 sparse 子模型
  - 全流程终端输出已中文化
- mip-nerf360 相关环境已清理，不作为当前建议路径

## 环境准备

建议 Python 3.11：

```bash
conda create -n nerf python=3.11 -y
conda activate nerf
pip install -r requirements.txt
make bootstrap
```

系统依赖：
- `COLMAP`
- `ffmpeg`

如果需要打开 instant-ngp GUI（`--gui`），建议安装 OpenGL/X11 依赖：

```bash
conda install -n nerf -c conda-forge \
  libgl-devel libglu xorg-libx11 xorg-libxext \
  xorg-libxrandr xorg-libxi xorg-libxinerama xorg-libxcursor
```

## 数据目录

初始化数据集：

```bash
make init DATASET=maize_plant_01
```

默认输入视频：

```text
data/raw/<dataset_id>/video/capture.mp4
```

如果文件名不同，改 `configs/datasets/<dataset_id>.toml` 的 `dataset.video_input`。

## 一键运行（推荐）

```bash
make check DATASET=maize_plant_01
make run DATASET=maize_plant_01
```

如果你希望实时看到训练日志（避免输出缓冲）：

```bash
make run-live DATASET=maize_plant_01
```

说明：
- `colmap` 阶段会自动清理旧的 `colmap/`、`colmap_text/`、`transforms.json`
- `pipeline.py run` 的主提示为中文（阶段、执行、错误、完成）

## 常用分阶段命令

只抽帧：

```bash
make frames DATASET=maize_plant_01
```

只重做位姿 + transforms：

```bash
python scripts/pipeline.py \
  --config configs/pipeline.toml run \
  --dataset maize_plant_01 \
  --stages colmap,colmap_to_text,transforms
```

从训练开始续跑：

```bash
python scripts/pipeline.py \
  --config configs/pipeline.toml run \
  --dataset maize_plant_01 \
  --stages train_instant_ngp,export_geometry,extract_dense_point_cloud,extract_traits
```

只从 mesh 重提密集点云：

```bash
make dense-cloud DATASET=maize_plant_01
```

## 结果查看

看指标：

```bash
cat outputs/maize_plant_01/traits.csv
```

看 NeRF（GUI，中文增强启动器）：

```bash
make view-gui DATASET=maize_plant_01
```

看网格：

```bash
meshlab outputs/maize_plant_01/mesh.ply
# 或
cloudcompare outputs/maize_plant_01/mesh.ply
```

看密集点云：

```bash
cloudcompare outputs/maize_plant_01/dense_point_cloud.ply
```

## 去云雾策略（当前建议）

当前 `maize_plant_01` 配置里 `dehaze.enabled = false`（默认关闭）。

建议做法：
1. 先以默认配置跑通完整流程，确认基线效果。
2. 如果场景确实有明显雾化/泛白，再开启 `dehaze` 并重跑 `colmap,colmap_to_text,transforms`。
3. 对比注册帧数、点云噪声和叶片边缘细节，再决定是否用于正式训练。

## 常见问题

1. `ModuleNotFoundError: No module named pyngp`
- 原因：instant-ngp Python 绑定未编译。
- 处理：重新编译 `third_party/instant-ngp/build`，然后执行 `make check`。

2. `No training images were found for NeRF training`
- 原因：`transforms.json` 中 `file_path` 不可解析。
- 处理：

```bash
python scripts/fix_transforms_paths.py \
  --transforms data/processed/<dataset_id>/transforms.json \
  --project-root .
```

3. `imread(...frame_xxxxxx.jpg)` + `cvtColor ... !_src.empty()`
- 原因：常见于换视频后仍引用了旧 COLMAP 中间结果。
- 处理：重跑

```bash
python scripts/pipeline.py \
  --config configs/pipeline.toml run \
  --dataset <dataset_id> \
  --stages colmap,colmap_to_text,transforms
```

4. `NGP was built without GUI support`
- 原因：GUI 依赖不完整或编译时关闭 GUI。
- 处理：安装 GUI 依赖后重新编译 instant-ngp。

## 输出与日志位置

- 运行日志：`outputs/runs/<dataset_id>/pipeline.log`
- 快照：`outputs/<dataset_id>/instant-ngp.msgpack`
- 网格：`outputs/<dataset_id>/mesh.ply`
- 密集点云：`outputs/<dataset_id>/dense_point_cloud.ply`
- 指标：`outputs/<dataset_id>/traits.csv`
- 训练可视化：`outputs/<dataset_id>/training_vis/`

## 相关文档

- 命令速查：[docs/COMMANDS.md](./docs/COMMANDS.md)
- 实验日志：[docs/EXPERIMENT_LOG.md](./docs/EXPERIMENT_LOG.md)
- 单次实验模板：[docs/EXPERIMENT_RUN_TEMPLATE.md](./docs/EXPERIMENT_RUN_TEMPLATE.md)
- 第一轮优化说明：[docs/OPTIMIZATION_ROUND1.md](./docs/OPTIMIZATION_ROUND1.md)
