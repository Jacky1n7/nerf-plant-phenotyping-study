#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[1]


def import_pyngp():
    try:
        import pyngp as ngp  # type: ignore

        return ngp
    except Exception:
        build_dir = ROOT_DIR / "third_party" / "instant-ngp" / "build"
        if build_dir.exists():
            sys.path.insert(0, str(build_dir))
        try:
            import pyngp as ngp  # type: ignore

            return ngp
        except Exception as exc:
            raise RuntimeError(
                "无法导入 pyngp。请在 nerf 环境运行，并设置 "
                "PYTHONPATH=third_party/instant-ngp/build"
            ) from exc


def triangle_areas(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    v0 = vertices[faces[:, 0]]
    v1 = vertices[faces[:, 1]]
    v2 = vertices[faces[:, 2]]
    cross = np.cross(v1 - v0, v2 - v0)
    return 0.5 * np.linalg.norm(cross, axis=1)


def sample_points_on_mesh(
    vertices: np.ndarray, faces: np.ndarray, n_points: int, seed: int
) -> np.ndarray:
    if n_points <= 0:
        raise ValueError("n_points 必须大于 0")
    if len(vertices) == 0 or len(faces) == 0:
        raise ValueError("网格为空，无法采样点云")

    rng = np.random.default_rng(seed)
    areas = triangle_areas(vertices, faces)
    total_area = float(np.sum(areas))
    if total_area <= 0:
        raise ValueError("网格三角面面积总和为 0，无法采样")

    probs = areas / total_area
    tri_indices = rng.choice(len(faces), size=n_points, replace=True, p=probs)
    chosen = faces[tri_indices]

    v0 = vertices[chosen[:, 0]]
    v1 = vertices[chosen[:, 1]]
    v2 = vertices[chosen[:, 2]]

    # Uniform barycentric sampling on triangles.
    r1 = np.sqrt(rng.random(n_points))
    r2 = rng.random(n_points)
    points = (1.0 - r1)[:, None] * v0 + (r1 * (1.0 - r2))[:, None] * v1 + (r1 * r2)[:, None] * v2
    return points.astype(np.float32)


def write_ply_xyz(points: np.ndarray, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "ply\n"
        "format binary_little_endian 1.0\n"
        f"element vertex {len(points)}\n"
        "property float x\n"
        "property float y\n"
        "property float z\n"
        "end_header\n"
    ).encode("ascii")

    with output_path.open("wb") as f:
        f.write(header)
        f.write(np.asarray(points, dtype="<f4").tobytes())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="使用 instant-ngp Python API 从 NeRF 快照采样点云（先提网格，再表面采样）。"
    )
    parser.add_argument("--snapshot", required=True, help="base.ingp 或 .msgpack 快照路径")
    parser.add_argument("--output", default="plant.ply", help="输出点云 PLY 路径")
    parser.add_argument("--mesh-output", default="", help="可选：保存中间 marching cubes 网格")
    parser.add_argument("--mc-res", type=int, default=384, help="marching cubes 分辨率（建议 256-512）")
    parser.add_argument(
        "--density-thresh",
        type=float,
        default=2.5,
        help="NeRF 密度阈值（instant-ngp 常用 2.5）",
    )
    parser.add_argument("--num-points", type=int, default=1200000, help="采样点数")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    snapshot = Path(args.snapshot).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    mesh_output = Path(args.mesh_output).expanduser().resolve() if args.mesh_output else None

    if not snapshot.exists():
        print(f"[错误] 快照不存在: {snapshot}", file=sys.stderr)
        return 1
    if args.mc_res < 64:
        print("[错误] --mc-res 过小，建议 >= 64", file=sys.stderr)
        return 1

    try:
        ngp = import_pyngp()
    except Exception as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 1

    print(f"[信息] 加载快照: {snapshot}")
    testbed = ngp.Testbed()
    testbed.load_snapshot(str(snapshot))

    print(
        f"[信息] 提取 marching cubes 网格: res={args.mc_res}, "
        f"density_thresh={args.density_thresh}"
    )
    mesh = testbed.compute_marching_cubes_mesh(
        resolution=np.array([args.mc_res, args.mc_res, args.mc_res], dtype=np.int32),
        thresh=args.density_thresh,
    )

    vertices = np.asarray(mesh["V"], dtype=np.float32)
    faces = np.asarray(mesh["F"], dtype=np.int32)

    print(f"[信息] 网格顶点/面片: {len(vertices)}/{len(faces)}")
    if len(vertices) == 0 or len(faces) == 0:
        print("[错误] 网格为空，可尝试降低 --density-thresh 或提高 --mc-res", file=sys.stderr)
        return 1

    if mesh_output is not None:
        print(f"[信息] 保存中间网格: {mesh_output}")
        testbed.compute_and_save_marching_cubes_mesh(
            str(mesh_output),
            resolution=np.array([args.mc_res, args.mc_res, args.mc_res], dtype=np.int32),
            thresh=args.density_thresh,
        )

    print(f"[信息] 采样点云: num_points={args.num_points}, seed={args.seed}")
    points = sample_points_on_mesh(vertices, faces, n_points=args.num_points, seed=args.seed)

    write_ply_xyz(points, output)
    print(f"[完成] 点云已写出: {output}")
    print(f"[完成] 点数: {len(points)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
