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
