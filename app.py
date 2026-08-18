from __future__ import annotations

import json
import os
import threading
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import Flask, jsonify, render_template, request, send_file


ROOT = Path(__file__).resolve().parent
OPENCODE_URL = os.getenv("OPENCODE_URL", "http://127.0.0.1:4096").rstrip("/")
app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/jobs")
def create_job():
    uploaded = request.files.get("requirement")
    if not uploaded or not uploaded.filename:
        return jsonify({"error": "请上传需求文档"}), 400

    suffix = Path(uploaded.filename).suffix.lower()
    if suffix not in {".md", ".txt", ".docx", ".pdf"}:
        return jsonify({"error": "仅支持 Markdown、TXT、DOCX 或 PDF 文件"}), 400

    job_id = uuid.uuid4().hex[:12]
    filename = f"需求文档-{job_id}{suffix}"
    destination = ROOT / filename
    uploaded.save(destination)
    with jobs_lock:
        jobs[job_id] = {
            "id": job_id,
            "filename": filename,
            "status": "queued",
            "message": "任务已提交",
        }
    threading.Thread(target=run_job, args=(job_id,), daemon=True).start()
    return jsonify(public_job(job_id)), 202


@app.get("/api/jobs/<job_id>")
def get_job(job_id: str):
    if job_id not in jobs:
        return jsonify({"error": "任务不存在"}), 404
    return jsonify(public_job(job_id))


@app.get("/api/jobs/<job_id>/download/<artifact>")
def download(job_id: str, artifact: str):
    if job_id not in jobs:
        return jsonify({"error": "任务不存在"}), 404
    files = {
        "analysis": ROOT / "output" / "需求分析结果.md",
        "analysis-json": ROOT / "output" / "validated" / "analysis.json",
        "test-cases": ROOT / "test_case_generation" / "test_cases.json",
    }
    path = files.get(artifact)
    if path is None or not path.is_file():
        return jsonify({"error": "文件暂不可下载"}), 404
    return send_file(path, as_attachment=True, download_name=path.name)


def public_job(job_id: str) -> dict:
    with jobs_lock:
        job = dict(jobs[job_id])
    job.pop("filename", None)
    return job


def run_job(job_id: str) -> None:
    update_job(job_id, status="analyzing", message="正在进行需求分析")
    try:
        session = opencode("POST", "/session", {"title": f"需求分析任务 {job_id}"})
        session_id = session["id"]
        filename = jobs[job_id]["filename"]
        send_message(session_id, f"/analyze-requirement {filename}")
        report = read_json(ROOT / "output" / "reports" / "validation.json")
        if not report.get("passed"):
            update_job(job_id, status="human_required", message="需求分析未通过，需要人工修复 analysis.json")
            return

        update_job(job_id, status="generating", message="正在生成并校验测试用例")
        send_message(session_id, "/generate-test-cases")
        case_report = read_json(ROOT / "test_case_generation" / "reports" / "validation.json")
        if not case_report.get("passed"):
            update_job(job_id, status="human_required", message="测试用例校验未通过，需要人工处理")
            return
        update_job(job_id, status="completed", message="处理完成，可下载结果")
    except Exception as exc:  # The UI gets a safe message; details remain server-side.
        app.logger.exception("job %s failed", job_id)
        update_job(job_id, status="failed", message=f"后台执行失败：{exc}")


def send_message(session_id: str, text: str) -> dict:
    return opencode("POST", f"/session/{session_id}/message", {"parts": [{"type": "text", "text": text}]})


def opencode(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    response = urlopen(Request(f"{OPENCODE_URL}{path}", data=data, method=method, headers={"Content-Type": "application/json"}), timeout=1800)
    return json.loads(response.read().decode("utf-8"))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def update_job(job_id: str, **values: str) -> None:
    with jobs_lock:
        jobs[job_id].update(values)


if __name__ == "__main__":
    app.run(host=os.getenv("WEB_HOST", "127.0.0.1"), port=int(os.getenv("WEB_PORT", "8080")))
