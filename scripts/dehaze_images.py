#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

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


def min_filter_2d(image: np.ndarray, kernel_size: int) -> np.ndarray:
    if kernel_size <= 1:
        return image.copy()
    if kernel_size % 2 == 0:
        raise ValueError("kernel_size must be odd.")

    h, w = image.shape
    pad = kernel_size // 2

    padded_h = np.pad(image, ((0, 0), (pad, pad)), mode="edge")
    row_windows = [padded_h[:, i : i + w] for i in range(kernel_size)]
    row_min = np.minimum.reduce(row_windows)

    padded_v = np.pad(row_min, ((pad, pad), (0, 0)), mode="edge")
    col_windows = [padded_v[i : i + h, :] for i in range(kernel_size)]
    return np.minimum.reduce(col_windows)


def dark_channel(image: np.ndarray, window_size: int) -> np.ndarray:
    channel_min = np.min(image, axis=2)
    return min_filter_2d(channel_min, window_size)


def estimate_atmospheric_light(
    image: np.ndarray, dark: np.ndarray, top_percent: float
) -> np.ndarray:
    if not (0 < top_percent <= 1):
        raise ValueError("top_percent must be in (0, 1].")
    flat_dark = dark.reshape(-1)
    n = max(1, int(flat_dark.size * top_percent))
    indices = np.argpartition(flat_dark, -n)[-n:]
    flat_rgb = image.reshape(-1, 3)[indices]
    return flat_rgb[np.argmax(np.sum(flat_rgb, axis=1))]


def box_filter(image: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return image.copy()
    kernel = 2 * radius + 1
    padded = np.pad(image, ((radius, radius), (radius, radius)), mode="reflect")
    integral = np.pad(np.cumsum(np.cumsum(padded, axis=0), axis=1), ((1, 0), (1, 0)), mode="constant")
    return (
        integral[kernel:, kernel:]
        - integral[:-kernel, kernel:]
        - integral[kernel:, :-kernel]
        + integral[:-kernel, :-kernel]
    )


def guided_filter(guidance: np.ndarray, target: np.ndarray, radius: int, eps: float) -> np.ndarray:
    n = box_filter(np.ones_like(guidance, dtype=np.float32), radius)
    n = np.maximum(n, 1e-6)
    mean_i = box_filter(guidance, radius) / n
    mean_p = box_filter(target, radius) / n
    corr_i = box_filter(guidance * guidance, radius) / n
    corr_ip = box_filter(guidance * target, radius) / n
    var_i = np.maximum(corr_i - mean_i * mean_i, 0.0)
    cov_ip = corr_ip - mean_i * mean_p
    a = cov_ip / np.maximum(var_i + eps, 1e-6)
    b = mean_p - a * mean_i
    mean_a = box_filter(a, radius) / n
    mean_b = box_filter(b, radius) / n
    return mean_a * guidance + mean_b


def dehaze(
    image: np.ndarray,
    omega: float,
    window_size: int,
    min_transmission: float,
    top_percent: float,
    guided_radius: int,
    guided_eps: float,
    gamma: float,
) -> np.ndarray:
    if window_size < 3 or window_size % 2 == 0:
        raise ValueError("window_size must be odd and >= 3.")
    if not (0.0 < omega <= 1.0):
        raise ValueError("omega must be in (0, 1].")
    if not (0.0 < min_transmission < 1.0):
        raise ValueError("min_transmission must be in (0, 1).")
    if guided_eps <= 0:
        raise ValueError("guided_eps must be > 0.")
    if gamma <= 0:
        raise ValueError("gamma must be > 0.")

    dark = dark_channel(image, window_size)
    airlight = estimate_atmospheric_light(image, dark, top_percent).astype(np.float32)

    normalized = image / np.maximum(airlight.reshape(1, 1, 3), 1e-6)
    transmission = 1.0 - omega * dark_channel(normalized, window_size)

    if guided_radius > 0:
        guidance = np.mean(image, axis=2).astype(np.float32)
        transmission = guided_filter(guidance, transmission.astype(np.float32), guided_radius, guided_eps)

    transmission = np.nan_to_num(
        transmission,
        nan=min_transmission,
        posinf=1.0,
        neginf=min_transmission,
    )
    transmission = np.clip(transmission, min_transmission, 1.0)
    recovered = (image - airlight.reshape(1, 1, 3)) / transmission[..., None] + airlight.reshape(1, 1, 3)
    recovered = np.nan_to_num(recovered, nan=0.0, posinf=1.0, neginf=0.0)
    recovered = np.clip(recovered, 0.0, 1.0)
    if gamma != 1.0:
        recovered = np.power(recovered, gamma)
    return np.clip(recovered, 0.0, 1.0)


def process_image(path: Path, output_path: Path, args: argparse.Namespace) -> None:
    image_bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise ValueError("cv2.imread failed")
    image = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0

    recovered = dehaze(
        image=image,
        omega=args.omega,
        window_size=args.window_size,
        min_transmission=args.min_transmission,
        top_percent=args.atmosphere_top_percent,
        guided_radius=args.guided_radius,
        guided_eps=args.guided_eps,
        gamma=args.gamma,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    out_u8 = np.clip(np.round(recovered * 255.0), 0, 255).astype(np.uint8)
    out_bgr = cv2.cvtColor(out_u8, cv2.COLOR_RGB2BGR)
    if output_path.suffix.lower() in {".jpg", ".jpeg"}:
        ok = cv2.imwrite(str(output_path), out_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), args.jpeg_quality])
    else:
        ok = cv2.imwrite(str(output_path), out_bgr)
    if not ok:
        raise ValueError("cv2.imwrite failed")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Remove haze/fog in image directory using dark channel prior.")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--enabled", default="true", help="true/false")
    parser.add_argument("--overwrite", default="false", help="true/false")
    parser.add_argument("--omega", type=float, default=0.95)
    parser.add_argument("--window-size", type=int, default=15)
    parser.add_argument("--min-transmission", type=float, default=0.1)
    parser.add_argument("--atmosphere-top-percent", type=float, default=0.001)
    parser.add_argument("--guided-radius", type=int, default=24)
    parser.add_argument("--guided-eps", type=float, default=1e-3)
    parser.add_argument("--gamma", type=float, default=1.0)
    parser.add_argument("--jpeg-quality", type=int, default=95)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if cv2 is None:
        print(f"[error] opencv-python is required for dehazing: {CV2_IMPORT_ERROR}", file=sys.stderr)
        return 1

    enabled = text_to_bool(args.enabled)
    if not enabled:
        print("[info] dehaze disabled by config; skipping.")
        return 0

    input_dir = Path(args.input_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    overwrite = text_to_bool(args.overwrite)

    if not input_dir.exists():
        print(f"[error] input dir not found: {input_dir}", file=sys.stderr)
        return 1

    images = list_images(input_dir)
    if not images:
        print(f"[error] no images found in: {input_dir}", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    if overwrite:
        for old in list_images(output_dir):
            old.unlink()

    total = len(images)
    print(f"[info] dehaze start: {total} images")
    print(f"[info] input={input_dir}")
    print(f"[info] output={output_dir}")

    for idx, image_path in enumerate(images, start=1):
        output_path = output_dir / image_path.name
        if output_path.exists() and not overwrite:
            continue
        try:
            process_image(image_path, output_path, args)
        except Exception as exc:
            print(f"[error] failed: {image_path.name} ({exc})", file=sys.stderr)
            return 1

        if idx % 20 == 0 or idx == total:
            print(f"[info] processed {idx}/{total}")

    print("[ok] dehaze completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
