#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp"}


def text_to_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def format_cmd(cmd: list[str]) -> str:
    return " ".join(shlex.quote(x) for x in cmd)


def run_command(cmd: list[str]) -> int:
    print(f"[exec] {format_cmd(cmd)}", flush=True)
    result = subprocess.run(cmd)
    return int(result.returncode)


def build_ngp_command(
    python_bin: str,
    ngp_script: Path,
    scene: Path,
    n_steps: int,
    snapshot: Path,
    load_snapshot: Path | None,
    screenshot_dir: Path | None,
    transforms: Path | None,
    screenshot_frame: int,
    screenshot_spp: int,
    width: int,
    height: int,
    near_distance: float,
    sharpen: float,
    exposure: float,
    train_mode: str,
    rfl_warmup_steps: int,
    rflrelax_begin_step: int,
    rflrelax_end_step: int,
) -> list[str]:
    cmd = [
        python_bin,
        str(ngp_script),
        "--scene",
        str(scene),
        "--n_steps",
        str(n_steps),
        "--save_snapshot",
        str(snapshot),
    ]
    if near_distance >= 0:
        cmd += ["--near_distance", str(near_distance)]
    if sharpen != 0:
        cmd += ["--sharpen", str(sharpen)]
    if exposure != 0:
        cmd += ["--exposure", str(exposure)]

    normalized_train_mode = train_mode.strip().lower()
    if normalized_train_mode not in {"nerf", "rfl", "rfl_relax", "rflrelax"}:
        raise ValueError(
            "--train-mode must be one of: nerf, rfl, rfl_relax (or rflrelax)"
        )

    cmd += [
        "--train_mode",
        normalized_train_mode,
        "--rfl_warmup_steps",
        str(rfl_warmup_steps),
        "--rflrelax_begin_step",
        str(rflrelax_begin_step),
        "--rflrelax_end_step",
        str(rflrelax_end_step),
    ]
    if load_snapshot is not None:
        cmd += ["--load_snapshot", str(load_snapshot)]

    if screenshot_dir is not None and transforms is not None:
        cmd += [
            "--screenshot_transforms",
            str(transforms),
            "--screenshot_frames",
            str(screenshot_frame),
            "--screenshot_dir",
            str(screenshot_dir),
            "--screenshot_spp",
            str(screenshot_spp),
            "--width",
            str(width),
            "--height",
            str(height),
        ]
    return cmd


def latest_image(path: Path) -> Path | None:
    candidates = [
        p for p in path.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS and not p.name.startswith(".")
    ]
    if not candidates:
        return None
    return sorted(candidates)[-1]


def make_video(ffmpeg_bin: str, frames_dir: Path, fps: int, output_path: Path) -> int:
    frame_pattern = frames_dir / "frame_*.*"
    cmd = [
        ffmpeg_bin,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-pattern_type",
        "glob",
        "-framerate",
        str(fps),
        "-i",
        str(frame_pattern),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(output_path),
    ]
    return run_command(cmd)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train instant-ngp with optional progress visualization frames.")
    parser.add_argument("--python-bin", default="python")
    parser.add_argument("--ngp-script", required=True, help="Path to instant-ngp scripts/run.py")
    parser.add_argument("--scene", required=True, help="Training scene directory")
    parser.add_argument("--steps", required=True, type=int, help="Total training steps")
    parser.add_argument("--snapshot", required=True, help="Output snapshot path")
    parser.add_argument("--transforms", required=True, help="Path to transforms.json (for screenshots)")
    parser.add_argument("--near-distance", type=float, default=-1.0)
    parser.add_argument("--sharpen", type=float, default=0.0)
    parser.add_argument("--exposure", type=float, default=0.0)
    parser.add_argument("--train-mode", default="rfl_relax", help="nerf | rfl | rfl_relax")
    parser.add_argument("--rfl-warmup-steps", type=int, default=1000)
    parser.add_argument("--rflrelax-begin-step", type=int, default=15000)
    parser.add_argument("--rflrelax-end-step", type=int, default=30000)

    parser.add_argument("--visualize", default="false", help="true/false")
    parser.add_argument("--chunk-steps", type=int, default=5000)
    parser.add_argument("--screenshot-frame", type=int, default=0)
    parser.add_argument("--screenshot-spp", type=int, default=8)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--vis-dir", required=True, help="Directory for training visualization outputs")

    parser.add_argument("--make-video", default="true", help="true/false")
    parser.add_argument("--video-fps", type=int, default=6)
    parser.add_argument("--video-output", required=True)
    parser.add_argument("--ffmpeg-bin", default="ffmpeg")
    parser.add_argument("--resume", action="store_true", help="Resume from existing snapshot if present")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.steps <= 0:
        print("[error] --steps must be > 0", file=sys.stderr)
        return 1

    if args.chunk_steps <= 0:
        print("[error] --chunk-steps must be > 0", file=sys.stderr)
        return 1
    if args.rfl_warmup_steps < 0:
        print("[error] --rfl-warmup-steps must be >= 0", file=sys.stderr)
        return 1
    if args.rflrelax_begin_step < 0 or args.rflrelax_end_step < 0:
        print("[error] --rflrelax-begin-step and --rflrelax-end-step must be >= 0", file=sys.stderr)
        return 1

    ngp_script = Path(args.ngp_script).expanduser().resolve()
    scene = Path(args.scene).expanduser().resolve()
    snapshot = Path(args.snapshot).expanduser().resolve()
    transforms = Path(args.transforms).expanduser().resolve()
    vis_dir = Path(args.vis_dir).expanduser().resolve()
    frames_dir = vis_dir / "frames"
    raw_dir = vis_dir / "raw"
    progress_csv = vis_dir / "progress_steps.csv"
    video_output = Path(args.video_output).expanduser().resolve()

    if not ngp_script.exists():
        print(f"[error] ngp script not found: {ngp_script}", file=sys.stderr)
        return 1
    if not scene.exists():
        print(f"[error] scene not found: {scene}", file=sys.stderr)
        return 1

    visualize = text_to_bool(args.visualize)
    if visualize and not transforms.exists():
        print(f"[error] transforms not found: {transforms}", file=sys.stderr)
        return 1

    snapshot.parent.mkdir(parents=True, exist_ok=True)

    if snapshot.exists() and not args.resume:
        snapshot.unlink()

    if not visualize:
        print("[info] training visualization disabled; running single-shot training", flush=True)
        cmd = build_ngp_command(
            python_bin=args.python_bin,
            ngp_script=ngp_script,
            scene=scene,
            n_steps=args.steps,
            snapshot=snapshot,
            load_snapshot=snapshot if args.resume and snapshot.exists() else None,
            screenshot_dir=None,
            transforms=None,
            screenshot_frame=args.screenshot_frame,
            screenshot_spp=args.screenshot_spp,
            width=args.width,
            height=args.height,
            near_distance=args.near_distance,
            sharpen=args.sharpen,
            exposure=args.exposure,
            train_mode=args.train_mode,
            rfl_warmup_steps=args.rfl_warmup_steps,
            rflrelax_begin_step=args.rflrelax_begin_step,
            rflrelax_end_step=args.rflrelax_end_step,
        )
        return run_command(cmd)

    print("[info] training visualization enabled", flush=True)
    print(f"[info] vis_dir={vis_dir}", flush=True)
    print(f"[info] chunk_steps={args.chunk_steps}", flush=True)
    vis_dir.mkdir(parents=True, exist_ok=True)
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    if raw_dir.exists():
        shutil.rmtree(raw_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    completed = 0
    frame_index = 0

    with progress_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["frame_index", "training_step"])

        while completed < args.steps:
            frame_index += 1
            chunk = min(args.chunk_steps, args.steps - completed)
            next_step = completed + chunk
            shot_dir = raw_dir / f"step_{next_step:07d}"
            shot_dir.mkdir(parents=True, exist_ok=True)

            load_snapshot = snapshot if (completed > 0 or (args.resume and snapshot.exists())) else None
            cmd = build_ngp_command(
                python_bin=args.python_bin,
                ngp_script=ngp_script,
                scene=scene,
                n_steps=chunk,
                snapshot=snapshot,
                load_snapshot=load_snapshot,
                screenshot_dir=shot_dir,
                transforms=transforms,
                screenshot_frame=args.screenshot_frame,
                screenshot_spp=args.screenshot_spp,
                width=args.width,
                height=args.height,
                near_distance=args.near_distance,
                sharpen=args.sharpen,
                exposure=args.exposure,
                train_mode=args.train_mode,
                rfl_warmup_steps=args.rfl_warmup_steps,
                rflrelax_begin_step=args.rflrelax_begin_step,
                rflrelax_end_step=args.rflrelax_end_step,
            )

            print(f"[info] chunk {frame_index}: steps {completed + 1}-{next_step}", flush=True)
            code = run_command(cmd)
            if code != 0:
                return code

            image = latest_image(shot_dir)
            if image is None:
                print(f"[warn] no screenshot generated for step={next_step}", flush=True)
            else:
                frame_path = frames_dir / f"frame_{frame_index:04d}{image.suffix.lower()}"
                shutil.copy2(image, frame_path)
                writer.writerow([frame_index, next_step])

            completed = next_step

    make_video_flag = text_to_bool(args.make_video)
    if not make_video_flag:
        print("[info] video generation disabled", flush=True)
        return 0

    vis_frames = sorted(frames_dir.glob("frame_*.*"))
    if len(vis_frames) < 2:
        print("[warn] less than 2 frames found; skip progress.mp4 generation", flush=True)
        return 0

    video_output.parent.mkdir(parents=True, exist_ok=True)
    code = make_video(args.ffmpeg_bin, frames_dir, args.video_fps, video_output)
    if code != 0:
        return code
    print(f"[ok] training progress video: {video_output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
