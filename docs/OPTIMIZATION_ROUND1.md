# 第一轮优化说明（2026-03-04）

## 参考论文

1. NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis  
   https://arxiv.org/abs/2010.07492
2. Mip-NeRF 360: Unbounded Anti-Aliased Neural Radiance Fields  
   https://arxiv.org/abs/2111.12077

## 本轮实现（已落地到 pipeline）

### 1) 去云雾（新阶段：`dehaze_images`）

- 新增脚本：`scripts/dehaze_images.py`
- 算法：Dark Channel Prior + Guided Filter（工程化可控参数）
- 处理路径：
  - 输入：`data/raw/<dataset>/images`
  - 输出：`data/processed/<dataset>/images_dehazed`
- 配置区段：`configs/datasets/<dataset>.toml` 的 `[dehaze]`
- 关键效果：开启后 COLMAP 与 transforms 自动改用去云雾图像目录（由 `{recon_images_dir}` 自动切换）

### 2) 建模精度提升（训练/几何参数增强）

- 新增训练参数透传到 instant-ngp：
  - `train_mode`
  - `rfl_warmup_steps`
  - `rflrelax_begin_step` / `rflrelax_end_step`
  - `near_distance`
  - `sharpen`
  - `exposure`
- 新增几何导出参数：
  - `marching_cubes_density_thresh`
- 关联脚本：
  - `scripts/train_with_visualization.py`
  - `configs/pipeline.toml`
  - `scripts/pipeline.py`
- 工程映射：
  - 对 NeRF 的“采样与体渲染质量敏感性”，通过训练超参与输入质量控制（去云雾）增强稳定性。
  - 对 Mip-NeRF 360 的“抑制伪影/提升几何一致性”思想，在当前 instant-ngp 框架中采用 RFL/RFLRelax 调度和更稳健几何阈值作为第一轮近似实现。

### 3) 密集点云提取（新阶段：`extract_dense_point_cloud`）

- 新增脚本：`scripts/extract_dense_point_cloud.py`
- 方法：基于重建 mesh 进行高密度表面采样并导出 `dense_point_cloud.ply`
- 配置区段：`[point_cloud]`
- 默认输出：
  - `outputs/<dataset>/dense_point_cloud.ply`

## 命令入口

- 全流程（包含去云雾与密集点云）：

```bash
make run DATASET=maize_plant_01
```

- 仅重提密集点云：

```bash
make dense-cloud DATASET=maize_plant_01
```

## 已验证项

- `python -m py_compile` 通过（新增/改动脚本）
- pipeline `--dry-run` 通过（阶段链路与参数拼接正确）
- 去云雾脚本实跑完成（160 张）
- 点云提取脚本实跑完成（示例采样 300000 点）

## 当前边界（下一轮可继续）

- 本轮未重写底层 NeRF 网络结构（proposal network / contraction / distortion loss 原生实现仍在上游框架内）。
- 当前是“在现有 instant-ngp pipeline 上的工程可落地增强”，优先保证可跑、可复现、可迭代。
