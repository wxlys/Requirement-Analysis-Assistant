from __future__ import annotations

import argparse
import getpass
import json
import os
import secrets
import threading
import time
import uuid
from datetime import datetime
from functools import wraps
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import Flask, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from test_case_generation.render_test_cases import render as render_test_cases


ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(ROOT))).resolve()
OPENCODE_URL = os.getenv("OPENCODE_URL", "http://127.0.0.1:4096").rstrip("/")
AUTH_FILE = DATA_DIR / "auth.json"
JOBS_FILE = DATA_DIR / "jobs.json"
DATA_WORKSPACES = DATA_DIR / "workspaces"
# 工作区入口在项目根目录（软链接到 DATA_DIR/workspaces），
# 使 opencode 的 read 工具路径落在 git 仓库内，避免对仓库外路径挂起
WORKSPACES_DIR = ROOT / "workspaces"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"

app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()


@app.context_processor
def inject_static_version():
    return {"static_version": static_version()}


def static_version() -> str:
    """按静态资源实际修改时间生成版本号：文件变了版本号才变，浏览器据此决定是否刷新缓存。"""
    try:
        files = list(Path(app.static_folder).rglob("*.js")) + list(Path(app.static_folder).rglob("*.css"))
        mtimes = [int(f.stat().st_mtime) for f in files if f.is_file()]
        return str(max(mtimes)) if mtimes else "1"
    except Exception:
        return "1"


def ensure_auth() -> None:
    if AUTH_FILE.is_file():
        return
    AUTH_FILE.write_text(
        json.dumps(
            {
                "username": DEFAULT_USERNAME,
                "password_hash": generate_password_hash(DEFAULT_PASSWORD),
                "secret_key": secrets.token_hex(32),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[!] 首次运行已创建默认账号 {DEFAULT_USERNAME}/{DEFAULT_PASSWORD}")
    print("[!] 请立即通过页面右上角“账号设置”或 `python app.py set-password` 修改")


def load_auth() -> dict:
    ensure_auth()
    return json.loads(AUTH_FILE.read_text(encoding="utf-8"))


def save_auth(data: dict) -> None:
    AUTH_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


ensure_auth()
app.secret_key = load_auth()["secret_key"]


def load_jobs() -> None:
    global jobs
    if JOBS_FILE.is_file():
        try:
            jobs = json.loads(JOBS_FILE.read_text(encoding="utf-8"))
        except Exception:
            app.logger.exception("load jobs failed")
            jobs = {}


def save_jobs() -> None:
    JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with jobs_lock:
        snapshot = {jid: dict(job) for jid, job in jobs.items()}
    JOBS_FILE.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")


def doc_display_name(ws_dir: Path) -> str:
    docs = sorted(ws_dir.glob("需求文档-*"))
    if not docs:
        return ""
    doc = docs[0]
    if doc.suffix.lower() == ".md":
        try:
            for line in doc.read_text(encoding="utf-8").splitlines():
                if line.startswith("#"):
                    return line.lstrip("#").strip() or doc.name
        except Exception:
            pass
    return doc.name


def backfill_jobs() -> None:
    DATA_WORKSPACES.mkdir(parents=True, exist_ok=True)
    changed = False
    for ws_dir in DATA_WORKSPACES.iterdir():
        if not ws_dir.is_dir():
            continue
        job_id = ws_dir.name
        if job_id in jobs:
            if not jobs[job_id].get("original_name"):
                jobs[job_id]["original_name"] = doc_display_name(ws_dir)
                jobs[job_id]["message"] = "历史任务（服务升级前创建）"
                changed = True
            continue
        original_name = doc_display_name(ws_dir)
        if (ws_dir / "test_case_generation" / "test_cases.json").is_file():
            status = "completed"
        elif (ws_dir / "output" / "reports" / "validation.json").is_file():
            status = "human_required"
        else:
            status = "unknown"
        try:
            now = datetime.fromtimestamp(ws_dir.stat().st_mtime).isoformat(timespec="seconds")
        except Exception:
            now = datetime.now().isoformat(timespec="seconds")
        jobs[job_id] = {
            "id": job_id,
            "filename": original_name,
            "original_name": original_name,
            "status": status,
            "message": "历史任务（服务升级前创建）",
            "created_at": now,
            "updated_at": now,
        }
        changed = True
    if changed:
        save_jobs()


load_jobs()
backfill_jobs()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "未登录"}), 401
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


@app.get("/login")
def login():
    return render_template("login.html")


@app.post("/login")
def login_submit():
    auth = load_auth()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if username == auth["username"] and check_password_hash(auth["password_hash"], password):
        session["user"] = username
        return redirect(url_for("index"))
    return render_template("login.html", error="账号或密码错误"), 401


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/")
@login_required
def index():
    return render_template("index.html")


@app.get("/api/account")
@login_required
def account():
    return jsonify({"username": session["user"]})


@app.post("/api/account")
@login_required
def account_update():
    body = request.get_json(silent=True) or {}
    auth = load_auth()
    if not check_password_hash(auth["password_hash"], body.get("current_password", "")):
        return jsonify({"error": "当前密码错误"}), 400
    username = body.get("username", "").strip()
    if not username:
        return jsonify({"error": "用户名不能为空"}), 400
    new_password = body.get("new_password", "")
    auth["username"] = username
    if new_password:
        auth["password_hash"] = generate_password_hash(new_password)
    save_auth(auth)
    session["user"] = username
    return jsonify({"ok": True, "username": username})


@app.post("/api/jobs")
@login_required
def create_job():
    uploaded = request.files.get("requirement")
    if not uploaded or not uploaded.filename:
        return jsonify({"error": "请上传需求文档"}), 400

    suffix = Path(uploaded.filename).suffix.lower()
    if suffix not in {".md", ".txt", ".docx", ".pdf"}:
        return jsonify({"error": "仅支持 Markdown、TXT、DOCX 或 PDF 文件"}), 400

    ensure_workspaces()
    job_id = uuid.uuid4().hex[:12]
    original_name = Path(uploaded.filename).name
    filename = f"需求文档-{job_id}{suffix}"
    workspace = WORKSPACES_DIR / job_id
    workspace.mkdir(parents=True, exist_ok=True)
    uploaded.save(workspace / filename)
    now = datetime.now().isoformat(timespec="seconds")
    with jobs_lock:
        jobs[job_id] = {
            "id": job_id,
            "filename": filename,
            "original_name": original_name,
            "status": "queued",
            "message": "任务已提交",
            "created_at": now,
            "updated_at": now,
        }
    save_jobs()
    threading.Thread(target=run_job, args=(job_id,), daemon=True).start()
    return jsonify(public_job(job_id)), 202


@app.get("/api/jobs")
@login_required
def list_jobs():
    with jobs_lock:
        job_ids = list(jobs)
    items = [public_job(jid) for jid in job_ids]
    items.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return jsonify({"jobs": items})


@app.get("/api/jobs/<job_id>")
@login_required
def get_job(job_id: str):
    if job_id not in jobs:
        return jsonify({"error": "任务不存在"}), 404
    return jsonify(public_job(job_id))


@app.get("/api/jobs/<job_id>/download/<artifact>")
@login_required
def download(job_id: str, artifact: str):
    if job_id not in jobs:
        return jsonify({"error": "任务不存在"}), 404
    workspace = WORKSPACES_DIR / job_id
    files = {
        "analysis": workspace / "output" / "需求分析结果.md",
        "analysis-json": workspace / "output" / "validated" / "analysis.json",
        "test-cases": workspace / "test_case_generation" / "test_cases.json",
        "test-cases-md": workspace / "test_case_generation" / "test_cases.md",
    }
    path = files.get(artifact)
    if path is None or not path.is_file():
        return jsonify({"error": "文件暂不可下载"}), 404
    return send_file(path, as_attachment=True, download_name=path.name)


def public_job(job_id: str) -> dict:
    with jobs_lock:
        job = dict(jobs[job_id])
    job.pop("filename", None)
    job.setdefault("original_name", "")
    return job


def ensure_workspaces() -> None:
    DATA_WORKSPACES.mkdir(parents=True, exist_ok=True)
    if WORKSPACES_DIR.is_symlink() or WORKSPACES_DIR.exists():
        if WORKSPACES_DIR.is_symlink():
            return
        for child in list(WORKSPACES_DIR.iterdir()):
            (DATA_WORKSPACES / child.name).mkdir(parents=True, exist_ok=True)
            child.rename(DATA_WORKSPACES / child.name)
        WORKSPACES_DIR.rmdir()
    WORKSPACES_DIR.symlink_to(DATA_WORKSPACES, target_is_directory=True)


def run_job(job_id: str) -> None:
    update_job(job_id, status="analyzing", message="正在进行需求分析")
    workspace = WORKSPACES_DIR / job_id
    try:
        session = opencode("POST", "/session", {"title": f"需求分析任务 {job_id}"})
        session_id = session["id"]
        filename = jobs[job_id]["filename"]
        send_message(session_id, f"/analyze-requirement {filename} {workspace}")
        report = read_json(workspace / "output" / "reports" / "validation.json")
        if not report.get("passed"):
            update_job(job_id, status="human_required", message="需求分析未通过，需要人工修复 analysis.json")
            return

        update_job(job_id, status="generating", message="正在生成并校验测试用例")
        send_message(session_id, f"/generate-test-cases {workspace}")
        case_report = read_json(workspace / "test_case_generation" / "reports" / "validation.json")
        if not case_report.get("passed"):
            update_job(job_id, status="human_required", message="测试用例校验未通过，需要人工处理")
            return
        render_test_case_markdown(workspace)
        update_job(job_id, status="completed", message="处理完成，可下载结果")
    except Exception as exc:  # The UI gets a safe message; details remain server-side.
        app.logger.exception("job %s failed", job_id)
        update_job(job_id, status="failed", message=f"后台执行失败：{exc}")


def send_message(session_id: str, text: str) -> dict:
    return opencode("POST", f"/session/{session_id}/message", {"parts": [{"type": "text", "text": text}]})


def opencode_auth_key() -> str | None:
    candidates = [os.getenv("XDG_DATA_HOME"), str(Path.home() / ".local" / "share")]
    for base in candidates:
        if not base:
            continue
        auth_file = Path(base) / "opencode" / "auth.json"
        if not auth_file.is_file():
            continue
        try:
            data = json.loads(auth_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        for entry in data.values():
            if isinstance(entry, dict) and entry.get("key"):
                return str(entry["key"])
    return None


def opencode(method: str, path: str, body: dict | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    key = opencode_auth_key()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    response = urlopen(Request(f"{OPENCODE_URL}{path}", data=data, method=method, headers=headers), timeout=1800)
    return json.loads(response.read().decode("utf-8"))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def render_test_case_markdown(workspace: Path) -> None:
    cases_path = workspace / "test_case_generation" / "test_cases.json"
    output_path = workspace / "test_case_generation" / "test_cases.md"
    if cases_path.is_file():
        document = json.loads(cases_path.read_text(encoding="utf-8"))
        output_path.write_text(render_test_cases(document), encoding="utf-8")


def update_job(job_id: str, **values: str) -> None:
    with jobs_lock:
        jobs[job_id].update(values)
        jobs[job_id]["updated_at"] = datetime.now().isoformat(timespec="seconds")
    save_jobs()


def cli_set_password() -> int:
    ensure_auth()
    auth = load_auth()
    username = input(f"用户名 [{auth['username']}]: ").strip() or auth["username"]
    password = getpass.getpass("新密码: ")
    confirm = getpass.getpass("确认密码: ")
    if not username or not password:
        print("用户名和密码不能为空")
        return 1
    if password != confirm:
        print("两次输入不一致")
        return 1
    auth["username"] = username
    auth["password_hash"] = generate_password_hash(password)
    save_auth(auth)
    print("登录账号已更新")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="需求分析助手 Web 服务")
    parser.add_argument("command", nargs="?", help="set-password: 修改登录账号密码")
    args = parser.parse_args()
    if args.command == "set-password":
        return cli_set_password()
    app.run(host=os.getenv("WEB_HOST", "127.0.0.1"), port=int(os.getenv("WEB_PORT", "8080")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
