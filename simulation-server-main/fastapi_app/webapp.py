import os
import json
import uuid
import mimetypes
from typing import List

import redis
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from rabbitmq_client import SimulationQueue


REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
RESULTS_DIR = os.environ.get("RESULTS_DIR", "/data/results")
RESOURCES_DIR = os.environ.get("RESOURCES_DIR", "/data/resources")

redis_client = redis.Redis(host=REDIS_HOST, port=6379, db=0)

app = FastAPI()

SERVER_ROOT = os.path.dirname(__file__)

app.mount(
    "/static", StaticFiles(directory=os.path.join(SERVER_ROOT, "static")), name="static"
)

templates = Jinja2Templates(directory=os.path.join(SERVER_ROOT, "templates"))


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/submit")
async def submit_simulation(files: List[UploadFile] = File(...)):
    """Accept uploaded files, save to /data/resources/{task_id}, queue the task."""
    task_id = str(uuid.uuid4())

    uploaded_filenames = []
    task_resources_dir = os.path.join(RESOURCES_DIR, task_id)
    os.makedirs(task_resources_dir, exist_ok=True)

    for f in files:
        file_path = os.path.join(task_resources_dir, f.filename)
        with open(file_path, "wb") as out:
            out.write(await f.read())
        uploaded_filenames.append(f.filename)

    payload = {
        "task_id": task_id,
        "resources_dir": task_resources_dir,
        "files": uploaded_filenames,
    }

    queue = SimulationQueue()
    queue.publish(task_id, payload)
    queue.close()

    redis_client.hset(
        f"task:{task_id}",
        mapping={"status": "PENDING", "files": "[]", "error": ""},
    )

    return JSONResponse(content={"task_id": task_id})


@app.get("/check/{task_id}")
async def check_task(task_id: str):
    data = redis_client.hgetall(f"task:{task_id}")

    if not data:
        return JSONResponse(content={"status": "NOT_FOUND"}, status_code=404)

    status = data[b"status"].decode()
    response = {"task_id": task_id, "status": status}

    if status == "DONE":
        files = json.loads(data.get(b"files", b"[]"))
        response["files"] = files
        response["downloads"] = [f"/download/{task_id}/{f}" for f in files]
    elif status == "ERROR":
        response["error"] = data.get(b"error", b"").decode()

    return JSONResponse(content=response)


@app.get("/list_files/{task_id}")
async def list_files(task_id: str):
    task_dir = os.path.join(RESULTS_DIR, task_id)

    if not os.path.isdir(task_dir):
        return JSONResponse(
            content={"error": "No results directory found"}, status_code=404
        )

    files = []
    for root, _, filenames in os.walk(task_dir):
        for f in filenames:
            rel = os.path.relpath(os.path.join(root, f), task_dir)
            files.append(rel)

    return JSONResponse(content={"task_id": task_id, "files": files})


@app.get("/download/{task_id}/{filename:path}")
async def download_file(task_id: str, filename: str):
    file_path = os.path.join(RESULTS_DIR, task_id, filename)

    if not os.path.isfile(file_path):
        return JSONResponse(content={"error": "File not found"}, status_code=404)

    media_type, _ = mimetypes.guess_type(filename)

    return FileResponse(
        path=file_path,
        filename=os.path.basename(filename),
        media_type=media_type or "application/octet-stream",
    )
