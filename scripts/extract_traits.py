#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np


def load_vertices_with_trimesh(path: Path) -> np.ndarray:
    try:
        import trimesh
    except Exception as exc:  # pragma: no cover - optional dependency branch
        raise RuntimeError("trimesh is not available") from exc

    geom = trimesh.load(str(path), force="mesh")

    if hasattr(geom, "vertices") and len(geom.vertices) > 0:
        return np.asarray(geom.vertices, dtype=np.float64)

    if hasattr(geom, "geometry") and geom.geometry:
        vertices = []
        for sub_geom in geom.geometry.values():
            if hasattr(sub_geom, "vertices") and len(sub_geom.vertices) > 0:
                vertices.append(np.asarray(sub_geom.vertices, dtype=np.float64))
        if vertices:
            return np.concatenate(vertices, axis=0)

    raise ValueError(f"No vertices found in geometry: {path}")


def load_ascii_ply_vertices(path: Path) -> np.ndarray:
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    if not lines or lines[0].strip() != "ply":
        raise ValueError("Not a valid ASCII PLY file.")

    vertex_count = None
    header_end = None
    for idx, line in enumerate(lines):
        raw = line.strip()
        if raw.startswith("format") and "ascii" not in raw:
            raise ValueError("Only ASCII PLY is supported without trimesh.")
        if raw.startswith("element vertex"):
            parts = raw.split()
            vertex_count = int(parts[-1])
        if raw == "end_header":
            header_end = idx
            break

    if vertex_count is None or header_end is None:
        raise ValueError("Failed to parse PLY header.")

    body = lines[header_end + 1 : header_end + 1 + vertex_count]
    vertices = []
    for line in body:
        parts = line.split()
        if len(parts) < 3:
            continue
        vertices.append([float(parts[0]), float(parts[1]), float(parts[2])])

    if not vertices:
        raise ValueError("No vertices parsed from ASCII PLY.")

    return np.asarray(vertices, dtype=np.float64)


def load_vertices(path: Path) -> np.ndarray:
    try:
        return load_vertices_with_trimesh(path)
    except Exception:
        if path.suffix.lower() == ".ply":
            return load_ascii_ply_vertices(path)
        raise


def compute_traits(vertices: np.ndarray, vertical_axis: str, scale_to_cm: float) -> dict[str, float]:
    axis_map = {"x": 0, "y": 1, "z": 2}
    if vertical_axis not in axis_map:
        raise ValueError("vertical_axis must be one of: x, y, z")

    mins = vertices.min(axis=0)
    maxs = vertices.max(axis=0)
    extents = (maxs - mins) * scale_to_cm

    vertical_idx = axis_map[vertical_axis]
    horizontal_indices = [i for i in (0, 1, 2) if i != vertical_idx]

    height_cm = float(extents[vertical_idx])
    width_cm = float(max(extents[horizontal_indices[0]], extents[horizontal_indices[1]]))
    depth_cm = float(min(extents[horizontal_indices[0]], extents[horizontal_indices[1]]))
    bbox_volume_cm3 = float(extents[0] * extents[1] * extents[2])

    return {
        "height_cm": height_cm,
        "width_cm": width_cm,
        "depth_cm": depth_cm,
        "bbox_volume_cm3": bbox_volume_cm3,
        "point_count": float(vertices.shape[0]),
    }


def write_csv(output_path: Path, dataset: str, traits: dict[str, float]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["dataset", *traits.keys()]
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({"dataset": dataset, **traits})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract simple phenotypic traits from mesh/point cloud.")
    parser.add_argument("--input", required=True, help="Path to geometry file (ply/obj/stl/glb...).")
    parser.add_argument("--output", required=True, help="Path to CSV output.")
    parser.add_argument("--dataset", default="", help="Dataset id in CSV.")
    parser.add_argument("--vertical-axis", default="z", choices=["x", "y", "z"])
    parser.add_argument(
        "--scale-to-cm",
        type=float,
        default=100.0,
        help="Multiply geometry units by this factor before reporting cm metrics. Default: 100 (m->cm).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    dataset = args.dataset or input_path.parent.name

    if not input_path.exists():
        print(f"[error] geometry file not found: {input_path}", file=sys.stderr)
        return 1

    try:
        vertices = load_vertices(input_path)
        traits = compute_traits(vertices, args.vertical_axis, args.scale_to_cm)
        write_csv(output_path, dataset, traits)
    except Exception as exc:
        print(f"[error] trait extraction failed: {exc}", file=sys.stderr)
        return 1

    print(f"[ok] traits saved to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
