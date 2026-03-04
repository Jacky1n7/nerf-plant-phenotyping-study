#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
import shutil
import sys
from pathlib import Path

import cv2

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def text_to_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def list_images(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(
        [
            p
            for p in path.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES and not p.name.startswith(".")
        ]
    )


def laplacian_sharpness(path: Path) -> float:
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"failed to read image: {path}")
    lap = cv2.Laplacian(img, cv2.CV_64F)
    return float(lap.var())


def pick_topup_by_segment(
    scored: list[tuple[Path, float]], selected_names: set[str], need: int
) -> list[tuple[Path, float]]:
    if need <= 0:
        return []

    n = len(scored)
    segment_count = min(n, need)
    picked: list[tuple[Path, float]] = []
    used: set[str] = set()

    for seg in range(segment_count):
        start = (seg * n) // segment_count
        end = ((seg + 1) * n) // segment_count
        if end <= start:
            end = min(start + 1, n)

        segment = scored[start:end]
        candidates = [
            (p, s)
            for p, s in sorted(segment, key=lambda x: x[1], reverse=True)
            if p.name not in selected_names and p.name not in used
        ]
        if not candidates:
            continue

        best = candidates[0]
        picked.append(best)
        used.add(best[0].name)

    if len(picked) >= need:
        return picked[:need]

    remaining = [
        (p, s)
        for p, s in sorted(scored, key=lambda x: x[1], reverse=True)
        if p.name not in selected_names and p.name not in used
    ]
    return picked + remaining[: need - len(picked)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Filter blurry frames before COLMAP by Laplacian sharpness.")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--metrics-csv", required=True)
    parser.add_argument("--enabled", default="false", help="true/false")
    parser.add_argument("--overwrite", default="true", help="true/false")
    parser.add_argument("--min-sharpness", type=float, default=8.0)
    parser.add_argument("--min-images", type=int, default=60)
    parser.add_argument("--min-index", type=int, default=0, help="Keep frames with index >= min-index. 0 disables.")
    parser.add_argument("--max-index", type=int, default=0, help="Keep frames with index <= max-index. 0 disables.")
    parser.add_argument(
        "--topup-mode",
        choices=("segment", "sharpness"),
        default="segment",
        help="How to add extra frames when selected frames are fewer than min-images.",
    )
    return parser.parse_args()


def parse_frame_index(path: Path) -> int | None:
    match = re.search(r"(\d+)", path.stem)
    if not match:
        return None
    return int(match.group(1))


def main() -> int:
    args = parse_args()
    enabled = text_to_bool(args.enabled)
    overwrite = text_to_bool(args.overwrite)

    input_dir = Path(args.input_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    metrics_csv = Path(args.metrics_csv).expanduser().resolve()

    if not input_dir.exists():
        print(f"[error] input dir not found: {input_dir}", file=sys.stderr)
        return 1

    images = list_images(input_dir)
    if not images:
        print(f"[error] no images found in: {input_dir}", file=sys.stderr)
        return 1

    if not enabled:
        output_dir.mkdir(parents=True, exist_ok=True)
        copied = 0
        for p in images:
            target = output_dir / p.name
            if target.exists() and not overwrite:
                continue
            shutil.copy2(p, target)
            copied += 1
        print(f"[info] frame filter disabled; copied {copied} images.")
        return 0

    if args.min_sharpness < 0:
        print("[error] --min-sharpness must be >= 0", file=sys.stderr)
        return 1
    if args.min_images <= 0:
        print("[error] --min-images must be > 0", file=sys.stderr)
        return 1

    min_index = args.min_index
    max_index = args.max_index
    if min_index < 0:
        print("[error] --min-index must be >= 0", file=sys.stderr)
        return 1
    if max_index < 0:
        print("[error] --max-index must be >= 0", file=sys.stderr)
        return 1
    if min_index > 0 and max_index > 0 and min_index > max_index:
        print("[error] --min-index must be <= --max-index", file=sys.stderr)
        return 1

    candidates: list[Path] = []
    for p in images:
        idx = parse_frame_index(p)
        if idx is not None:
            if min_index > 0 and idx < min_index:
                continue
            if max_index > 0 and idx > max_index:
                continue
        candidates.append(p)

    if not candidates:
        print("[error] no images remain after index filtering", file=sys.stderr)
        return 1

    scored: list[tuple[Path, float]] = []
    for p in candidates:
        try:
            score = laplacian_sharpness(p)
        except Exception as exc:
            print(f"[error] failed to score {p.name}: {exc}", file=sys.stderr)
            return 1
        scored.append((p, score))

    threshold_selected = [(p, s) for p, s in scored if s >= args.min_sharpness]
    threshold_selected_names = {p.name for p, _ in threshold_selected}

    desired = min(args.min_images, len(scored))
    selected_names = set(threshold_selected_names)
    topup_selected: list[tuple[Path, float]] = []

    if len(selected_names) < desired:
        need = desired - len(selected_names)
        if args.topup_mode == "segment":
            topup_selected = pick_topup_by_segment(scored, selected_names, need)
        else:
            topup_selected = [
                (p, s)
                for p, s in sorted(scored, key=lambda x: x[1], reverse=True)
                if p.name not in selected_names
            ][:need]
        selected_names.update(p.name for p, _ in topup_selected)

    output_dir.mkdir(parents=True, exist_ok=True)
    if overwrite:
        for old in list_images(output_dir):
            old.unlink()

    kept = 0
    for p, _ in scored:
        if p.name in selected_names:
            shutil.copy2(p, output_dir / p.name)
            kept += 1

    metrics_csv.parent.mkdir(parents=True, exist_ok=True)
    with metrics_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["image_name", "sharpness", "kept", "selection_reason"])
        topup_names = {p.name for p, _ in topup_selected}
        for p, s in sorted(scored, key=lambda x: x[0].name):
            if p.name in threshold_selected_names:
                reason = "threshold"
            elif p.name in topup_names:
                reason = "topup"
            else:
                reason = ""
            writer.writerow([p.name, f"{s:.6f}", "1" if p.name in selected_names else "0", reason])

    sharp_values = [s for _, s in scored]
    if min_index > 0 or max_index > 0:
        print(
            f"[ok] index filter: input={len(images)} candidates={len(scored)} "
            f"range=[{min_index if min_index > 0 else '-inf'},{max_index if max_index > 0 else '+inf'}]"
        )
    print(f"[ok] frame filter completed: keep {kept}/{len(scored)}")
    print(
        f"[ok] selected by threshold={len(threshold_selected_names)} "
        f"topup={len(topup_selected)} mode={args.topup_mode}"
    )
    print(f"[ok] sharpness min={min(sharp_values):.3f} max={max(sharp_values):.3f} mean={sum(sharp_values)/len(sharp_values):.3f}")
    print(f"[ok] metrics: {metrics_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
