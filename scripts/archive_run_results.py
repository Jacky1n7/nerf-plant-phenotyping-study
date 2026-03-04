#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path


def text_to_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Archive pipeline outputs for each run.")
    parser.add_argument("--enabled", default="true", help="true/false")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--outputs-dir", required=True)
    parser.add_argument("--workspace-dir", required=True)
    parser.add_argument("--run-log", required=True)
    parser.add_argument("--archive-root", required=True)
    parser.add_argument("--include-training-vis", default="true", help="true/false")
    parser.add_argument("--include-workspace-meta", default="true", help="true/false")
    return parser.parse_args()


def next_archive_dir(root: Path, dataset: str) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    base = root / f"{dataset}_{stamp}"
    if not base.exists():
        return base
    for idx in range(2, 100):
        candidate = root / f"{dataset}_{stamp}_{idx:02d}"
        if not candidate.exists():
            return candidate
    raise RuntimeError("failed to allocate archive folder name")


def copy_file_if_exists(src: Path, dst: Path, copied: list[str]) -> None:
    if not src.exists() or not src.is_file():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    copied.append(str(dst))


def copy_dir_if_exists(src: Path, dst: Path, copied: list[str]) -> None:
    if not src.exists() or not src.is_dir():
        return
    shutil.copytree(src, dst)
    copied.append(str(dst))


def main() -> int:
    args = parse_args()
    enabled = text_to_bool(args.enabled)
    if not enabled:
        print("[信息] 结果归档已禁用，跳过。")
        return 0

    project_root = Path(args.project_root).expanduser().resolve()
    outputs_dir = Path(args.outputs_dir).expanduser().resolve()
    workspace_dir = Path(args.workspace_dir).expanduser().resolve()
    run_log = Path(args.run_log).expanduser().resolve()
    archive_root = Path(args.archive_root).expanduser().resolve()
    include_training_vis = text_to_bool(args.include_training_vis)
    include_workspace_meta = text_to_bool(args.include_workspace_meta)

    if not outputs_dir.exists():
        print(f"[错误] 输出目录不存在: {outputs_dir}", file=sys.stderr)
        return 1

    archive_root.mkdir(parents=True, exist_ok=True)
    target_dir = next_archive_dir(archive_root, args.dataset)
    outputs_archive = target_dir / "outputs"
    meta_archive = target_dir / "meta"
    outputs_archive.mkdir(parents=True, exist_ok=True)
    meta_archive.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []

    # Core artifacts from outputs dir.
    for name in ("instant-ngp.msgpack", "mesh.ply", "dense_point_cloud.ply", "traits.csv"):
        copy_file_if_exists(outputs_dir / name, outputs_archive / name, copied)

    if include_training_vis:
        copy_dir_if_exists(outputs_dir / "training_vis", outputs_archive / "training_vis", copied)

    # Config and logs.
    copy_file_if_exists(
        project_root / "configs" / "datasets" / f"{args.dataset}.toml",
        meta_archive / "dataset_config.toml",
        copied,
    )
    copy_file_if_exists(project_root / "configs" / "pipeline.toml", meta_archive / "pipeline.toml", copied)
    copy_file_if_exists(run_log, meta_archive / "pipeline.log", copied)

    if include_workspace_meta:
        for name in ("transforms.json", "frame_filter_metrics.csv", "colmap_best_model_path.txt"):
            copy_file_if_exists(workspace_dir / name, meta_archive / name, copied)
        copy_dir_if_exists(workspace_dir / "colmap_text", meta_archive / "colmap_text", copied)

    manifest = {
        "dataset": args.dataset,
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "source_outputs_dir": str(outputs_dir),
        "source_workspace_dir": str(workspace_dir),
        "source_run_log": str(run_log),
        "archive_dir": str(target_dir),
        "include_training_vis": include_training_vis,
        "include_workspace_meta": include_workspace_meta,
        "copied_items": copied,
    }

    manifest_path = target_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"[完成] 本次运行结果已归档: {target_dir}")
    print(f"[完成] 共归档 {len(copied)} 项，清单: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
