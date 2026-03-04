#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import tomllib

ROOT_DIR = Path(__file__).resolve().parents[1]


def load_toml(path: Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


def as_abs(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        path = ROOT_DIR / path
    return path.resolve()


def color(text: str, code: str) -> str:
    if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
        return text
    return f"\033[{code}m{text}\033[0m"


def info(msg: str) -> None:
    print(color(f"ℹ️  {msg}", "36"))


def ok(msg: str) -> None:
    print(color(f"✅ {msg}", "32"))


def warn(msg: str) -> None:
    print(color(f"⚠️  {msg}", "33"))


def err(msg: str) -> None:
    print(color(f"❌ {msg}", "31"), file=sys.stderr)


def section(title: str) -> None:
    line = "=" * 18
    print(color(f"\n{line} {title} {line}", "1;34"))


def resolve_dataset_name(config: dict, dataset_arg: str | None) -> str:
    if dataset_arg:
        return dataset_arg
    return str(config.get("project", {}).get("default_dataset", "maize_plant_01"))


def load_paths(config_path: Path, dataset: str) -> dict[str, Path | str]:
    config = load_toml(config_path)
    dataset_cfg_path = ROOT_DIR / "configs" / "datasets" / f"{dataset}.toml"
    if not dataset_cfg_path.exists():
        raise FileNotFoundError(f"数据集配置不存在: {dataset_cfg_path}")

    dataset_cfg = load_toml(dataset_cfg_path)
    paths = config.get("paths", {})
    dataset_info = dataset_cfg.get("dataset", {})

    workspace_dir = as_abs(dataset_info.get("workspace_dir", f"data/processed/{dataset}"))
    outputs_dataset_dir = as_abs(dataset_info.get("outputs_dataset_dir", f"outputs/{dataset}"))
    instant_ngp_dir = as_abs(paths.get("instant_ngp_dir", "third_party/instant-ngp"))
    python_bin = str(paths.get("python_bin", "python"))

    return {
        "python_bin": python_bin,
        "ngp_script": (instant_ngp_dir / "scripts" / "run.py"),
        "scene": workspace_dir,
        "snapshot": outputs_dataset_dir / "instant-ngp.msgpack",
        "transforms": workspace_dir / "transforms.json",
    }


def transforms_frame_count(transforms_path: Path) -> int | None:
    if not transforms_path.exists():
        return None
    try:
        data = json.loads(transforms_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    frames = data.get("frames")
    if not isinstance(frames, list):
        return None
    return len(frames)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="中文增强版 instant-ngp GUI 启动器")
    parser.add_argument("--config", default="configs/pipeline.toml", help="Pipeline 配置文件路径")
    parser.add_argument("--dataset", default=None, help="数据集名称，例如 maize_plant_01")
    parser.add_argument("--python-bin", default=None, help="Python 可执行文件，默认读取 pipeline.toml")
    parser.add_argument("--ngp-script", default=None, help="instant-ngp run.py 路径")
    parser.add_argument("--scene", default=None, help="场景目录（包含 transforms.json）")
    parser.add_argument("--snapshot", default=None, help="训练快照 .msgpack 路径")
    parser.add_argument("--dry-run", action="store_true", help="只展示命令，不实际启动 GUI")
    parser.add_argument(
        "--extra-args",
        default="",
        help="附加参数字符串，会追加到 run.py 后面",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = as_abs(args.config)
    if not config_path.exists():
        err(f"配置文件不存在: {config_path}")
        return 1

    config = load_toml(config_path)
    dataset = resolve_dataset_name(config, args.dataset)

    try:
        defaults = load_paths(config_path, dataset)
    except FileNotFoundError as exc:
        err(str(exc))
        return 1

    python_bin = args.python_bin or str(defaults["python_bin"])
    ngp_script = as_abs(args.ngp_script) if args.ngp_script else Path(defaults["ngp_script"])
    scene = as_abs(args.scene) if args.scene else Path(defaults["scene"])
    snapshot = as_abs(args.snapshot) if args.snapshot else Path(defaults["snapshot"])
    transforms = scene / "transforms.json"

    section("Instant-NGP GUI 启动信息")
    info(f"数据集: {dataset}")
    info(f"Python: {python_bin}")
    info(f"脚本: {ngp_script}")
    info(f"场景目录: {scene}")
    info(f"快照文件: {snapshot}")
    info(f"工作目录: {ROOT_DIR}")

    display = os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    if display:
        ok(f"检测到图形会话: {display}")
    else:
        warn("未检测到 DISPLAY/WAYLAND_DISPLAY，GUI 可能无法弹窗。")

    if not ngp_script.exists():
        err(f"run.py 不存在: {ngp_script}")
        return 1
    ok("run.py 已找到")

    if not scene.exists():
        err(f"场景目录不存在: {scene}")
        return 1
    ok("场景目录已找到")

    if not snapshot.exists():
        err(f"快照不存在: {snapshot}")
        info("请先完成训练，或通过 --snapshot 指定已有快照。")
        return 1
    ok("快照文件已找到")

    frame_count = transforms_frame_count(transforms)
    if frame_count is None:
        warn(f"未能读取 transforms 或文件不存在: {transforms}")
    else:
        ok(f"transforms 帧数: {frame_count}")

    cmd = [
        python_bin,
        str(ngp_script),
        "--scene",
        str(scene),
        "--load_snapshot",
        str(snapshot),
        "--gui",
    ]
    if args.extra_args.strip():
        cmd.extend(shlex.split(args.extra_args))

    section("即将执行的命令")
    print(color("🚀 " + shlex.join(cmd), "35"))

    if args.dry_run:
        info("dry-run 模式，未实际启动 GUI。")
        return 0

    section("运行中")
    info("正在启动 GUI，关闭窗口后本命令会退出。")

    try:
        proc = subprocess.Popen(cmd, cwd=ROOT_DIR)
        return int(proc.wait())
    except KeyboardInterrupt:
        warn("收到中断信号，已停止启动器。")
        return 130
    except FileNotFoundError as exc:
        err(f"启动失败: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
