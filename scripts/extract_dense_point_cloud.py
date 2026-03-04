#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

try:
    import trimesh
except Exception as exc:  # pragma: no cover - dependency check
    trimesh = None
    TRIMESH_IMPORT_ERROR = exc
else:
    TRIMESH_IMPORT_ERROR = None


def text_to_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def merge_meshes(geometry: trimesh.Trimesh | trimesh.Scene) -> trimesh.Trimesh:
    if isinstance(geometry, trimesh.Trimesh):
        return geometry
    if not isinstance(geometry, trimesh.Scene):
        raise ValueError(f"Unsupported geometry type: {type(geometry).__name__}")

    meshes = [g for g in geometry.geometry.values() if isinstance(g, trimesh.Trimesh)]
    if not meshes:
        raise ValueError("No mesh geometry found in scene.")
    if len(meshes) == 1:
        return meshes[0]
    return trimesh.util.concatenate(meshes)


def sample_mesh(mesh: trimesh.Trimesh, num_points: int) -> tuple[np.ndarray, np.ndarray | None]:
    if len(mesh.faces) == 0:
        if len(mesh.vertices) == 0:
            raise ValueError("Mesh contains no faces or vertices.")
        points = np.asarray(mesh.vertices, dtype=np.float32)
        if num_points <= len(points):
            indices = np.random.choice(len(points), size=num_points, replace=False)
            points = points[indices]
        else:
            extra = np.random.choice(len(points), size=num_points - len(points), replace=True)
            points = np.concatenate([points, points[extra]], axis=0)
        return points, None

    points, face_idx = trimesh.sample.sample_surface(mesh, count=num_points)
    points = np.asarray(points, dtype=np.float32)

    colors = None
    visual = mesh.visual
    if hasattr(visual, "face_colors") and len(visual.face_colors) == len(mesh.faces):
        colors = np.asarray(visual.face_colors[face_idx, :3], dtype=np.uint8)
    elif hasattr(visual, "vertex_colors") and len(visual.vertex_colors) == len(mesh.vertices):
        vertex_colors = np.asarray(visual.vertex_colors[:, :3], dtype=np.float32)
        face_vertex_colors = vertex_colors[mesh.faces[face_idx]]
        colors = np.clip(np.mean(face_vertex_colors, axis=1), 0, 255).astype(np.uint8)

    return points, colors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract dense point cloud by sampling a reconstructed mesh.")
    parser.add_argument("--input", required=True, help="Input mesh path (ply/obj/stl/glb...).")
    parser.add_argument("--output", required=True, help="Output point cloud path (.ply recommended).")
    parser.add_argument("--enabled", default="true", help="true/false")
    parser.add_argument("--num-points", type=int, default=1200000, help="Number of sampled points.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic sampling.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if trimesh is None:
        print(
            f"[error] trimesh is required for dense point cloud export: {TRIMESH_IMPORT_ERROR}",
            file=sys.stderr,
        )
        return 1

    enabled = text_to_bool(args.enabled)
    if not enabled:
        print("[info] dense point cloud extraction disabled by config; skipping.")
        return 0

    if args.num_points <= 0:
        print("[error] --num-points must be > 0", file=sys.stderr)
        return 1

    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    if not input_path.exists():
        print(f"[error] mesh file not found: {input_path}", file=sys.stderr)
        return 1

    np.random.seed(args.seed)
    try:
        geometry = trimesh.load(str(input_path), force="mesh", process=False)
        mesh = merge_meshes(geometry)
        points, colors = sample_mesh(mesh, args.num_points)
    except Exception as exc:
        print(f"[error] failed to sample mesh: {exc}", file=sys.stderr)
        return 1

    cloud = trimesh.points.PointCloud(vertices=points, colors=colors)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        cloud.export(str(output_path))
    except Exception as exc:
        print(f"[error] failed to export point cloud: {exc}", file=sys.stderr)
        return 1

    print(f"[ok] dense point cloud saved: {output_path}")
    print(f"[ok] sampled points: {points.shape[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
