#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import tomllib

ROOT_DIR = Path(__file__).resolve().parents[1]
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".avi", ".m4v"}
STAGE_LABELS = {
    "prepare_dirs": "准备目录",
    "extract_video_frames": "视频抽帧",
    "crop_images": "图像裁剪",
    "filter_frames": "帧筛选",
    "dehaze_images": "去云雾",
    "colmap": "COLMAP重建",
    "colmap_to_text": "模型转文本",
    "transforms": "生成transforms",
    "train_instant_ngp": "训练重建模型",
    "export_geometry": "导出几何",
    "extract_dense_point_cloud": "提取密集点云",
    "extract_traits": "提取表型指标",
    "archive_results": "归档运行结果",
}


def load_toml(path: Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


def as_abs(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        path = ROOT_DIR / path
    return path.resolve()


def dataset_config_path(dataset: str) -> Path:
    return ROOT_DIR / "configs" / "datasets" / f"{dataset}.toml"


def ensure_dataset_config(dataset: str) -> Path:
    target = dataset_config_path(dataset)
    if target.exists():
        return target

    template_path = ROOT_DIR / "configs" / "datasets" / "template.toml"
    if not template_path.exists():
        raise FileNotFoundError(f"Dataset template missing: {template_path}")

    content = template_path.read_text(encoding="utf-8").replace("dataset_name", dataset)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def resolve_dataset_name(config: dict, dataset_arg: str | None) -> str:
    if dataset_arg:
        return dataset_arg
    return config.get("project", {}).get("default_dataset", "maize_plant_01")


def bool_to_text(value: bool) -> str:
    return "true" if value else "false"


def bool_to_int_text(value: bool) -> str:
    return "1" if value else "0"


def text_to_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def stage_display_name(stage: str) -> str:
    label = STAGE_LABELS.get(stage)
    if label:
        return f"{label} ({stage})"
    return stage


def build_context(config: dict, dataset_cfg: dict, dataset_name: str) -> dict[str, str]:
    paths = config.get("paths", {})
    dataset = dataset_cfg.get("dataset", {})
    video = dataset_cfg.get("video", {})
    crop = dataset_cfg.get("crop", {})
    frame_filter = dataset_cfg.get("frame_filter", {})
    dehaze = dataset_cfg.get("dehaze", {})
    colmap = dataset_cfg.get("colmap", {})
    recon = dataset_cfg.get("reconstruction", {})
    mip = dataset_cfg.get("mipnerf360", {})
    point_cloud = dataset_cfg.get("point_cloud", {})
    archive = dataset_cfg.get("archive", {})
    traits = dataset_cfg.get("traits", {})

    video_dir = as_abs(dataset.get("video_dir", f"data/raw/{dataset_name}/video"))
    images_dir = as_abs(dataset.get("images_dir", f"data/raw/{dataset_name}/images"))
    workspace_dir = as_abs(dataset.get("workspace_dir", f"data/processed/{dataset_name}"))
    outputs_dataset_dir = as_abs(dataset.get("outputs_dataset_dir", f"outputs/{dataset_name}"))
    run_dir = as_abs(Path(paths.get("runs_dir", "outputs/runs")) / dataset_name)

    keep_colmap_coords = bool(recon.get("keep_colmap_coords", False))
    recon_backend = str(recon.get("backend", "instant_ngp")).strip().lower()
    overwrite_frames = bool(video.get("overwrite", False))
    crop_enabled = bool(crop.get("enabled", False))
    frame_filter_enabled = bool(frame_filter.get("enabled", False))
    dehaze_enabled = bool(dehaze.get("enabled", False))
    colmap_single_camera = bool(colmap.get("single_camera", True))
    colmap_use_gpu = bool(colmap.get("use_gpu", True))
    colmap_extra_args = str(colmap.get("extra_args", "")).strip()
    training_vis_enabled = bool(recon.get("training_vis_enabled", False))
    training_vis_make_video = bool(recon.get("training_vis_make_video", True))
    point_cloud_enabled = bool(point_cloud.get("enabled", True))

    video_input_raw = str(dataset.get("video_input", "auto")).strip()
    if video_input_raw and video_input_raw.lower() != "auto":
        video_input = str(as_abs(video_input_raw))
    else:
        video_input = "auto"

    cropped_images_dir = as_abs(crop.get("output_dir", str(workspace_dir / "images_cropped")))
    frame_filter_input_dir = cropped_images_dir if crop_enabled else images_dir
    filtered_images_dir = as_abs(frame_filter.get("output_dir", str(workspace_dir / "images_filtered")))
    preprocess_images_dir = filtered_images_dir if frame_filter_enabled else frame_filter_input_dir

    dehazed_images_dir = as_abs(dehaze.get("output_dir", str(workspace_dir / "images_dehazed")))
    dehaze_input_dir = preprocess_images_dir
    recon_images_dir = dehazed_images_dir if dehaze_enabled else preprocess_images_dir
    mip_output_dir = as_abs(mip.get("output_dir", str(outputs_dataset_dir / "mipnerf360")))
    mip_config_link = as_abs(
        mip.get("config_link", str(outputs_dataset_dir / "mipnerf360_latest_config.txt"))
    )
    mip_export_dir = as_abs(mip.get("export_dir", str(outputs_dataset_dir / "mipnerf360_export")))
    archive_root_dir = as_abs(archive.get("root_dir", "outputs/history"))

    return {
        "project_root": str(ROOT_DIR),
        "dataset_name": dataset_name,
        "video_dir": str(video_dir),
        "video_input": video_input,
        "images_dir": str(images_dir),
        "cropped_images_dir": str(cropped_images_dir),
        "frame_filter_input_dir": str(frame_filter_input_dir),
        "filtered_images_dir": str(filtered_images_dir),
        "preprocess_images_dir": str(preprocess_images_dir),
        "dehazed_images_dir": str(dehazed_images_dir),
        "dehaze_input_dir": str(dehaze_input_dir),
        "recon_images_dir": str(recon_images_dir),
        "workspace_dir": str(workspace_dir),
        "outputs_dataset_dir": str(outputs_dataset_dir),
        "run_dir": str(run_dir),
        "instant_ngp_dir": str(as_abs(paths.get("instant_ngp_dir", "third_party/instant-ngp"))),
        "pointnerf_dir": str(as_abs(paths.get("pointnerf_dir", "third_party/pointnerf"))),
        "python_bin": paths.get("python_bin", "python"),
        "recon_backend": recon_backend,
        "frame_fps": str(video.get("fps", 3.0)),
        "video_start_time": str(video.get("start_time", "00:00:00")),
        "video_end_time": str(video.get("end_time", "none")),
        "frame_max_count": str(video.get("max_frames", 0)),
        "jpeg_quality": str(video.get("jpeg_quality", 2)),
        "resize_width": str(video.get("resize_width", -1)),
        "resize_height": str(video.get("resize_height", -1)),
        "frame_prefix": str(video.get("filename_prefix", "frame")),
        "frame_start_number": str(video.get("start_number", 1)),
        "overwrite_frames": bool_to_text(overwrite_frames),
        "crop_enabled": bool_to_text(crop_enabled),
        "crop_overwrite": bool_to_text(crop.get("overwrite", True)),
        "crop_x_min_ratio": str(crop.get("x_min_ratio", 0.0)),
        "crop_x_max_ratio": str(crop.get("x_max_ratio", 1.0)),
        "crop_y_min_ratio": str(crop.get("y_min_ratio", 0.0)),
        "crop_y_max_ratio": str(crop.get("y_max_ratio", 1.0)),
        "crop_mask_right_ratio": str(crop.get("mask_right_ratio", 0.0)),
        "crop_mask_bottom_ratio": str(crop.get("mask_bottom_ratio", 0.0)),
        "frame_filter_enabled": bool_to_text(frame_filter_enabled),
        "frame_filter_overwrite": bool_to_text(frame_filter.get("overwrite", True)),
        "frame_filter_min_sharpness": str(frame_filter.get("min_sharpness", 8.0)),
        "frame_filter_min_images": str(frame_filter.get("min_images", 60)),
        "frame_filter_min_index": str(frame_filter.get("min_index", 0)),
        "frame_filter_max_index": str(frame_filter.get("max_index", 0)),
        "frame_filter_topup_mode": str(frame_filter.get("topup_mode", "segment")),
        "dehaze_enabled": bool_to_text(dehaze_enabled),
        "dehaze_overwrite": bool_to_text(dehaze.get("overwrite", False)),
        "dehaze_omega": str(dehaze.get("omega", 0.95)),
        "dehaze_window_size": str(dehaze.get("window_size", 15)),
        "dehaze_min_transmission": str(dehaze.get("min_transmission", 0.1)),
        "dehaze_atmosphere_top_percent": str(dehaze.get("atmosphere_top_percent", 0.001)),
        "dehaze_guided_radius": str(dehaze.get("guided_radius", 24)),
        "dehaze_guided_eps": str(dehaze.get("guided_eps", 1e-3)),
        "dehaze_gamma": str(dehaze.get("gamma", 1.0)),
        "colmap_data_type": str(colmap.get("data_type", "video")),
        "colmap_quality": str(colmap.get("quality", "medium")),
        "colmap_single_camera": bool_to_int_text(colmap_single_camera),
        "colmap_use_gpu": bool_to_int_text(colmap_use_gpu),
        "colmap_gpu_index": str(colmap.get("gpu_index", -1)),
        "colmap_num_threads": str(colmap.get("num_threads", -1)),
        "openblas_num_threads": str(colmap.get("openblas_num_threads", 1)),
        "colmap_extra_args": colmap_extra_args,
        "aabb_scale": str(recon.get("aabb_scale", 16)),
        "ngp_steps": str(recon.get("ngp_steps", 35000)),
        "marching_cubes_res": str(recon.get("marching_cubes_res", 512)),
        "marching_cubes_density_thresh": str(recon.get("marching_cubes_density_thresh", 2.5)),
        "recon_near_distance": str(recon.get("near_distance", -1.0)),
        "recon_sharpen": str(recon.get("sharpen", 0.0)),
        "recon_exposure": str(recon.get("exposure", 0.0)),
        "recon_train_mode": str(recon.get("train_mode", "nerf")),
        "recon_rfl_warmup_steps": str(recon.get("rfl_warmup_steps", 1000)),
        "recon_rflrelax_begin_step": str(recon.get("rflrelax_begin_step", 15000)),
        "recon_rflrelax_end_step": str(recon.get("rflrelax_end_step", 30000)),
        "training_vis_enabled": bool_to_text(training_vis_enabled),
        "training_vis_chunk_steps": str(recon.get("training_vis_chunk_steps", 5000)),
        "training_vis_frame_index": str(recon.get("training_vis_frame_index", 0)),
        "training_vis_spp": str(recon.get("training_vis_spp", 8)),
        "training_vis_width": str(recon.get("training_vis_width", 1280)),
        "training_vis_height": str(recon.get("training_vis_height", 720)),
        "training_vis_video_fps": str(recon.get("training_vis_video_fps", 6)),
        "training_vis_make_video": bool_to_text(training_vis_make_video),
        "mip_train_bin": str(mip.get("train_bin", "ns-train")),
        "mip_export_bin": str(mip.get("export_bin", "ns-export")),
        "mip_method": str(mip.get("method", "nerfacto")),
        "mip_output_dir": str(mip_output_dir),
        "mip_config_link": str(mip_config_link),
        "mip_export_method": str(mip.get("export_method", "poisson")),
        "mip_export_dir": str(mip_export_dir),
        "mip_train_extra_args": str(mip.get("train_extra_args", "")),
        "mip_export_extra_args": str(mip.get("export_extra_args", "")),
        "point_cloud_enabled": bool_to_text(point_cloud_enabled),
        "point_cloud_num_points": str(point_cloud.get("num_points", 1200000)),
        "point_cloud_seed": str(point_cloud.get("seed", 42)),
        "archive_enabled": bool_to_text(archive.get("enabled", True)),
        "archive_root_dir": str(archive_root_dir),
        "archive_include_training_vis": bool_to_text(archive.get("include_training_vis", True)),
        "archive_include_workspace_meta": bool_to_text(archive.get("include_workspace_meta", True)),
        "vertical_axis": str(traits.get("vertical_axis", "z")),
        "keep_colmap_coords_flag": "--keep_colmap_coords" if keep_colmap_coords else "",
    }


def parse_stages(config: dict, stages_arg: str | None) -> list[str]:
    if stages_arg:
        return [s.strip() for s in stages_arg.split(",") if s.strip()]
    return list(config.get("pipeline", {}).get("default_stages", []))


def format_command(template: str, context: dict[str, str]) -> str:
    return template.format(**context).strip()


def list_images(images_dir: Path) -> list[Path]:
    if not images_dir.exists():
        return []
    return [
        p
        for p in images_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES and not p.name.startswith(".")
    ]


def list_videos(video_dir: Path) -> list[Path]:
    if not video_dir.exists():
        return []
    return [
        p
        for p in video_dir.iterdir()
        if p.is_file() and p.suffix.lower() in VIDEO_SUFFIXES and not p.name.startswith(".")
    ]


def list_pyngp_binaries(instant_ngp_dir: Path) -> list[Path]:
    patterns = ["build*/**/pyngp*.so", "build*/**/pyngp*.pyd"]
    results: list[Path] = []
    for pattern in patterns:
        for item in glob.glob(str(instant_ngp_dir / pattern), recursive=True):
            path = Path(item)
            if path.is_file():
                results.append(path)
    return sorted(results)


def check_transforms_images(transforms_path: Path, project_root: Path) -> tuple[bool, str]:
    if not transforms_path.exists():
        return False, f"缺少文件: {transforms_path}"

    try:
        with transforms_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"JSON 解析失败: {exc}"

    frames = data.get("frames", [])
    if not isinstance(frames, list) or not frames:
        return False, "transforms.json 中未找到有效的 frames"

    transforms_dir = transforms_path.parent
    missing = 0
    for frame in frames:
        raw = frame.get("file_path")
        if not raw:
            missing += 1
            continue

        p = Path(raw)
        candidates: list[Path]
        if p.is_absolute():
            candidates = [p]
        else:
            candidates = [(transforms_dir / p).resolve(), (project_root / p).resolve()]

        if not any(c.is_file() for c in candidates):
            missing += 1

    if missing > 0:
        return False, f"{transforms_path.name} 中有 {missing}/{len(frames)} 张图像路径无法解析"
    return True, f"已成功解析 {len(frames)} 张图像路径: {transforms_path}"


def first_token(cmd: str) -> str | None:
    parts = shlex.split(cmd)
    for part in parts:
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=.*$", part):
            continue
        return part
    return None


def check_binary(binary: str) -> bool:
    if "/" in binary or binary.startswith("."):
        candidate = Path(binary)
        if not candidate.is_absolute():
            candidate = (ROOT_DIR / candidate).resolve()
        return candidate.exists()
    return shutil.which(binary) is not None


def print_check(label: str, ok: bool, detail: str) -> None:
    flag = "通过" if ok else "失败"
    print(f"[检查-{flag}] {label}: {detail}")


def cmd_init_dataset(args: argparse.Namespace) -> int:
    config = load_toml(as_abs(args.config))
    dataset_name = resolve_dataset_name(config, args.dataset)
    dataset_path = ensure_dataset_config(dataset_name)
    dataset_cfg = load_toml(dataset_path)
    context = build_context(config, dataset_cfg, dataset_name)

    Path(context["video_dir"]).mkdir(parents=True, exist_ok=True)
    Path(context["images_dir"]).mkdir(parents=True, exist_ok=True)
    Path(context["cropped_images_dir"]).mkdir(parents=True, exist_ok=True)
    Path(context["filtered_images_dir"]).mkdir(parents=True, exist_ok=True)
    Path(context["dehazed_images_dir"]).mkdir(parents=True, exist_ok=True)
    Path(context["mip_output_dir"]).mkdir(parents=True, exist_ok=True)
    Path(context["mip_export_dir"]).mkdir(parents=True, exist_ok=True)
    Path(context["archive_root_dir"]).mkdir(parents=True, exist_ok=True)
    Path(context["workspace_dir"]).mkdir(parents=True, exist_ok=True)
    Path(context["outputs_dataset_dir"]).mkdir(parents=True, exist_ok=True)
    Path(context["run_dir"]).mkdir(parents=True, exist_ok=True)

    print(f"[完成] 数据集配置: {dataset_path}")
    print(f"[完成] 视频目录: {context['video_dir']}")
    print(f"[完成] 原始图像目录: {context['images_dir']}")
    print(f"[完成] 裁剪图像目录: {context['cropped_images_dir']}")
    print(f"[完成] 筛选图像目录: {context['filtered_images_dir']}")
    print(f"[完成] 去雾图像目录: {context['dehazed_images_dir']}")
    print(f"[完成] Mip-NeRF360输出目录: {context['mip_output_dir']}")
    print(f"[完成] 运行归档目录: {context['archive_root_dir']}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    config = load_toml(as_abs(args.config))
    dataset_name = resolve_dataset_name(config, args.dataset)
    dataset_path = dataset_config_path(dataset_name)
    if not dataset_path.exists():
        print(f"[错误] 找不到数据集配置: {dataset_path}", file=sys.stderr)
        print("请先执行: make init DATASET=<dataset_id>", file=sys.stderr)
        return 1

    dataset_cfg = load_toml(dataset_path)
    context = build_context(config, dataset_cfg, dataset_name)
    stages = parse_stages(config, args.stages)
    stages_cfg = config.get("stages", {})
    overall_ok = True

    images_dir = Path(context["images_dir"])
    images = list_images(images_dir)
    video_dir = Path(context["video_dir"])
    videos = list_videos(video_dir)
    video_input_text = context["video_input"]
    overwrite_frames = text_to_bool(context["overwrite_frames"])

    extraction_stage_enabled = (
        "extract_video_frames" in stages
        and bool(stages_cfg.get("extract_video_frames", {}).get("enabled", True))
    )

    images_ok = len(images) > 0
    if images_ok:
        print_check("输入图像", True, f"{images_dir} ({len(images)} 个文件)")
    elif extraction_stage_enabled:
        print_check("输入图像", True, f"{images_dir} (当前 0 个文件，将从视频自动抽帧)")
    else:
        print_check("输入图像", False, f"{images_dir} (当前 0 个文件)")

    if images_ok and not overwrite_frames:
        print_check("视频来源", True, "已存在输入图像，可跳过抽帧")
    elif extraction_stage_enabled:
        if video_input_text != "auto":
            video_input = Path(video_input_text)
            video_ok = video_input.exists()
            print_check("视频输入", video_ok, str(video_input))
            overall_ok = overall_ok and video_ok
        else:
            auto_ok = len(videos) == 1
            detail = f"{video_dir} ({len(videos)} 个候选文件)"
            print_check("视频自动发现", auto_ok, detail)
            overall_ok = overall_ok and auto_ok
    else:
        overall_ok = overall_ok and images_ok

    for path_key in ("instant_ngp_dir",):
        path = Path(context[path_key])
        ok = path.exists()
        print_check(path_key, ok, str(path))
        overall_ok = overall_ok and ok

    python_ok = check_binary(context["python_bin"])
    print_check("python_bin", python_ok, context["python_bin"])
    overall_ok = overall_ok and python_ok

    train_related = {"train_instant_ngp", "export_geometry"}
    train_stages_selected = any(stage in train_related for stage in stages)
    recon_backend = context.get("recon_backend", "instant_ngp").strip().lower()
    if train_stages_selected:
        transforms_ok, transforms_detail = check_transforms_images(
            Path(context["workspace_dir"]) / "transforms.json",
            ROOT_DIR,
        )
        print_check("transforms_images", transforms_ok, transforms_detail)
        overall_ok = overall_ok and transforms_ok

        if recon_backend == "instant_ngp":
            pyngp_bins = list_pyngp_binaries(Path(context["instant_ngp_dir"]))
            pyngp_ok = len(pyngp_bins) > 0
            detail = str(pyngp_bins[0]) if pyngp_ok else f"未在 {context['instant_ngp_dir']}/build* 下找到"
            print_check("pyngp_binary", pyngp_ok, detail)
            overall_ok = overall_ok and pyngp_ok
        elif recon_backend == "mipnerf360":
            if "train_instant_ngp" in stages:
                mip_train_ok = check_binary(context["mip_train_bin"])
                print_check("mipnerf360.train_bin", mip_train_ok, context["mip_train_bin"])
                overall_ok = overall_ok and mip_train_ok
            if "export_geometry" in stages:
                mip_export_ok = check_binary(context["mip_export_bin"])
                print_check("mipnerf360.export_bin", mip_export_ok, context["mip_export_bin"])
                overall_ok = overall_ok and mip_export_ok
        else:
            print_check("reconstruction.backend", False, f"不支持的后端: {recon_backend}")
            overall_ok = False

    training_vis_enabled = text_to_bool(context.get("training_vis_enabled", "false"))
    training_vis_make_video = text_to_bool(context.get("training_vis_make_video", "false"))
    if (
        recon_backend == "instant_ngp"
        and "train_instant_ngp" in stages
        and training_vis_enabled
        and training_vis_make_video
    ):
        ffmpeg_ok = check_binary("ffmpeg")
        print_check("train_instant_ngp.ffmpeg", ffmpeg_ok, "ffmpeg")
        overall_ok = overall_ok and ffmpeg_ok

    for stage in stages:
        stage_cfg = stages_cfg.get(stage)
        if not stage_cfg:
            print_check(f"stage.{stage}", False, "配置中缺少该阶段")
            overall_ok = False
            continue
        if not bool(stage_cfg.get("enabled", True)):
            print_check(f"stage.{stage}", True, "已禁用")
            continue

        required_tools = stage_cfg.get("required_tools", [])
        for tool in required_tools:
            ok = check_binary(str(tool))
            print_check(f"{stage}.tool", ok, str(tool))
            overall_ok = overall_ok and ok

        commands = stage_cfg.get("commands", [])
        for idx, template in enumerate(commands, start=1):
            cmd = format_command(template, context)
            token = first_token(cmd)
            if token is None:
                print_check(f"{stage}.cmd{idx}", False, "命令为空")
                overall_ok = False
                continue
            ok = check_binary(token)
            print_check(f"{stage}.cmd{idx}", ok, token)
            overall_ok = overall_ok and ok

    if not overall_ok:
        print("[错误] 环境检查未通过，请先修复上述问题后再执行流水线。")
        return 1
    print("[完成] 环境检查通过。")
    return 0


def append_log(log_path: Path, line: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(line + os.linesep)


def run_command(cmd: str, dry_run: bool) -> int:
    if dry_run:
        return 0
    result = subprocess.run(cmd, cwd=ROOT_DIR, shell=True)
    return int(result.returncode)


def cmd_run(args: argparse.Namespace) -> int:
    config = load_toml(as_abs(args.config))
    dataset_name = resolve_dataset_name(config, args.dataset)
    dataset_path = dataset_config_path(dataset_name)
    if not dataset_path.exists():
        print(f"[错误] 找不到数据集配置: {dataset_path}", file=sys.stderr)
        print("请先执行: make init DATASET=<dataset_id>", file=sys.stderr)
        return 1

    dataset_cfg = load_toml(dataset_path)
    context = build_context(config, dataset_cfg, dataset_name)
    stages = parse_stages(config, args.stages)
    stages_cfg = config.get("stages", {})
    log_path = Path(context["run_dir"]) / "pipeline.log"
    start_time = dt.datetime.now().isoformat(timespec="seconds")

    append_log(log_path, f"=== 开始运行 {start_time} dataset={dataset_name} dry_run={args.dry_run} ===")
    stage_text = ", ".join(stage_display_name(s) for s in stages)
    print(f"[信息] 数据集: {dataset_name}")
    print(f"[信息] 执行阶段: {stage_text}")
    print(f"[信息] 日志文件: {log_path}")

    for stage in stages:
        stage_cfg = stages_cfg.get(stage)
        if not stage_cfg:
            msg = f"[错误] 缺少阶段配置: {stage}"
            print(msg)
            append_log(log_path, msg)
            return 1
        if not bool(stage_cfg.get("enabled", True)):
            msg = f"[跳过] 阶段已禁用: {stage_display_name(stage)}"
            print(msg)
            append_log(log_path, msg)
            continue

        stage_title = stage_display_name(stage)
        print(f"[阶段] {stage_title}")
        append_log(log_path, f"[阶段] {stage_title}")
        commands = stage_cfg.get("commands", [])

        for idx, template in enumerate(commands, start=1):
            cmd = format_command(template, context)
            prefix = "[演练]" if args.dry_run else "[执行]"
            line = f"{prefix} ({stage}.{idx}) {cmd}"
            print(line)
            append_log(log_path, line)

            code = run_command(cmd, args.dry_run)
            if code != 0:
                err = f"[错误] 命令执行失败，退出码 {code}: {cmd}"
                print(err)
                append_log(log_path, err)
                if not args.continue_on_error:
                    return code

    end_time = dt.datetime.now().isoformat(timespec="seconds")
    append_log(log_path, f"=== 运行结束 {end_time} ===")
    print("[完成] 流水线执行结束。")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Data-ready NeRF phenotyping pipeline runner.")
    parser.add_argument("--config", default="configs/pipeline.toml", help="Pipeline TOML config.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-dataset", help="Create dataset config and directories.")
    init_parser.add_argument("--dataset", default=None, help="Dataset id (e.g. maize_plant_01)")
    init_parser.set_defaults(func=cmd_init_dataset)

    check_parser = subparsers.add_parser("check", help="Validate tools, paths and stage commands.")
    check_parser.add_argument("--dataset", default=None, help="Dataset id")
    check_parser.add_argument("--stages", default=None, help="Comma separated stage list.")
    check_parser.set_defaults(func=cmd_check)

    run_parser = subparsers.add_parser("run", help="Run staged pipeline commands.")
    run_parser.add_argument("--dataset", default=None, help="Dataset id")
    run_parser.add_argument("--stages", default=None, help="Comma separated stage list.")
    run_parser.add_argument("--dry-run", action="store_true", help="Print commands only.")
    run_parser.add_argument("--continue-on-error", action="store_true", help="Continue after command failure.")
    run_parser.set_defaults(func=cmd_run)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
