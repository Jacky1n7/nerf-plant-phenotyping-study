#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


def format_cmd(cmd: list[str]) -> str:
    return " ".join(shlex.quote(x) for x in cmd)


def run_command(cmd: list[str]) -> int:
    print(f"[exec] {format_cmd(cmd)}", flush=True)
    result = subprocess.run(cmd)
    return int(result.returncode)


def find_latest_config(root: Path) -> Path | None:
    configs = sorted(root.rglob("config.yml"), key=lambda p: p.stat().st_mtime)
    if not configs:
        return None
    return configs[-1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train reconstruction backend (instant-ngp or mip-nerf360-compatible backend)."
    )
    parser.add_argument("--backend", default="instant_ngp", help="instant_ngp | mipnerf360")
    parser.add_argument("--python-bin", default="python")
    parser.add_argument("--scene", required=True)
    parser.add_argument("--steps", required=True, type=int)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--transforms", required=True)

    parser.add_argument("--ngp-script", required=True)
    parser.add_argument("--near-distance", type=float, default=-1.0)
    parser.add_argument("--sharpen", type=float, default=0.0)
    parser.add_argument("--exposure", type=float, default=0.0)
    parser.add_argument("--train-mode", default="nerf")
    parser.add_argument("--rfl-warmup-steps", type=int, default=1000)
    parser.add_argument("--rflrelax-begin-step", type=int, default=15000)
    parser.add_argument("--rflrelax-end-step", type=int, default=30000)
    parser.add_argument("--visualize", default="false")
    parser.add_argument("--chunk-steps", type=int, default=5000)
    parser.add_argument("--screenshot-frame", type=int, default=0)
    parser.add_argument("--screenshot-spp", type=int, default=8)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--vis-dir", required=True)
    parser.add_argument("--make-video", default="true")
    parser.add_argument("--video-fps", type=int, default=6)
    parser.add_argument("--video-output", required=True)

    parser.add_argument("--mip-train-bin", default="ns-train")
    parser.add_argument("--mip-method", default="nerfacto")
    parser.add_argument("--mip-output-dir", required=True)
    parser.add_argument("--mip-config-link", required=True)
    parser.add_argument("--mip-extra-args", default="")
    return parser.parse_args()


def train_instant_ngp(args: argparse.Namespace) -> int:
    script_dir = Path(__file__).resolve().parent
    train_script = script_dir / "train_with_visualization.py"
    cmd = [
        args.python_bin,
        str(train_script),
        "--python-bin",
        args.python_bin,
        "--ngp-script",
        args.ngp_script,
        "--scene",
        args.scene,
        "--steps",
        str(args.steps),
        "--snapshot",
        args.snapshot,
        "--transforms",
        args.transforms,
        "--near-distance",
        str(args.near_distance),
        "--sharpen",
        str(args.sharpen),
        "--exposure",
        str(args.exposure),
        "--train-mode",
        args.train_mode,
        "--rfl-warmup-steps",
        str(args.rfl_warmup_steps),
        "--rflrelax-begin-step",
        str(args.rflrelax_begin_step),
        "--rflrelax-end-step",
        str(args.rflrelax_end_step),
        "--visualize",
        args.visualize,
        "--chunk-steps",
        str(args.chunk_steps),
        "--screenshot-frame",
        str(args.screenshot_frame),
        "--screenshot-spp",
        str(args.screenshot_spp),
        "--width",
        str(args.width),
        "--height",
        str(args.height),
        "--vis-dir",
        args.vis_dir,
        "--make-video",
        args.make_video,
        "--video-fps",
        str(args.video_fps),
        "--video-output",
        args.video_output,
    ]
    return run_command(cmd)


def train_mipnerf360(args: argparse.Namespace) -> int:
    train_bin = args.mip_train_bin
    if shutil.which(train_bin) is None and not Path(train_bin).exists():
        print(f"[error] mip-nerf360 train binary not found: {train_bin}", file=sys.stderr)
        print("[hint] install nerfstudio (or set [mipnerf360].train_bin)", file=sys.stderr)
        return 1

    scene = Path(args.scene).expanduser().resolve()
    transforms = Path(args.transforms).expanduser().resolve()
    output_dir = Path(args.mip_output_dir).expanduser().resolve()
    config_link = Path(args.mip_config_link).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    config_link.parent.mkdir(parents=True, exist_ok=True)

    if not scene.exists():
        print(f"[error] scene dir not found: {scene}", file=sys.stderr)
        return 1
    if not transforms.exists():
        print(f"[error] transforms not found: {transforms}", file=sys.stderr)
        return 1

    cmd = [
        train_bin,
        args.mip_method,
        "--data",
        str(scene),
        "--output-dir",
        str(output_dir),
        "--max-num-iterations",
        str(args.steps),
    ]
    if args.mip_extra_args.strip():
        cmd.extend(shlex.split(args.mip_extra_args))

    code = run_command(cmd)
    if code != 0:
        return code

    latest_config = find_latest_config(output_dir)
    if latest_config is None:
        print(f"[error] no config.yml found under: {output_dir}", file=sys.stderr)
        return 1

    config_link.write_text(str(latest_config) + "\n", encoding="utf-8")
    print(f"[ok] mip-nerf360 config: {latest_config}")
    print(f"[ok] config link: {config_link}")
    return 0


def main() -> int:
    args = parse_args()
    backend = args.backend.strip().lower()
    if args.steps <= 0:
        print("[error] --steps must be > 0", file=sys.stderr)
        return 1

    if backend == "instant_ngp":
        return train_instant_ngp(args)
    if backend == "mipnerf360":
        return train_mipnerf360(args)

    print(f"[error] unsupported backend: {args.backend}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
