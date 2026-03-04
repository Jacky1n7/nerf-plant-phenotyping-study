# 实验进展日志

用于持续记录每次数据接收、参数调整、运行结果与结论，便于复现与回溯。

## 2026-03-03｜工程初始化

### 完成内容
- 建立可执行流水线入口：`make init/check/dry-run/run/traits`
- 新增配置体系：`configs/pipeline.toml`、`configs/datasets/*.toml`
- 新增执行脚本：`scripts/pipeline.py`、`scripts/extract_traits.py`
- 新增第三方依赖引导：`scripts/bootstrap_third_party.sh`
- 同步中英文 README 到“数据就绪即可运行”流程

### 当前状态
- `make init DATASET=maize_plant_01`：通过
- `make dry-run DATASET=maize_plant_01`：通过
- `make check DATASET=maize_plant_01`：未通过（预期）
  - 原因1：尚未放入采集图像
  - 原因2：本机尚未安装 `colmap`
  - 原因3：尚未执行 `make bootstrap` 拉取 `third_party/instant-ngp`

### 下一步
1. 执行 `make bootstrap`
2. 安装依赖：`pip install -r requirements.txt`
3. 按目录投放图像：`data/raw/<dataset_id>/images/`
4. 运行：`make check DATASET=<dataset_id>` -> `make run DATASET=<dataset_id>`

---

## 日志追加规则
每次实验在本文件追加一段，建议格式：
- 日期
- 数据集 ID
- 核心参数变更
- 运行命令
- 指标结果
- 问题与下一步动作

可直接复制 [EXPERIMENT_RUN_TEMPLATE.md](./EXPERIMENT_RUN_TEMPLATE.md) 填写。

## 2026-03-03｜接入视频抽帧流程

### 完成内容
- 新增视频输入目录约定：`data/raw/<dataset_id>/video/`
- 新增抽帧脚本：`scripts/extract_video_frames.py`
- 流水线新增阶段：`extract_video_frames`（位于 COLMAP 之前）
- 新增命令：`make frames DATASET=<dataset_id>`
- 更新数据集配置，支持视频抽帧参数（`[video]`）
- README 改为更直接的使用说明

### 当前默认行为
- 如果 `images/` 已有图片且 `overwrite=false`，抽帧阶段会自动跳过
- 如果 `images/` 为空，抽帧阶段会从 `video_input` 抽帧
- `video_input=auto` 时，会从 `video_dir` 自动识别单个视频文件

---

## 2026-03-04｜maize_plant_01 全流程跑通

### 数据与参数
- 数据集：`maize_plant_01`
- 原始输入：`data/raw/maize_plant_01/video/capture.mp4`
- 抽帧参数：
  - `fps=6`
  - `max_frames=180`
  - `overwrite=true`（重抽）
- COLMAP 参数：
  - `data_type=video`
  - `quality=medium`
  - `single_camera=true`
  - `use_gpu=true`
  - `openblas_num_threads=1`

### 关键修复与工程变更
- 修复 COLMAP 工作目录缺失问题（运行前创建 `workspace_dir/colmap`）。
- 新增 COLMAP 可配置参数（GPU、线程、数据类型、质量）。
- 补全 instant-ngp Python 绑定编译，解决 `No module named pyngp`。
- 新增训练前检查：
  - `pyngp_binary` 存在性检查
  - `transforms_images` 可访问性检查
- 新增 `scripts/fix_transforms_paths.py`，自动修复 `transforms.json` 的图片路径。
- 在 transforms 阶段接入路径修复命令，避免 `No training images were found`。
- 重新编译 instant-ngp 并启用 GUI，修复 `NGP was built without GUI support`。

### 运行结果
- 全流程结束时间：`2026-03-04 11:38:50`（见 `pipeline.log`）。
- 产物：
  - `outputs/maize_plant_01/instant-ngp.msgpack`
  - `outputs/maize_plant_01/mesh.ply`
  - `outputs/maize_plant_01/traits.csv`
- traits（当前未做真实尺度标定）：
  - `height_cm=4839.003944396973`
  - `width_cm=4839.007949829102`
  - `depth_cm=4839.005088806152`
  - `bbox_volume_cm3=113310039392.7856`
  - `point_count=20452419.0`

### 主要踩坑记录
1. `ModuleNotFoundError: No module named 'pyngp'`
- 处理：编译 `third_party/instant-ngp/build` 并在 `make check` 增加预检。

2. `ValueError: No training images were found for NeRF training`
- 处理：修复 `transforms.json` 的 `file_path` 指向，接入自动修复脚本。

3. `RuntimeError: init_window failed: NGP was built without GUI support`
- 处理：安装 OpenGL/X11 依赖并重新编译 GUI 版本。

### 下一步
1. 新对话窗口开始“点云生成”链路设计（从 `mesh.ply` 导出统一点云格式）。
2. 引入尺度标定（标定尺或已知器件尺寸）将当前相对量换算为真实厘米量级。
3. 形成批量多株处理模板（dataset 配置复制 + 批处理命令）。
