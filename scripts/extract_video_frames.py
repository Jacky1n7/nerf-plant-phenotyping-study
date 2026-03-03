#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".avi", ".m4v"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def parse_optional(value: str) -> str | None:
    text = value.strip()
    if text.lower() in {"", "none", "null"}:
        return None
    return text


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def discover_video(video_dir: Path) -> Path:
    candidates = sorted(
        p for p in video_dir.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_SUFFIXES and not p.name.startswith(".")
    )
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise FileNotFoundError(f"no video file found under: {video_dir}")
    raise RuntimeError(f"multiple videos found under {video_dir}; set --input-video explicitly")


def resolve_video(input_video: str, video_dir: Path) -> Path:
    if input_video.strip().lower() != "auto":
        candidate = Path(input_video).expanduser().resolve()
        if not candidate.exists():
            raise FileNotFoundError(f"video file not found: {candidate}")
        return candidate
    if not video_dir.exists():
        raise FileNotFoundError(f"video dir does not exist: {video_dir}")
    return discover_video(video_dir)


def remove_existing_images(output_dir: Path) -> int:
    removed = 0
    for path in output_dir.iterdir():
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
            path.unlink()
            removed += 1
    return removed


def count_images(output_dir: Path) -> int:
    return len(
        [
            p
            for p in output_dir.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES and not p.name.startswith(".")
        ]
    )


def build_ffmpeg_command(args: argparse.Namespace, video_path: Path, output_dir: Path) -> list[str]:
    filters = [f"fps={args.fps}"]

    if args.resize_width > 0 or args.resize_height > 0:
        width = args.resize_width if args.resize_width > 0 else -1
        height = args.resize_height if args.resize_height > 0 else -1
        filters.append(f"scale={width}:{height}:flags=lanczos")

    output_pattern = output_dir / f"{args.filename_prefix}_%06d.jpg"

    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", args.start_time, "-i", str(video_path)]

    end_time = parse_optional(args.end_time)
    if end_time is not None:
        cmd.extend(["-to", end_time])

    cmd.extend(["-vf", ",".join(filters)])

    if args.max_frames > 0:
        cmd.extend(["-frames:v", str(args.max_frames)])

    cmd.extend(
        [
            "-q:v",
            str(args.jpeg_quality),
            "-start_number",
            str(args.start_number),
            str(output_pattern),
        ]
    )
    return cmd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract images from a dataset video with ffmpeg.")
    parser.add_argument("--video-dir", required=True, help="Directory for raw videos.")
    parser.add_argument("--input-video", default="auto", help="Video file path or 'auto' for single-file discovery.")
    parser.add_argument("--output-dir", required=True, help="Directory to save extracted frames.")
    parser.add_argument("--fps", type=float, default=3.0, help="Sampling fps.")
    parser.add_argument("--start-time", default="00:00:00", help="ffmpeg -ss value.")
    parser.add_argument("--end-time", default="none", help="ffmpeg -to value, use 'none' for full video.")
    parser.add_argument("--max-frames", type=int, default=0, help="0 means unlimited.")
    parser.add_argument("--jpeg-quality", type=int, default=2, help="1-31, smaller means better quality.")
    parser.add_argument("--resize-width", type=int, default=-1, help="-1 keeps aspect ratio.")
    parser.add_argument("--resize-height", type=int, default=-1, help="-1 keeps aspect ratio.")
    parser.add_argument("--filename-prefix", default="frame", help="Output filename prefix.")
    parser.add_argument("--start-number", type=int, default=1, help="Output index start.")
    parser.add_argument("--overwrite", default="false", help="true/false: whether to clear output images first.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if shutil.which("ffmpeg") is None:
        print("[error] ffmpeg not found in PATH", file=sys.stderr)
        return 1

    if args.fps <= 0:
        print("[error] fps must be > 0", file=sys.stderr)
        return 1

    if not (1 <= args.jpeg_quality <= 31):
        print("[error] jpeg_quality must be in [1, 31]", file=sys.stderr)
        return 1

    video_dir = Path(args.video_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    overwrite = parse_bool(args.overwrite)

    existing = count_images(output_dir)
    if existing > 0 and not overwrite:
        print(f"[skip] {existing} images already exist in {output_dir}. Use overwrite=true to regenerate.")
        return 0

    if existing > 0 and overwrite:
        removed = remove_existing_images(output_dir)
        print(f"[info] removed {removed} existing images from {output_dir}")

    try:
        video_path = resolve_video(args.input_video, video_dir)
    except Exception as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1

    cmd = build_ffmpeg_command(args, video_path, output_dir)
    print("[info] video:", video_path)
    print("[info] output:", output_dir)
    print("[info] ffmpeg:", " ".join(cmd))

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"[error] ffmpeg failed with exit code {exc.returncode}", file=sys.stderr)
        return exc.returncode

    generated = count_images(output_dir)
    if generated == 0:
        print("[error] no frames were generated", file=sys.stderr)
        return 1

    print(f"[ok] extracted {generated} images")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
