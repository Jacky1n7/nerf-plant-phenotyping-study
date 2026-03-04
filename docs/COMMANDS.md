# 命令速查（maize_plant_01）

## 1. 基础

```bash
conda activate nerf
cd ~/nerf-plant-phenotyping-study
```

## 2. 初始化与检查

```bash
make init DATASET=maize_plant_01
make check DATASET=maize_plant_01
```

## 3. 全流程重跑（推荐）

```bash
make run DATASET=maize_plant_01
```

如果你想在终端稳定看到实时训练进度（避免输出缓存）：

```bash
make run-live DATASET=maize_plant_01
```

说明：`colmap` 阶段会自动清理旧的 `colmap/`、`colmap_text/`、`transforms.json`，适合换视频后直接重跑。

## 4. 常用分阶段

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

只跑训练：

```bash
python scripts/pipeline.py \
  --config configs/pipeline.toml run \
  --dataset maize_plant_01 \
  --stages train_instant_ngp
```

只提取密集点云：

```bash
make dense-cloud DATASET=maize_plant_01
```

## 5. 结果查看

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

## 6. 常见报错快速处理

`imread(...frame_xxxxxx.jpg)` + `cvtColor !_src.empty()`：

```bash
python scripts/pipeline.py \
  --config configs/pipeline.toml run \
  --dataset maize_plant_01 \
  --stages colmap,colmap_to_text,transforms
```

`No training images were found for NeRF training`：

```bash
python scripts/fix_transforms_paths.py \
  --transforms data/processed/maize_plant_01/transforms.json \
  --project-root .
```
