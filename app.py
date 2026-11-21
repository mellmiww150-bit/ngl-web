"""
NGL Spammer Tool — Web Version (Flask)
PROJ3CTX SPAM NGL
Developed by JARVIS — Web build by CyonaraAI
"""

from __future__ import annotations

import random
import threading
import time
import urllib.parse

try:
    from flask import Flask, jsonify, render_template, request
except ImportError:
    import os
    import sys
    os.system(f"{sys.executable} -m pip install flask --break-system-packages")
    from flask import Flask, jsonify, render_template, request

try:
    import requests
except ImportError:
    import os
    import sys
    os.system(f"{sys.executable} -m pip install requests --break-system-packages")
    import requests


app = Flask(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
    "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.64 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
]

JOBS = {}
JOBS_LOCK = threading.Lock()
JOB_COUNTER = 0


def extract_username(url: str) -> str:
    parsed = urllib.parse.urlparse(url.strip())
    path = parsed.path if parsed.path else parsed.geturl()
    segments = [s for s in path.split("/") if s]
    if segments:
        return segments[-1].split("?")[0]
    return ""


def random_device_id() -> str:
    return (
        f"{random.randint(10000000, 99999999)}-"
        f"{random.randint(1000, 9999)}-"
        f"{random.randint(1000, 9999)}-"
        f"{random.randint(1000, 9999)}-"
        f"{random.randint(100000000000, 999999999999)}"
    )


def send_single(target_url: str, username: str, message: str, proxies: list) -> tuple:
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://ngl.link",
        "Referer": target_url,
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "th-TH,th;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    payload = {
        "username": username,
        "question": message,
        "deviceId": random_device_id(),
        "gameSlug": "",
        "referrer": "",
    }

    proxy = random.choice(proxies) if proxies else None
    proxy_dict = {"http": proxy, "https": proxy} if proxy else None

    try:
        r = requests.post(
            "https://ngl.link/api/submit",
            data=payload,
            headers=headers,
            timeout=10,
            proxies=proxy_dict,
        )
        if r.status_code == 200:
            text = (r.text or "").lower()
            if any(k in text for k in ("error", "blocked", "too many")):
                return False, True
            return True, False
        if r.status_code in (429, 403):
            return False, True
        return False, False
    except Exception:
        return False, False


def run_job(job_id: int, target_url: str, message: str, count: int, proxies: list):
    username = extract_username(target_url)
    if not username:
        with JOBS_LOCK:
            JOBS[job_id]["status"] = "error"
            JOBS[job_id]["error"] = "ดึง Username ไม่ได้ ตรวจสอบลิงก์"
        return

    success = 0
    blocked = 0
    failed = 0

    with JOBS_LOCK:
        JOBS[job_id]["status"] = "running"
        JOBS[job_id]["total"] = count
        JOBS[job_id]["username"] = username

    for i in range(count):
        s, b = send_single(target_url, username, message, proxies)
        if s:
            success += 1
        elif b:
            blocked += 1
            time.sleep(1.2)
        else:
            failed += 1

        with JOBS_LOCK:
            JOBS[job_id]["success"] = success
            JOBS[job_id]["blocked"] = blocked
            JOBS[job_id]["failed"] = failed
            JOBS[job_id]["done"] = success + blocked + failed

        time.sleep(random.uniform(0.1, 0.3))

    with JOBS_LOCK:
        JOBS[job_id]["status"] = "finished"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/start", methods=["POST"])
def start():
    global JOB_COUNTER
    data = request.get_json(silent=True) or {}
    target_url = (data.get("url") or "").strip()
    message = (data.get("message") or "").strip()
    try:
        count = int(data.get("count") or 0)
    except (TypeError, ValueError):
        count = 0
    proxy_text = (data.get("proxies") or "").strip()

    if not target_url or not message:
        return jsonify({"error": "กรอก URL กับข้อความให้ครบ"}), 400
    if count < 1 or count > 2000:
        return jsonify({"error": "จำนวนต้องอยู่ระหว่าง 1 - 2000"}), 400

    proxies = [p.strip() for p in proxy_text.splitlines() if p.strip()]

    with JOBS_LOCK:
        JOB_COUNTER += 1
        job_id = JOB_COUNTER
        JOBS[job_id] = {
            "id": job_id,
            "status": "queued",
            "total": count,
            "success": 0,
            "blocked": 0,
            "failed": 0,
            "done": 0,
            "error": None,
            "username": extract_username(target_url),
        }

    t = threading.Thread(
        target=run_job,
        args=(job_id, target_url, message, count, proxies),
        daemon=True,
    )
    t.start()

    return jsonify({"job_id": job_id})


@app.route("/api/status/<int:job_id>", methods=["GET"])
def status(job_id: int):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "ไม่พบ job"}), 404
    return jsonify(job)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)