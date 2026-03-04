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


def find_latest_ply(root: Path) -> Path | None:
    plys = sorted(root.rglob("*.ply"), key=lambda p: p.stat().st_mtime)
    if not plys:
        return None
    return plys[-1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export geometry for reconstruction backend (instant-ngp or mip-nerf360)."
    )
    parser.add_argument("--backend", default="instant_ngp", help="instant_ngp | mipnerf360")
    parser.add_argument("--python-bin", default="python")
    parser.add_argument("--scene", required=True)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--output-mesh", required=True)
    parser.add_argument("--ngp-script", required=True)
    parser.add_argument("--marching-cubes-res", type=int, default=256)
    parser.add_argument("--marching-cubes-density-thresh", type=float, default=2.5)

    parser.add_argument("--mip-export-bin", default="ns-export")
    parser.add_argument("--mip-output-dir", required=True)
    parser.add_argument("--mip-config", default="")
    parser.add_argument("--mip-config-link", required=True)
    parser.add_argument("--mip-export-method", default="poisson")
    parser.add_argument("--mip-export-dir", required=True)
    parser.add_argument("--mip-extra-args", default="")
    return parser.parse_args()


def export_instant_ngp(args: argparse.Namespace) -> int:
    cmd = [
        args.python_bin,
        args.ngp_script,
        "--scene",
        args.scene,
        "--mode",
        "nerf",
        "--load_snapshot",
        args.snapshot,
        "--save_mesh",
        args.output_mesh,
        "--marching_cubes_res",
        str(args.marching_cubes_res),
        "--marching_cubes_density_thresh",
        str(args.marching_cubes_density_thresh),
    ]
    return run_command(cmd)


def resolve_mip_config(args: argparse.Namespace) -> Path | None:
    if args.mip_config.strip():
        path = Path(args.mip_config).expanduser().resolve()
        if path.exists():
            return path
        return None

    link = Path(args.mip_config_link).expanduser().resolve()
    if link.exists():
        content = link.read_text(encoding="utf-8").strip()
        if content:
            p = Path(content).expanduser().resolve()
            if p.exists():
                return p

    output_dir = Path(args.mip_output_dir).expanduser().resolve()
    if output_dir.exists():
        return find_latest_config(output_dir)
    return None


def export_mipnerf360(args: argparse.Namespace) -> int:
    export_bin = args.mip_export_bin
    if shutil.which(export_bin) is None and not Path(export_bin).exists():
        print(f"[error] mip-nerf360 export binary not found: {export_bin}", file=sys.stderr)
        print("[hint] install nerfstudio (or set [mipnerf360].export_bin)", file=sys.stderr)
        return 1

    config = resolve_mip_config(args)
    if config is None:
        print("[error] unable to resolve mip-nerf360 config.yml", file=sys.stderr)
        print("[hint] run train stage first or set [mipnerf360].config_link/config path", file=sys.stderr)
        return 1

    output_mesh = Path(args.output_mesh).expanduser().resolve()
    export_dir = Path(args.mip_export_dir).expanduser().resolve()
    export_dir.mkdir(parents=True, exist_ok=True)
    output_mesh.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        export_bin,
        args.mip_export_method,
        "--load-config",
        str(config),
        "--output-dir",
        str(export_dir),
    ]
    if args.mip_extra_args.strip():
        cmd.extend(shlex.split(args.mip_extra_args))

    code = run_command(cmd)
    if code != 0:
        return code

    mesh = find_latest_ply(export_dir)
    if mesh is None:
        print(f"[error] no .ply exported under: {export_dir}", file=sys.stderr)
        return 1

    if mesh.resolve() != output_mesh.resolve():
        shutil.copy2(mesh, output_mesh)

    print(f"[ok] exported mesh: {mesh}")
    print(f"[ok] copied mesh to: {output_mesh}")
    return 0


def main() -> int:
    args = parse_args()
    backend = args.backend.strip().lower()
    if backend == "instant_ngp":
        return export_instant_ngp(args)
    if backend == "mipnerf360":
        return export_mipnerf360(args)

    print(f"[error] unsupported backend: {args.backend}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
