from __future__ import annotations

import asyncio
import json
import os
import shutil
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from backend.shared.db import DATA_ROOT, add_event, connect, init_db, json_load, new_id, now_iso, row_dict
from backend.api.remote import router as remote_router
from backend.shared.metrics import training_metric
from backend.api.terminal import router as terminal_router


app = FastAPI(title="LoRA Platform API", version="0.1.0")
app.include_router(remote_router)
app.include_router(terminal_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DatasetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    path: str = Field(min_length=1, max_length=500)


class CaptionUpdate(BaseModel):
    caption: str = Field(default="", max_length=4000)
    source: str = Field(default='manual', pattern='^(manual|wd14)$')


class JobCreate(BaseModel):
    kind: str = Field(pattern="^(tag|train|infer|model_download)$")
    payload: dict[str, Any] = Field(default_factory=dict)


class SettingsUpdate(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)


DEFAULT_SETTINGS = {
    "models_dir": "/data/models",
    "datasets_dir": "/data/datasets",
    "runs_dir": "/data/runs",
    "outputs_dir": "/data/outputs",
    "default_base_model": "/data/models/sd15/v1-5-pruned-emaonly.safetensors",
    "default_resolution": "512",
    "default_steps": "100",
    "default_rank": "16",
    "default_learning_rate": "0.0001",
    "comfy_url": "http://stable-diffusion:8188",
}

MODEL_CATALOG = {
    "sd15": {
        "id": "sd15",
        "title": "Stable Diffusion 1.5（pruned EMA）",
        "source": "Hugging Face",
        "repo_id": "stable-diffusion-v1-5/stable-diffusion-v1-5",
        "filename": "v1-5-pruned-emaonly.safetensors",
        "destination": "/data/models/sd15/v1-5-pruned-emaonly.safetensors",
        "files": ["v1-5-pruned-emaonly.safetensors"],
        "kind": "base",
    },
    "wd14": {
        "id": "wd14",
        "title": "WD14 ConvNeXtV2 Tagger",
        "source": "Hugging Face",
        "repo_id": "SmilingWolf/wd-v1-4-convnextv2-tagger-v2",
        "filename": "model.onnx",
        "destination": "/data/models/SmilingWolf_wd-v1-4-convnextv2-tagger-v2/model.onnx",
        "files": ["model.onnx", "selected_tags.csv"],
        "kind": "tagger",
    },
}


def safe_data_path(raw: str) -> Path:
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = DATA_ROOT / raw
    candidate = candidate.resolve()
    root = DATA_ROOT.resolve()
    if candidate != root and root not in candidate.parents:
        raise HTTPException(status_code=400, detail="路径必须位于 /data 内")
    return candidate


@app.on_event("startup")
def startup() -> None:
    for path in (DATA_ROOT / "models", DATA_ROOT / "datasets", DATA_ROOT / "runs", DATA_ROOT / "outputs"):
        path.mkdir(parents=True, exist_ok=True)
    init_db()


@app.get("/api/health")
def health() -> dict[str, Any]:
    with connect() as db:
        db.execute("SELECT 1")
    return {"status": "ok", "service": "api", "time": now_iso()}


@app.get("/api/system")
def system() -> dict[str, Any]:
    with connect() as db:
        queued = db.execute("SELECT COUNT(*) AS n FROM jobs WHERE status='queued'").fetchone()["n"]
        running = db.execute("SELECT COUNT(*) AS n FROM jobs WHERE status IN ('validating','running','cancelling')").fetchone()["n"]
    return {
        "api": "ok",
        "worker": "GPU worker is configured; status is refreshed from tasks",
        "gpu": {"name": "NVIDIA GeForce RTX 4060 Laptop GPU", "memory": "8 GB", "mode": "single GPU serial"},
        "queue": {"queued": queued, "running": running},
        "data_root": str(DATA_ROOT),
    }


@app.get("/api/settings")
def get_settings() -> dict[str, str]:
    values = DEFAULT_SETTINGS.copy()
    with connect() as db:
        rows = db.execute("SELECT key,value FROM settings").fetchall()
    values.update({row["key"]: row["value"] for row in rows})
    return values


@app.put("/api/settings")
def update_settings(body: SettingsUpdate) -> dict[str, str]:
    allowed = set(DEFAULT_SETTINGS)
    unknown = sorted(set(body.values) - allowed)
    if unknown:
        raise HTTPException(status_code=400, detail=f"不支持的设置项：{', '.join(unknown)}")
    for key in ("models_dir", "datasets_dir", "runs_dir", "outputs_dir", "default_base_model"):
        if key in body.values:
            safe_data_path(body.values[key])
    with connect() as db:
        for key, value in body.values.items():
            db.execute(
                "INSERT INTO settings(key,value,updated_at) VALUES (?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
                (key, value, now_iso()),
            )
    return get_settings()


@app.get("/api/models")
def list_models() -> dict[str, Any]:
    catalog = []
    for item in MODEL_CATALOG.values():
        candidate = safe_data_path(item["destination"])
        catalog.append({**item, "available": candidate.exists(), "size": candidate.stat().st_size if candidate.exists() else 0})
    lora_root = DATA_ROOT / "runs"
    loras = [
        {"name": path.name, "path": str(path), "size": path.stat().st_size}
        for path in sorted(lora_root.rglob("*.safetensors"))
    ] if lora_root.exists() else []
    return {"catalog": catalog, "loras": loras}


@app.post("/api/models/download", status_code=201)
def download_model(model_id: str = Query(..., pattern="^(sd15|wd14)$")) -> dict[str, Any]:
    item = MODEL_CATALOG[model_id]
    if safe_data_path(item["destination"]).exists():
        return {"status": "available", "model": item}
    return create_job(JobCreate(kind="model_download", payload=item))


@app.get("/api/image")
def serve_image(path: str) -> FileResponse:
    image_path = safe_data_path(path)
    if not image_path.is_file() or image_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise HTTPException(status_code=404, detail="图片不存在")
    return FileResponse(image_path)


@app.get("/api/browse")
def browse_directories(path: str = "/data") -> dict[str, Any]:
    current = safe_data_path(path)
    if not current.exists() or not current.is_dir():
        raise HTTPException(status_code=404, detail="目录不存在")
    root = DATA_ROOT.resolve()
    parent = str(current.parent) if current.resolve() != root else None
    directories = [
        {"name": item.name, "path": str(item)}
        for item in sorted(current.iterdir())
        if item.is_dir() and not item.name.startswith(".")
    ]
    return {"current": str(current), "parent": parent, "directories": directories}


@app.get("/api/datasets")
def list_datasets() -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute("SELECT * FROM datasets ORDER BY updated_at DESC").fetchall()
    return [row_dict(row) for row in rows]


@app.post("/api/datasets", status_code=201)
def create_dataset(body: DatasetCreate) -> dict[str, Any]:
    path = safe_data_path(body.path)
    path.mkdir(parents=True, exist_ok=True)
    dataset_id = new_id("ds")
    now = now_iso()
    image_count = 0
    with connect() as db:
        for file_path in sorted(path.iterdir()):
            if file_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                continue
            image_count += 1
            caption_path = file_path.with_suffix(".txt")
            caption = caption_path.read_text(encoding="utf-8") if caption_path.exists() else ""
            db.execute(
                "INSERT INTO images(id,dataset_id,filename,path,caption,has_caption) VALUES (?,?,?,?,?,?)",
                (new_id("img"), dataset_id, file_path.name, str(file_path), caption, int(bool(caption.strip()))),
            )
        db.execute(
            "INSERT INTO datasets(id,name,path,version,image_count,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
            (dataset_id, body.name, str(path), 1, image_count, now, now),
        )
    return get_dataset(dataset_id)


@app.post("/api/datasets/import", status_code=201)
async def import_dataset(name: str = Form(...), files: list[UploadFile] = File(...)) -> dict[str, Any]:
    if not files:
        raise HTTPException(status_code=400, detail="请至少选择一张图片")
    dataset_id = new_id("ds")
    target = DATA_ROOT / "datasets" / dataset_id
    target.mkdir(parents=True, exist_ok=False)
    allowed = {".png", ".jpg", ".jpeg", ".webp"}
    count = 0
    for upload in files:
        filename = Path(upload.filename or "").name
        if Path(filename).suffix.lower() not in allowed:
            continue
        with (target / filename).open("wb") as output:
            shutil.copyfileobj(upload.file, output)
        count += 1
    if not count:
        shutil.rmtree(target)
        raise HTTPException(status_code=400, detail="未收到支持的图片格式")
    now = now_iso()
    with connect() as db:
        for file_path in sorted(target.iterdir()):
            if file_path.suffix.lower() in allowed:
                db.execute(
                    "INSERT INTO images(id,dataset_id,filename,path,caption,has_caption) VALUES (?,?,?,?,?,?)",
                    (new_id("img"), dataset_id, file_path.name, str(file_path), "", 0),
                )
        db.execute(
            "INSERT INTO datasets(id,name,path,version,image_count,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
            (dataset_id, name.strip() or "未命名数据集", str(target), 1, count, now, now),
        )
    return get_dataset(dataset_id)


@app.get("/api/datasets/{dataset_id}")
def get_dataset(dataset_id: str) -> dict[str, Any]:
    with connect() as db:
        row = db.execute("SELECT * FROM datasets WHERE id=?", (dataset_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="数据集不存在")
        images = db.execute("SELECT * FROM images WHERE dataset_id=? ORDER BY filename", (dataset_id,)).fetchall()
        records = {record['image_path']: record for record in db.execute('SELECT cr.* FROM caption_records cr JOIN images i ON i.path=cr.image_path WHERE i.dataset_id=?', (dataset_id,)).fetchall()}
    result = row_dict(row)
    result["images"] = []
    for image in images:
        item = row_dict(image)
        assert item is not None
        record = records.get(item['path'])
        caption_path = Path(item["path"]).with_suffix(".txt")
        if caption_path.exists():
            item["caption"] = caption_path.read_text(encoding="utf-8")
            item["has_caption"] = int(bool(item["caption"].strip()))
        item['caption_source'] = record['source'] if record else ('imported' if item['has_caption'] else 'none')
        item['wd14_caption'] = record['wd14_caption'] if record else None
        item['wd14_model'] = record['model_id'] if record else None
        item['wd14_threshold'] = record['threshold'] if record else None
        result["images"].append(item)
    return result


@app.put("/api/datasets/{dataset_id}/images/{image_id}/caption")
def update_caption(dataset_id: str, image_id: str, body: CaptionUpdate) -> dict[str, Any]:
    with connect() as db:
        image = db.execute("SELECT * FROM images WHERE id=? AND dataset_id=?", (image_id, dataset_id)).fetchone()
        if not image:
            raise HTTPException(status_code=404, detail="图片不存在")
        caption_path = Path(image["path"]).with_suffix(".txt")
        if body.source == 'wd14':
            generated = db.execute('SELECT wd14_caption FROM caption_records WHERE image_path=?', (image['path'],)).fetchone()
            if not generated or generated['wd14_caption'] is None:
                raise HTTPException(400, '这张图片还没有 WD14 自动标签。')
            body.caption = generated['wd14_caption']
        caption_path.write_text(body.caption.strip(), encoding="utf-8")
        db.execute("UPDATE images SET caption=?,has_caption=? WHERE id=?", (body.caption.strip(), int(bool(body.caption.strip())), image_id))
        db.execute('INSERT INTO caption_records(image_path,source,updated_at) VALUES (?,?,?) ON CONFLICT(image_path) DO UPDATE SET source=excluded.source,updated_at=excluded.updated_at', (image['path'], body.source, now_iso()))
    return {"id": image_id, "caption": body.caption.strip(), "saved": True}


@app.post("/api/jobs", status_code=201)
def create_job(body: JobCreate) -> dict[str, Any]:
    if body.kind == 'tag':
        safe_data_path(str(body.payload.get('dataset_dir', '')))
        threshold = body.payload.get('threshold', 0.35)
        if not isinstance(threshold, (int, float)) or not 0 <= threshold <= 1:
            raise HTTPException(400, 'WD14 阈值必须在 0 到 1 之间。')
    job_id = new_id("job")
    now = now_iso()
    with connect() as db:
        db.execute(
            "INSERT INTO jobs(id,kind,status,payload,message,created_at) VALUES (?,?,?,?,?,?)",
            (job_id, body.kind, "queued", json.dumps(body.payload, ensure_ascii=False), "等待 GPU worker", now),
        )
        event_id = add_event(db, job_id, "status", {"status": "queued", "message": "任务已进入队列"})
    return {"id": job_id, "kind": body.kind, "status": "queued", "event_id": event_id}


def job_from_row(row: Any) -> dict[str, Any]:
    item = row_dict(row) or {}
    item["payload"] = json_load(item.get("payload"), {})
    item["error"] = item.get("error") or None
    return item


@app.get("/api/jobs")
def list_jobs(limit: int = Query(default=30, ge=1, le=100)) -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [job_from_row(row) for row in rows]


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    with connect() as db:
        row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="任务不存在")
        events = db.execute("SELECT id,event_type,payload,created_at FROM job_events WHERE job_id=? ORDER BY id DESC LIMIT 200", (job_id,)).fetchall()
        artifacts = db.execute("SELECT * FROM artifacts WHERE job_id=? ORDER BY created_at", (job_id,)).fetchall()
    result = job_from_row(row)
    result["events"] = [{**row_dict(event), "payload": json_load(event["payload"], {})} for event in reversed(events)]
    result["artifacts"] = [{**row_dict(item), "metadata": json_load(item["metadata"], {})} for item in artifacts]
    return result


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str) -> dict[str, Any]:
    with connect() as db:
        row = db.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="任务不存在")
        if row["status"] in {"queued", "validating", "running"}:
            db.execute("UPDATE jobs SET status='cancelling',message=? WHERE id=?", ("等待 worker 停止", job_id))
            add_event(db, job_id, "status", {"status": "cancelling", "message": "已请求停止"})
    return get_job(job_id)


@app.get("/api/jobs/{job_id}/events")
async def job_events(job_id: str, after: int = Query(default=0, ge=0)) -> StreamingResponse:
    with connect() as db:
        if not db.execute("SELECT 1 FROM jobs WHERE id=?", (job_id,)).fetchone():
            raise HTTPException(status_code=404, detail="任务不存在")

    async def stream():
        cursor = after
        for _ in range(1800):
            with connect() as db:
                rows = db.execute("SELECT id,event_type,payload,created_at FROM job_events WHERE job_id=? AND id>? ORDER BY id", (job_id, cursor)).fetchall()
            for row in rows:
                cursor = row["id"]
                payload = {"id": row["id"], "type": row["event_type"], "payload": json_load(row["payload"], {}), "created_at": row["created_at"]}
                yield f"id: {cursor}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/files")
def files(path: str = "/data/runs") -> list[dict[str, Any]]:
    target = safe_data_path(path)
    if not target.exists():
        return []
    return [{"name": item.name, "path": str(item), "size": item.stat().st_size, "is_dir": item.is_dir()} for item in sorted(target.iterdir())]


@app.get('/api/jobs/{job_id}/metrics')
def job_metrics(job_id: str) -> dict:
    with connect() as db:
        if not db.execute('SELECT 1 FROM jobs WHERE id=?', (job_id,)).fetchone():
            raise HTTPException(404, '任务不存在')
        values = [dict(row) for row in db.execute('SELECT step,total,loss,created_at FROM job_metrics WHERE job_id=? ORDER BY step', (job_id,))]
        if not values:
            historic = db.execute("SELECT payload,created_at FROM job_events WHERE job_id=? AND event_type='log' ORDER BY id", (job_id,))
            parsed = {}
            for event in historic:
                metric = training_metric(json_load(event['payload'], {}).get('line', ''))
                if metric:
                    step, total, loss = metric
                    parsed[step] = {'step': step, 'total': total, 'loss': loss, 'created_at': event['created_at']}
            values = list(parsed.values())
    return {'points': values, 'metric': 'average_loss', 'source': 'sd-scripts stdout'}


@app.get('/api/files/download')
def download_artifact(path: str):
    target = safe_data_path(path)
    if not target.is_file() or not any(folder in target.parents for folder in (DATA_ROOT / 'runs', DATA_ROOT / 'outputs')):
        raise HTTPException(404, '产物文件不存在。')
    return FileResponse(target, filename=target.name)

