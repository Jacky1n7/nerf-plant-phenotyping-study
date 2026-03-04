#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Select the best COLMAP sparse model by registered image count."
    )
    parser.add_argument("--sparse-root", required=True, help="Path to colmap/sparse directory.")
    parser.add_argument(
        "--output-path-file",
        required=True,
        help="File path to write selected model directory.",
    )
    parser.add_argument("--colmap-bin", default="colmap", help="COLMAP executable.")
    return parser.parse_args()


def list_model_dirs(sparse_root: Path) -> list[Path]:
    if not sparse_root.exists():
        return []
    dirs: list[Path] = []
    for p in sorted(sparse_root.iterdir()):
        if not p.is_dir():
            continue
        if not (p / "images.bin").exists():
            continue
        dirs.append(p)
    return dirs


def analyze_model(colmap_bin: str, model_dir: Path) -> tuple[int, int]:
    proc = subprocess.run(
        [colmap_bin, "model_analyzer", "--path", str(model_dir)],
        check=False,
        capture_output=True,
        text=True,
    )
    output = (proc.stdout or "") + "\n" + (proc.stderr or "")

    reg_match = re.search(r"Registered images:\s*(\d+)", output)
    points_match = re.search(r"Points:\s*(\d+)", output)

    if reg_match is None:
        raise RuntimeError(f"failed to parse registered image count from {model_dir}")

    registered = int(reg_match.group(1))
    points = int(points_match.group(1)) if points_match is not None else 0
    return registered, points


def main() -> int:
    args = parse_args()
    sparse_root = Path(args.sparse_root).expanduser().resolve()
    output_path_file = Path(args.output_path_file).expanduser().resolve()

    model_dirs = list_model_dirs(sparse_root)
    if not model_dirs:
        print(f"[error] no sparse model dirs found under: {sparse_root}", file=sys.stderr)
        return 1

    scored: list[tuple[Path, int, int]] = []
    for model_dir in model_dirs:
        try:
            registered, points = analyze_model(args.colmap_bin, model_dir)
        except Exception as exc:
            print(f"[warn] skipping {model_dir}: {exc}")
            continue
        scored.append((model_dir, registered, points))
        print(f"[info] model={model_dir.name} registered={registered} points={points}")

    if not scored:
        print("[error] failed to analyze all sparse model dirs", file=sys.stderr)
        return 1

    best_dir, best_registered, best_points = sorted(
        scored,
        key=lambda x: (x[1], x[2], x[0].name),
        reverse=True,
    )[0]

    output_path_file.parent.mkdir(parents=True, exist_ok=True)
    output_path_file.write_text(str(best_dir) + "\n", encoding="utf-8")

    print(
        f"[ok] selected sparse model: {best_dir} "
        f"(registered={best_registered}, points={best_points})"
    )
    print(f"[ok] wrote model path file: {output_path_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
