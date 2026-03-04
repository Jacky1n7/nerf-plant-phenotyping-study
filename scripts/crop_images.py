#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

try:
    import cv2
except Exception as exc:  # pragma: no cover - dependency check
    cv2 = None
    CV2_IMPORT_ERROR = exc
else:
    CV2_IMPORT_ERROR = None

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


def clamp_int(value: float, low: int, high: int) -> int:
    return int(min(max(value, low), high))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crop all dataset images with a fixed ROI.")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--enabled", default="false", help="true/false")
    parser.add_argument("--overwrite", default="true", help="true/false")
    parser.add_argument("--x-min-ratio", type=float, default=0.0)
    parser.add_argument("--x-max-ratio", type=float, default=1.0)
    parser.add_argument("--y-min-ratio", type=float, default=0.0)
    parser.add_argument("--y-max-ratio", type=float, default=1.0)
    parser.add_argument(
        "--mask-right-ratio",
        type=float,
        default=0.0,
        help="Mask right-side ratio of cropped image in the lower region. 0 disables masking.",
    )
    parser.add_argument(
        "--mask-bottom-ratio",
        type=float,
        default=0.0,
        help="Mask bottom ratio of cropped image in the right-side region. 0 disables masking.",
    )
    return parser.parse_args()


def validate_ratios(args: argparse.Namespace) -> str | None:
    checks = [
        ("x-min-ratio", args.x_min_ratio),
        ("x-max-ratio", args.x_max_ratio),
        ("y-min-ratio", args.y_min_ratio),
        ("y-max-ratio", args.y_max_ratio),
    ]
    for name, value in checks:
        if not (0.0 <= value <= 1.0):
            return f"--{name} must be in [0, 1], got {value}"

    if not (args.x_min_ratio < args.x_max_ratio):
        return "--x-min-ratio must be < --x-max-ratio"
    if not (args.y_min_ratio < args.y_max_ratio):
        return "--y-min-ratio must be < --y-max-ratio"

    if not (0.0 <= args.mask_right_ratio < 1.0):
        return f"--mask-right-ratio must be in [0, 1), got {args.mask_right_ratio}"
    if not (0.0 <= args.mask_bottom_ratio < 1.0):
        return f"--mask-bottom-ratio must be in [0, 1), got {args.mask_bottom_ratio}"

    if (args.mask_right_ratio == 0.0) != (args.mask_bottom_ratio == 0.0):
        return "--mask-right-ratio and --mask-bottom-ratio must both be 0 or both > 0"
    return None


def copy_passthrough(images: list[Path], output_dir: Path, overwrite: bool) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for p in images:
        target = output_dir / p.name
        if target.exists() and not overwrite:
            continue
        shutil.copy2(p, target)
        copied += 1
    return copied


def main() -> int:
    args = parse_args()
    enabled = text_to_bool(args.enabled)
    overwrite = text_to_bool(args.overwrite)

    if cv2 is None:
        print(f"[error] opencv-python is required for crop stage: {CV2_IMPORT_ERROR}", file=sys.stderr)
        return 1

    ratio_error = validate_ratios(args)
    if ratio_error:
        print(f"[error] {ratio_error}", file=sys.stderr)
        return 1

    input_dir = Path(args.input_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    if not input_dir.exists():
        print(f"[error] input dir not found: {input_dir}", file=sys.stderr)
        return 1

    images = list_images(input_dir)
    if not images:
        print(f"[error] no images found in: {input_dir}", file=sys.stderr)
        return 1

    if not enabled:
        copied = copy_passthrough(images, output_dir, overwrite)
        print(f"[info] crop stage disabled; copied {copied} images.")
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    if overwrite:
        for old in list_images(output_dir):
            old.unlink()

    x0 = x1 = y0 = y1 = None
    mask_px = None
    processed = 0

    for p in images:
        img = cv2.imread(str(p), cv2.IMREAD_COLOR)
        if img is None:
            print(f"[error] failed to read image: {p}", file=sys.stderr)
            return 1

        h, w = img.shape[:2]
        cx0 = clamp_int(round(args.x_min_ratio * w), 0, w - 1)
        cx1 = clamp_int(round(args.x_max_ratio * w), cx0 + 1, w)
        cy0 = clamp_int(round(args.y_min_ratio * h), 0, h - 1)
        cy1 = clamp_int(round(args.y_max_ratio * h), cy0 + 1, h)

        cropped = img[cy0:cy1, cx0:cx1]
        if cropped.size == 0:
            print(f"[error] empty crop for {p.name}", file=sys.stderr)
            return 1

        if args.mask_right_ratio > 0 and args.mask_bottom_ratio > 0:
            ch, cw = cropped.shape[:2]
            mx0 = clamp_int(round((1.0 - args.mask_right_ratio) * cw), 0, cw - 1)
            my0 = clamp_int(round((1.0 - args.mask_bottom_ratio) * ch), 0, ch - 1)
            cropped[my0:ch, mx0:cw] = 0
            mask_px = (mx0, my0, cw, ch)

        ok = cv2.imwrite(str(output_dir / p.name), cropped)
        if not ok:
            print(f"[error] failed to write cropped image: {p.name}", file=sys.stderr)
            return 1

        x0, x1, y0, y1 = cx0, cx1, cy0, cy1
        processed += 1

    print(f"[ok] crop stage completed: {processed}/{len(images)} images")
    print(f"[ok] crop pixels x=[{x0},{x1}) y=[{y0},{y1})")
    print(
        f"[ok] crop ratios x=[{args.x_min_ratio:.3f},{args.x_max_ratio:.3f}] "
        f"y=[{args.y_min_ratio:.3f},{args.y_max_ratio:.3f}]"
    )
    if mask_px is not None:
        mx0, my0, cw, ch = mask_px
        print(
            f"[ok] mask rectangle pixels x=[{mx0},{cw}) y=[{my0},{ch}) "
            f"(right={args.mask_right_ratio:.3f}, bottom={args.mask_bottom_ratio:.3f})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
