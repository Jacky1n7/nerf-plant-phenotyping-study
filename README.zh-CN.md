<p align="center">
  <img src="assets/banner.svg" alt="NeRF 植物三维重建与表型提取" width="100%" />
</p>

<p align="center">
  <a href="./README.md"><img src="assets/lang-en.svg" alt="English" width="180" height="36"/></a>
  <a href="./README.zh-CN.md"><img src="assets/lang-zh.svg" alt="中文" width="180" height="36"/></a>
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

草稿中的方法流程已补充为可复现的工程路径：
- **Instant-NGP分支**：以哈希编码 NeRF 为主干，包含 COLMAP 到 `transforms.json` 的预处理与密度场几何导出。
- **Point-NeRF分支**：以神经点表示增强稀疏视角/强遮挡场景，通过点剪枝与增殖提高局部几何稳定性。

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
└── manuscript_package.tar.gz
```

## 本地编译

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
