from __future__ import annotations

import json
import os
import re
import signal
import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

import requests
from huggingface_hub import snapshot_download

from backend.shared.db import DATA_ROOT, add_event, connect, init_db, json_load, new_id, now_iso
from backend.shared.metrics import training_metric


WORKER_ID = f"{socket.gethostname()}-{os.getpid()}"
POLL_SECONDS = float(os.getenv("LORA_POLL_SECONDS", "1"))
REAL_MODE = os.getenv("LORA_EXECUTE_REAL", "0") == "1"
ACTIVE_PROCESS: subprocess.Popen[str] | None = None
COMFY_URL = os.getenv("COMFY_URL", "http://stable-diffusion:8188")


def job_workspace(job_id: str, payload: dict[str, Any] | None = None) -> Path:
    if payload is None:
        with connect() as db:
            row = db.execute('SELECT payload FROM jobs WHERE id=?', (job_id,)).fetchone()
        payload = json_load(row['payload'], {}) if row else {}
    paths = [str(payload.get(key, '')) for key in ('dataset_dir', 'train_data_dir', 'output_dir', 'lora_path', 'destination')]
    if any(path.startswith(('/data/manzhou/', '/data/runs/manzhou/')) for path in paths):
        return DATA_ROOT / 'runs' / 'manzhou' / 'jobs' / job_id
    return DATA_ROOT / 'runs' / job_id


def set_job(job_id: str, *, status: str | None = None, progress: float | None = None, message: str | None = None, step: int | None = None, total: int | None = None, error: str | None = None) -> None:
    fields: list[str] = ["heartbeat_at=?"]
    values: list[Any] = [now_iso()]
    if status is not None:
        fields.append("status=?")
        values.append(status)
        if status in {'succeeded', 'failed', 'cancelled', 'interrupted'}:
            fields.append('finished_at=?')
            values.append(now_iso())
    if progress is not None:
        fields.append("progress=?")
        values.append(max(0.0, min(1.0, progress)))
    if message is not None:
        fields.append("message=?")
        values.append(message)
    if step is not None:
        fields.append("current_step=?")
        values.append(step)
    if total is not None:
        fields.append("total_steps=?")
        values.append(total)
    if error is not None:
        fields.append("error=?")
        values.append(error)
    values.append(job_id)
    with connect() as db:
        db.execute(f"UPDATE jobs SET {','.join(fields)} WHERE id=?", values)
        payload = {"status": status, "progress": progress, "message": message, "step": step, "total": total, "error": error}
        add_event(db, job_id, "progress" if progress is not None else "status", {k: v for k, v in payload.items() if v is not None})


def is_cancelled(job_id: str) -> bool:
    with connect() as db:
        row = db.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()
    return bool(row and row["status"] == "cancelling")


def claim_next() -> tuple[str, str, dict[str, Any]] | None:
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT id,kind,payload FROM jobs WHERE status='queued' ORDER BY created_at LIMIT 1").fetchone()
        if not row:
            db.execute("COMMIT")
            return None
        db.execute("UPDATE jobs SET status='validating',worker_id=?,started_at=?,heartbeat_at=?,message=? WHERE id=?", (WORKER_ID, now_iso(), now_iso(), "worker 正在校验任务", row["id"]))
        add_event(db, row["id"], "status", {"status": "validating", "message": "worker 正在校验任务"})
        db.execute("COMMIT")
    return row["id"], row["kind"], json_load(row["payload"], {})


def run_demo(job_id: str, kind: str, payload: dict[str, Any]) -> None:
    total = 20 if kind == "train" else 8
    for index in range(total + 1):
        if is_cancelled(job_id):
            set_job(job_id, status="cancelled", progress=index / total, message="任务已停止", step=index, total=total)
            return
        status = "running"
        set_job(job_id, status=status, progress=index / total, message=f"演示模式：{kind} 任务 {index}/{total}", step=index, total=total)
        time.sleep(0.25)
    run_dir = job_workspace(job_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "demo-result.json").write_text(json.dumps({"kind": kind, "payload": payload, "mode": "demo", "created_at": now_iso()}, ensure_ascii=False, indent=2), encoding="utf-8")
    with connect() as db:
        db.execute("INSERT INTO artifacts(id,job_id,kind,path,metadata,created_at) VALUES (?,?,?,?,?,?)", (new_id("art"), job_id, "demo-result", str(run_dir / "demo-result.json"), json.dumps({"mode": "demo"}), now_iso()))


def build_real_command(job_id: str, kind: str, payload: dict[str, Any]) -> list[str]:
    run_dir = job_workspace(job_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    sd_scripts = Path(os.getenv("SD_SCRIPTS_DIR", "/opt/sd-scripts"))
    python = os.getenv("LORA_TRAIN_PYTHON", "python")
    if kind == "tag":
        script = sd_scripts / "finetune" / "tag_images_by_wd14_tagger.py"
        dataset = str(payload.get("dataset_dir", ""))
        model_dir = str(payload.get("model_dir", "/data/models"))
        if not script.exists() or not dataset:
            raise RuntimeError("真实打标需要 sd-scripts 和 dataset_dir")
        # sd-scripts expects --repo_id to be a Hugging Face ID, while --model_dir
        # is the local cache root. Keep both explicit so the job is reproducible.
        repo_id = str(payload.get("repo_id", "SmilingWolf/wd-v1-4-convnextv2-tagger-v2"))
        return [python, str(script), "--onnx", "--repo_id", repo_id, "--model_dir", model_dir, "--thresh", str(payload.get('threshold', 0.35)), '--recursive', '--caption_extension', '.wd14.txt', dataset]
    if kind == "train":
        script = sd_scripts / "train_network.py"
        if not script.exists():
            raise RuntimeError("真实训练需要 /opt/sd-scripts/train_network.py")
        required = {"pretrained_model_name_or_path", "train_data_dir", "output_dir"}
        missing = sorted(required - payload.keys())
        if missing:
            raise RuntimeError(f"训练参数缺少：{', '.join(missing)}")
        args = [python, str(script)]
        for key, value in payload.items():
            if key in {"kind", "description", "logging_dir", "output_dir"}:
                continue
            # sd-scripts exposes argparse options with underscores; preserve the
            # upstream spelling instead of translating them to hyphenated flags.
            cli = "--" + key
            if isinstance(value, bool):
                if value:
                    args.append(cli)
            elif value is not None and value != "":
                args.extend([cli, str(value)])
        args.extend(["--logging_dir", str(run_dir / "tensorboard"), "--output_dir", str(payload["output_dir"])])
        return args
    if kind == "model_download":
        script = Path("/app/scripts/download_hf_file.py")
        required = {"repo_id", "filename", "destination"}
        missing = sorted(required - payload.keys())
        if not script.exists() or missing:
            raise RuntimeError("模型下载参数或下载脚本缺失：" + ", ".join(missing))
        return [python, str(script), str(payload["repo_id"]), str(payload["filename"]), str(payload["destination"])]
    raise RuntimeError("首版真实推理适配尚未启用，请先完成 P2 的模型资源验证")


def prepare_train_data(job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    prepared = dict(payload)
    source = Path(str(prepared.get("train_data_dir", "")))
    if source.is_dir() and re.fullmatch(r"\d+_[A-Za-z0-9_-]+", source.name):
        # A prebuilt sd-scripts repeat folder already contains its image and
        # VAE latent cache. Keep it intact when an operator selects it in UI.
        prepared["train_data_dir"] = str(source.parent)
        return prepared
    images = [item for item in source.iterdir() if item.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}] if source.is_dir() else []
    if not images:
        return prepared
    target = job_workspace(job_id, prepared) / "training_dataset" / "1_train"
    target.mkdir(parents=True, exist_ok=True)
    for image in images:
        shutil.copy2(image, target / image.name)
        caption = image.with_suffix(".txt")
        if caption.exists():
            shutil.copy2(caption, target / caption.name)
    prepared["train_data_dir"] = str(target.parent)
    return prepared


def append_artifact(job_id: str, kind: str, path: Path, metadata: dict[str, Any] | None = None) -> None:
    with connect() as db:
        db.execute(
            "INSERT INTO artifacts(id,job_id,kind,path,metadata,created_at) VALUES (?,?,?,?,?,?)",
            (new_id("art"), job_id, kind, str(path), json.dumps(metadata or {}, ensure_ascii=False), now_iso()),
        )


def comfy_workflow(job_id: str, payload: dict[str, Any], use_lora: bool) -> dict[str, Any]:
    base_model = Path(str(payload["base_model"])).name
    prompt = str(payload.get("prompt", "a studio portrait photo"))
    negative = str(payload.get("negative_prompt", "low quality, blurry, watermark, text"))
    width = int(payload.get("width", 512))
    height = int(payload.get("height", 512))
    seed = int(payload.get("seed", 42))
    steps = int(payload.get("steps", 20))
    cfg = float(payload.get("guidance_scale", 7))
    output_namespace = 'lora-platform/manzhou' if str(payload.get('lora_path', '')).startswith('/data/runs/manzhou/') else 'lora-platform'
    workflow: dict[str, Any] = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": f"sd15/{base_model}"}},
        "3": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0, "model": ["1", 0], "positive": ["2", 0], "negative": ["4", 0], "latent_image": ["3", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"filename_prefix": f"{output_namespace}/{job_id}/{'lora' if use_lora else 'base'}", "images": ["6", 0]}},
    }
    clip_ref: list[Any] = ["1", 1]
    if use_lora:
        lora_path = Path(str(payload["lora_path"])).relative_to(DATA_ROOT / "runs").as_posix()
        workflow["8"] = {"class_type": "LoraLoader", "inputs": {"model": ["1", 0], "clip": ["1", 1], "lora_name": f"lora-platform-runs/{lora_path}", "strength_model": float(payload.get("lora_strength", 0.8)), "strength_clip": float(payload.get("lora_strength", 0.8))}}
        workflow["5"]["inputs"]["model"] = ["8", 0]
        clip_ref = ["8", 1]
    workflow["2"] = {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": clip_ref}}
    workflow["4"] = {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": clip_ref}}
    return workflow


def run_comfy(job_id: str, payload: dict[str, Any], use_lora: bool) -> list[Path]:
    response = requests.post(f"{COMFY_URL}/prompt", json={"prompt": comfy_workflow(job_id, payload, use_lora)}, timeout=30)
    response.raise_for_status()
    prompt_id = response.json()["prompt_id"]
    for _ in range(360):
        if is_cancelled(job_id):
            raise RuntimeError("推理任务已取消")
        history = requests.get(f"{COMFY_URL}/history/{prompt_id}", timeout=15).json()
        record = history.get(prompt_id)
        if record and record.get("status", {}).get("completed"):
            images = record.get("outputs", {}).get("7", {}).get("images", [])
            return [DATA_ROOT / "outputs" / image.get("subfolder", "") / image["filename"] for image in images]
        time.sleep(1)
    raise RuntimeError("ComfyUI 推理等待超时")


def run_inference(job_id: str, payload: dict[str, Any]) -> None:
    required = {"base_model", "prompt"}
    missing = sorted(required - payload.keys())
    if missing:
        raise RuntimeError("推理参数缺少：" + ", ".join(missing))
    set_job(job_id, status="running", progress=0.05, message="正在加载 Stable Diffusion 基础模型")
    base_paths = run_comfy(job_id, payload, use_lora=False)
    for path in base_paths:
        append_artifact(job_id, "base-image", path, {"with_lora": False})
    if payload.get("lora_path"):
        set_job(job_id, progress=0.55, message="正在加载 LoRA 并生成对比图")
        lora_paths = run_comfy(job_id, payload, use_lora=True)
        for path in lora_paths:
            append_artifact(job_id, "lora-image", path, {"with_lora": True, "lora_path": payload["lora_path"]})
    set_job(job_id, progress=0.95, message="推理图像已保存")


def release_comfy_memory() -> None:
    try:
        requests.post(f"{COMFY_URL}/free", json={"unload_models": True, "free_memory": True}, timeout=20).raise_for_status()
    except requests.RequestException:
        # The training task should remain usable even when the optional inference
        # service is stopped or restarting.
        pass


def run_model_download(job_id: str, payload: dict[str, Any]) -> None:
    repo_id = str(payload.get("repo_id", ""))
    destination = Path(str(payload.get("destination", "")))
    files = payload.get("files", [])
    if not repo_id or not destination or not isinstance(files, list):
        raise RuntimeError("模型下载参数不完整")
    set_job(job_id, status="running", progress=0.05, message="正在连接 Hugging Face")
    if len(files) == 1:
        command = build_real_command(job_id, "model_download", payload)
        _run_subprocess(job_id, command)
    else:
        snapshot_download(repo_id=repo_id, local_dir=str(destination.parent), allow_patterns=[str(item) for item in files])
    if not destination.exists():
        raise RuntimeError("下载结束后未找到目标模型文件")
    append_artifact(job_id, "model", destination, {"repo_id": repo_id})
    set_job(job_id, status="succeeded", progress=1.0, message="模型已下载并可在页面中使用")


def _run_subprocess(job_id: str, command: list[str]) -> None:
    global ACTIVE_PROCESS
    run_dir = job_workspace(job_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "logs.txt"
    with log_path.open("w", encoding="utf-8") as log_file:
        ACTIVE_PROCESS = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, start_new_session=True)
        assert ACTIVE_PROCESS.stdout is not None
        for line in ACTIVE_PROCESS.stdout:
            log_file.write(line)
            log_file.flush()
            with connect() as db:
                add_event(db, job_id, "log", {"line": line.rstrip()})
                metric = training_metric(line)
                if metric:
                    step, total, loss = metric
                    db.execute('INSERT OR REPLACE INTO job_metrics VALUES (?,?,?,?,?)', (job_id, step, total, loss, now_iso()))
                    db.execute('UPDATE jobs SET current_step=?,total_steps=?,progress=? WHERE id=?', (step, total, step / total, job_id))
            if is_cancelled(job_id):
                os.killpg(ACTIVE_PROCESS.pid, signal.SIGTERM)
        exit_code = ACTIVE_PROCESS.wait()
    ACTIVE_PROCESS = None
    if exit_code != 0:
        raise RuntimeError(f"下载进程退出码 {exit_code}")


def run_real(job_id: str, kind: str, payload: dict[str, Any]) -> None:
    global ACTIVE_PROCESS
    if kind == "infer":
        run_inference(job_id, payload)
        set_job(job_id, status="succeeded", progress=1.0, message="基础模型与 LoRA 对比图已生成")
        return
    if kind == "model_download":
        run_model_download(job_id, payload)
        return
    if kind in {'train', 'tag'}:
        release_comfy_memory()
    if kind == "train":
        payload = prepare_train_data(job_id, payload)
    command = build_real_command(job_id, kind, payload)
    set_job(job_id, status="running", message="正在执行 GPU 任务")
    run_dir = job_workspace(job_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "logs.txt"
    with log_path.open("w", encoding="utf-8") as log_file:
        ACTIVE_PROCESS = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, start_new_session=True)
        assert ACTIVE_PROCESS.stdout is not None
        for line in ACTIVE_PROCESS.stdout:
            log_file.write(line)
            log_file.flush()
            with connect() as db:
                add_event(db, job_id, "log", {"line": line.rstrip()})
                metric = training_metric(line)
                if metric:
                    step, total, loss = metric
                    db.execute('INSERT OR REPLACE INTO job_metrics VALUES (?,?,?,?,?)', (job_id, step, total, loss, now_iso()))
                    db.execute('UPDATE jobs SET current_step=?,total_steps=?,progress=? WHERE id=?', (step, total, step / total, job_id))
            if is_cancelled(job_id):
                os.killpg(ACTIVE_PROCESS.pid, signal.SIGTERM)
        exit_code = ACTIVE_PROCESS.wait()
    ACTIVE_PROCESS = None
    if is_cancelled(job_id):
        set_job(job_id, status="cancelled", message="任务已停止")
    elif exit_code == 0:
        set_job(job_id, message="计算结束，正在保存标签和产物")
        with connect() as db:
            db.execute("INSERT INTO artifacts(id,job_id,kind,path,metadata,created_at) VALUES (?,?,?,?,?,?)", (new_id("art"), job_id, "logs", str(log_path), json.dumps({}), now_iso()))
        if kind == "train":
            output = Path(str(payload["output_dir"]))
            produced = list(output.glob("*.safetensors"))
            if not produced:
                raise RuntimeError("训练未生成 .safetensors LoRA 文件")
            for artifact in produced:
                append_artifact(job_id, "lora", artifact, {"backend": "sd-scripts"})
        elif kind == 'tag':
            for image in Path(str(payload['dataset_dir'])).rglob('*'):
                if image.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp'}:
                    continue
                caption = image.with_suffix('.wd14.txt')
                if caption.exists():
                    text = caption.read_text(encoding='utf-8')
                    training_caption = image.with_suffix('.txt')
                    with connect() as db:
                        previous = db.execute('SELECT source FROM caption_records WHERE image_path=?', (str(image),)).fetchone()
                        source = previous['source'] if previous else ('imported' if training_caption.exists() else 'wd14')
                        if source == 'wd14':
                            training_caption.write_text(text, encoding='utf-8')
                        db.execute('INSERT OR REPLACE INTO caption_records VALUES (?,?,?,?,?,?,?)', (str(image), source, text, payload.get('repo_id', 'SmilingWolf/wd-v1-4-convnextv2-tagger-v2'), float(payload.get('threshold', 0.35)), job_id, now_iso()))
        if kind == "model_download":
            model_path = Path(str(payload["destination"]))
            if model_path.exists():
                append_artifact(job_id, "model", model_path, {"repo_id": payload["repo_id"]})
        set_job(job_id, status="succeeded", progress=1.0, message="任务完成")
    else:
        set_job(job_id, status="failed", message="GPU 任务失败", error=f"退出码 {exit_code}")


def execute(job: tuple[str, str, dict[str, Any]]) -> None:
    job_id, kind, payload = job
    try:
        set_job(job_id, status="running", progress=0, message=f"开始 {kind} 任务")
        if REAL_MODE:
            run_real(job_id, kind, payload)
        else:
            run_demo(job_id, kind, payload)
            if not is_cancelled(job_id):
                set_job(job_id, status="succeeded", progress=1.0, message="演示任务完成")
    except Exception as exc:  # keep worker alive for the next queued job
        set_job(job_id, status="failed", message="任务校验或执行失败", error=str(exc))


def main() -> None:
    init_db()
    print(f"lora-gpu-worker started: {WORKER_ID}; real_mode={REAL_MODE}", flush=True)
    while True:
        job = claim_next()
        if job:
            execute(job)
        else:
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
