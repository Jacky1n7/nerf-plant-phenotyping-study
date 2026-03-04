#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def parse_ply_header(path: Path) -> tuple[int, int]:
    vertex_count = -1
    header_bytes = 0
    with path.open("rb") as f:
        while True:
            line = f.readline()
            if not line:
                raise ValueError("Invalid PLY: end_header not found")
            header_bytes += len(line)
            text = line.decode("utf-8", errors="ignore").strip()
            if text.startswith("format ") and "ascii" not in text:
                raise ValueError("Only ASCII PLY is supported by this preview script")
            if text.startswith("element vertex "):
                vertex_count = int(text.split()[-1])
            if text == "end_header":
                break
    if vertex_count <= 0:
        raise ValueError("Invalid PLY: vertex count not found")
    return vertex_count, header_bytes


def sample_vertices(path: Path, target_points: int) -> np.ndarray:
    vertex_count, _ = parse_ply_header(path)
    step = max(1, vertex_count // max(1, target_points))
    points: list[tuple[float, float, float]] = []

    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.strip() == "end_header":
                break
        for i in range(vertex_count):
            line = f.readline()
            if not line:
                break
            if i % step != 0:
                continue
            parts = line.strip().split()
            if len(parts) < 3:
                continue
            try:
                x, y, z = float(parts[0]), float(parts[1]), float(parts[2])
            except ValueError:
                continue
            points.append((x, y, z))

    if not points:
        raise ValueError("No valid points sampled from mesh")
    return np.asarray(points, dtype=np.float32)


def camera_center_from_transforms(path: Path) -> np.ndarray:
    data = json.loads(path.read_text(encoding="utf-8"))
    frames = data.get("frames", [])
    if not isinstance(frames, list) or not frames:
        raise ValueError("No frames found in transforms file")
    centers = []
    for frame in frames:
        mat = np.asarray(frame.get("transform_matrix"), dtype=np.float32)
        if mat.shape != (4, 4):
            continue
        centers.append(mat[:3, 3])
    if not centers:
        raise ValueError("No valid camera transforms found")
    return np.mean(np.stack(centers, axis=0), axis=0)


def radial_focus(points: np.ndarray, center: np.ndarray, keep_quantile: float) -> np.ndarray:
    q = min(0.8, max(0.01, keep_quantile))
    d = np.linalg.norm(points - center[None, :], axis=1)
    threshold = float(np.quantile(d, q))
    kept = points[d <= threshold]
    if len(kept) < max(2000, len(points) // 20):
        return points
    return kept


def rotation_matrix(elev_deg: float, azim_deg: float) -> np.ndarray:
    elev = math.radians(elev_deg)
    azim = math.radians(azim_deg)

    rx = np.array(
        [
            [1, 0, 0],
            [0, math.cos(elev), -math.sin(elev)],
            [0, math.sin(elev), math.cos(elev)],
        ],
        dtype=np.float32,
    )
    rz = np.array(
        [
            [math.cos(azim), -math.sin(azim), 0],
            [math.sin(azim), math.cos(azim), 0],
            [0, 0, 1],
        ],
        dtype=np.float32,
    )
    return rz @ rx


def render_view(points: np.ndarray, size: tuple[int, int], elev: float, azim: float) -> Image.Image:
    w, h = size
    margin = 20
    canvas = np.full((h, w, 3), 245, dtype=np.uint8)

    rot = rotation_matrix(elev, azim)
    p = points @ rot.T

    x = p[:, 0]
    y = p[:, 1]
    z = p[:, 2]

    x = (x - x.min()) / (x.max() - x.min() + 1e-8)
    y = (y - y.min()) / (y.max() - y.min() + 1e-8)
    z = (z - z.min()) / (z.max() - z.min() + 1e-8)

    px = (margin + x * (w - 2 * margin)).astype(np.int32)
    py = (margin + (1 - y) * (h - 2 * margin)).astype(np.int32)

    order = np.argsort(z)
    for idx in order:
        xi = int(px[idx])
        yi = int(py[idx])
        if xi < 0 or xi >= w or yi < 0 or yi >= h:
            continue
        depth = float(z[idx])
        shade = int(40 + 180 * depth)
        canvas[yi, xi, :] = (30, shade, 50)
        if yi + 1 < h:
            canvas[yi + 1, xi, :] = (60, min(255, shade + 20), 80)
        if xi + 1 < w:
            canvas[yi, xi + 1, :] = (60, min(255, shade + 20), 80)

    return Image.fromarray(canvas, mode="RGB")


def crop_outer_shell(points: np.ndarray, quantile: float) -> np.ndarray:
    if quantile <= 0.0:
        return points
    q = min(0.2, max(0.0, quantile))
    lo = np.quantile(points, q, axis=0)
    hi = np.quantile(points, 1.0 - q, axis=0)
    mask = np.all((points >= lo) & (points <= hi), axis=1)
    cropped = points[mask]
    if len(cropped) < max(2000, len(points) // 10):
        return points
    return cropped


def compose_preview(points: np.ndarray, output_path: Path, dataset: str) -> None:
    panel_size = (760, 760)
    left = render_view(points, panel_size, elev=18, azim=35)
    right = render_view(points, panel_size, elev=10, azim=-55)

    final = Image.new("RGB", (1600, 900), (255, 255, 255))
    draw = ImageDraw.Draw(final)
    draw.rectangle([0, 0, 1599, 89], fill=(24, 32, 42))
    draw.text((24, 28), f"{dataset} | Instant-NGP Mesh Preview", fill=(240, 245, 250))

    final.paste(left, (30, 110))
    final.paste(right, (810, 110))

    draw.rectangle([30, 110, 790, 870], outline=(220, 220, 220), width=2)
    draw.rectangle([810, 110, 1570, 870], outline=(220, 220, 220), width=2)
    draw.text((42, 840), "View A", fill=(80, 90, 100))
    draw.text((822, 840), "View B", fill=(80, 90, 100))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    final.save(output_path, format="PNG")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a lightweight preview image from mesh.ply")
    parser.add_argument("--input", required=True, help="Input mesh PLY path")
    parser.add_argument("--output", required=True, help="Output preview PNG path")
    parser.add_argument("--dataset", required=True, help="Dataset id for preview title")
    parser.add_argument("--transforms", default="", help="Optional transforms.json for camera-center-guided focus")
    parser.add_argument("--target-points", type=int, default=220000, help="Approx sampled point count")
    parser.add_argument(
        "--radial-keep-quantile",
        type=float,
        default=0.15,
        help="Keep nearest quantile of points around camera center (requires --transforms)",
    )
    parser.add_argument(
        "--crop-quantile",
        type=float,
        default=0.025,
        help="Trim outer shell by quantile on each axis to suppress boundary artifacts",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    if not input_path.exists():
        raise FileNotFoundError(f"Input mesh not found: {input_path}")

    points = sample_vertices(input_path, args.target_points)
    if args.transforms:
        transforms_path = Path(args.transforms)
        if not transforms_path.exists():
            raise FileNotFoundError(f"Transforms file not found: {transforms_path}")
        center = camera_center_from_transforms(transforms_path)
        points = radial_focus(points, center, args.radial_keep_quantile)
    points = crop_outer_shell(points, args.crop_quantile)
    compose_preview(points, output_path, args.dataset)
    print(f"[ok] preview saved to: {output_path}")
    print(f"[ok] sampled points: {len(points)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
