#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def resolve_existing_path(raw_path: str, transforms_dir: Path, project_root: Path) -> Path | None:
    path = Path(raw_path)
    candidates: list[Path]
    if path.is_absolute():
        candidates = [path]
    else:
        candidates = [(transforms_dir / path).resolve(), (project_root / path).resolve()]

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def normalize_rel_path(target: Path, base_dir: Path) -> str:
    rel = Path(os.path.relpath(target, start=base_dir)).as_posix()
    if not rel.startswith("."):
        rel = f"./{rel}"
    return rel


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize file_path entries in transforms.json so instant-ngp can locate images."
    )
    parser.add_argument("--transforms", required=True, help="Path to transforms.json")
    parser.add_argument("--project-root", default=".", help="Project root used to resolve legacy paths")
    parser.add_argument("--dry-run", action="store_true", help="Show summary only, do not write file")
    args = parser.parse_args()

    transforms_path = Path(args.transforms).resolve()
    project_root = Path(args.project_root).resolve()
    if not transforms_path.exists():
        print(f"[error] transforms file not found: {transforms_path}")
        return 1

    with transforms_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    frames = data.get("frames", [])
    if not isinstance(frames, list) or not frames:
        print("[error] no frames found in transforms.json")
        return 1

    transforms_dir = transforms_path.parent
    updated = 0
    missing = 0

    for frame in frames:
        raw = frame.get("file_path")
        if not raw:
            missing += 1
            continue

        resolved = resolve_existing_path(str(raw), transforms_dir, project_root)
        if resolved is None:
            missing += 1
            continue

        normalized = normalize_rel_path(resolved, transforms_dir)
        if normalized != raw:
            frame["file_path"] = normalized
            updated += 1

    print(f"[info] frames={len(frames)} updated={updated} missing={missing}")
    if missing > 0:
        print("[error] unresolved image paths remain in transforms.json")
        return 1

    if args.dry_run:
        print("[ok] dry-run finished")
        return 0

    with transforms_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    print(f"[ok] wrote {transforms_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
