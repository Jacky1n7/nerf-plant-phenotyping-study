# 单次实验记录模板

## 基本信息
- 日期：
- 执行人：
- 数据集 ID：
- 数据规模（图片数）：

## 输入与配置
- 图像路径：`data/raw/<dataset_id>/images/`
- 数据集配置：`configs/datasets/<dataset_id>.toml`
- 关键参数：
  - `aabb_scale`:
  - `ngp_steps`:
  - `marching_cubes_res`:
  - `vertical_axis`:

## 运行命令
```bash
make check DATASET=<dataset_id>
make run DATASET=<dataset_id>
```

## 输出产物
- 运行日志：`outputs/runs/<dataset_id>/pipeline.log`
- 模型快照：`outputs/<dataset_id>/instant-ngp.msgpack`
- 几何文件：`outputs/<dataset_id>/mesh.ply`
- 表型结果：`outputs/<dataset_id>/traits.csv`

## 结果摘要
- 高度（cm）：
- 宽度（cm）：
- 深度（cm）：
- 包围盒体积（cm^3）：
- 点数量：

## 问题与分析
- 问题 1：
- 问题 2：

## 下一步动作
1.
2.
