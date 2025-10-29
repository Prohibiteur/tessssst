#!/usr/bin/env python3
# CORD ULTIMATE v14 – 100µs SPAM – RATE LIMIT DÉFIÉ
# python3 cord_ultimate_v14.py → http://localhost:5000

import requests
import json
import time
import threading
import random
import os
import uuid
import mimetypes
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify
from concurrent.futures import ThreadPoolExecutor

# === CONFIG ===
API_BASE = "https://discord.com/api/v9"
TOKENS_FILE = "tokens.json"
MEDIA_DIR = "media"
IMAGES_DIR = os.path.join(MEDIA_DIR, "images")
VIDEOS_DIR = os.path.join(MEDIA_DIR, "videos")
TEXTS_DIR = os.path.join(MEDIA_DIR, "texts")
LOGS_DIR = "logs"
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)
os.makedirs(TEXTS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

app = Flask(__name__, static_folder=MEDIA_DIR)
logs = []
lock = threading.Lock()
executor = ThreadPoolExecutor(max_workers=100)  # 100 threads max

# === SELF-BOT CLASS ===
class DiscordBot:
    def __init__(self, token):
        self.token = token.strip()
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": self.token,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
            "Origin": "https://discord.com",
            "Referer": "https://discord.com/channels/@me"
        })
        self.online = True

    def send_message(self, channel_id, content, file_path=None):
        url = f"{API_BASE}/channels/{channel_id}/messages"
        payload = {"content": content}
        files = None

        if file_path and os.path.exists(file_path):
            if file_path.endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = [l.strip() for l in f if l.strip()]
                if lines:
                    payload["content"] = random.choice(lines) + (f"\n{content}" if content else "")
            else:
                mime = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
                files = {'file': (os.path.basename(file_path), open(file_path, 'rb'), mime)}

        try:
            r = self.session.post(url, data=json.dumps(payload) if not files else None, files=files, timeout=3)
            if r.status_code == 429:
                return "RATE", r.json().get("retry_after", 0)
            return "OK", r.status_code in (200, 201)
        except:
            return "ERR", None
        finally:
            if files:
                files['file'][1].close()

# === TOKENS ===
def load_tokens():
    if os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, 'r') as f:
            return [t for t in json.load(f) if t.strip()]
    return []

# === ULTRA-FAST SPAM ENGINE ===
def ultra_spam(channel_id, message, count, media_paths, target1, target2, tokens, use_switch):
    bots = [DiscordBot(t) for t in tokens]
    cycle = media_paths * max(1, count // len(media_paths) + 1) if media_paths else [None] * count
    content = f"#{message}\n<@{target1}> " * 5 + f"<@{target2}> " * 5

    def send_one(i):
        file_path = cycle[i % len(cycle)]
        bot = bots[i % len(bots)]
        status, _ = bot.send_message(channel_id, content, file_path)
        if status == "RATE" and use_switch:
            bots.remove(bot)  # Switch token
            if bots:
                bot = bots[i % len(bots)]
                bot.send_message(channel_id, content, file_path)
        log(f"[{bot.token[:8]}...] {i+1}/{count}: {status}")

    # ENVOI EN PARALLÈLE
    futures = [executor.submit(send_one, i) for i in range(count)]
    for f in futures:
        f.result(timeout=1)
    log("ULTRA SPAM TERMINÉ")

# === VOCAL + STATUS ===
def join_voice(guild_id, bot):
    try:
        r = bot.session.get(f"{API_BASE}/guilds/{guild_id}")
        if r.status_code != 200: return
        channels = [c for c in r.json().get("channels", []) if c["type"] == 2]
        if channels:
            vc = random.choice(channels)
            bot.session.patch(f"{API_BASE}/users/@me/voice-state", json={
                "channel_id": vc["id"], "guild_id": guild_id
            })
            log(f"Vocal: {vc['name']}")
    except: pass

def change_status(bot):
    status = random.choice(["online", "idle", "dnd", "invisible"])
    try:
        bot.session.patch(f"{API_BASE}/users/@me/settings", json={"status": status})
    except: pass

# === LOGS ===
def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    with lock:
        logs.append(entry)
        if len(logs) > 500: logs.pop(0)
    print(entry)
    with open(f"{LOGS_DIR}/cord.log", "a", encoding="utf-8") as f:
        f.write(entry + "\n")

# === HTML ===
HTML = '''<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Cord v14</title>
<style>
    body {background:#fff;color:#000;font-family:Arial;padding:16px;}
    input,button {background:#f8f8f8;color:#000;border:1px solid #ddd;padding:12px;margin:6px;border-radius:8px;width:100%;}
    button {background:#eee;font-weight:bold;}
    .section {margin:20px 0;padding:16px;border:1px solid #eee;border-radius:12px;background:#fcfcfc;}
    #logs {background:#fff;height:350px;overflow:auto;padding:12px;border:1px solid #eee;white-space:pre;font-size:12px;}
</style></head><body>
<h1>Cord v14 – 100µs SPAM</h1>

<div class="section">
    <input type="text" id="token" placeholder="Token...">
    <button onclick="add()">Ajouter Token</button>
</div>

<div class="section">
    <input type="text" id="channel" placeholder="Channel ID">
    <input type="text" id="msg" placeholder="Message">
    <input type="number" id="count" value="500">
    <input type="text" id="t1" placeholder="User ID 1">
    <input type="text" id="t2" placeholder="User ID 2">
    <input type="file" id="files" multiple>
    <button onclick="upload()">Upload</button>
    <div id="list">Aucun</div>
    <label><input type="checkbox" id="switch"> Token Switch</label>
    <button onclick="start()">SPAM 100µs</button>
</div>

<div class="section">
    <input type="text" id="guild" placeholder="Guild ID">
    <button onclick="vocal()">Spam Vocal</button>
</div>

<div class="section"><div id="logs">...</div></div>

<script>
let files = [];
function add() { /* ... même que avant ... */ }
function upload() { /* ... */ }
function start() {
    const data = {
        c: document.getElementById('channel').value,
        m: document.getElementById('msg').value,
        n: +document.getElementById('count').value,
        t1: document.getElementById('t1').value,
        t2: document.getElementById('t2').value,
        files: files,
        sw: document.getElementById('switch').checked
    };
    fetch('/spam', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)})
        .then(r=>r.json()).then(d=>alert(d.msg));
}
function vocal() {
    fetch('/vocal', {method:'POST', headers:{'Content-Type':'application/json'}, 
        body:JSON.stringify({g: document.getElementById('guild').value})})
        .then(r=>r.json()).then(d=>alert(d.msg));
}
setInterval(() => fetch('/logs').then(r=>r.text()).then(t=>document.getElementById('logs').textContent = t), 800);
</script>
</body></html>'''

# === ROUTES ===
@app.route("/"); def index(): return HTML
@app.route("/logs"); def get_logs(): return "\n".join(logs[-300:]) + "\n"

@app.route("/token", methods=["POST"])
def add_token():
    t = request.json.get("t", "").strip()
    if len(t) < 50: return jsonify({"msg": "Invalid"}), 400
    tokens = load_tokens()
    if t not in tokens: tokens.append(t); open(TOKENS_FILE, 'w').write(json.dumps(tokens))
    return jsonify({"msg": "Ajouté"})

@app.route("/upload", methods=["POST"])
def upload():
    saved = []
    for f in request.files.getlist("file"):
        path = os.path.join(TEXTS_DIR if f.filename.endswith('.txt') else VIDEOS_DIR if 'video' in f.content_type else IMAGES_DIR, f.filename)
        f.save(path)
        saved.append(path)
    return jsonify({"files": saved})

@app.route("/spam", methods=["POST"])
def spam():
    data = request.json
    tokens = load_tokens()
    if not tokens: return jsonify({"msg": "No tokens"}), 400
    threading.Thread(target=ultra_spam, args=(
        data["c"], data["m"], data["n"], data.get("files", []),
        data["t1"], data["t2"], tokens, data.get("sw", False)
    ), daemon=True).start()
    return jsonify({"msg": "ULTRA SPAM LANCÉ – 100µs"})

@app.route("/vocal", methods=["POST"])
def vocal():
    guild_id = request.json["g"]
    tokens = load_tokens()
    bots = [DiscordBot(t) for t in tokens]
    for bot in bots:
        threading.Thread(target=join_voice, args=(guild_id, bot), daemon=True).start()
        threading.Thread(target=change_status, args=(bot,), daemon=True).start()
    return jsonify({"msg": "Vocal + Status ON"})

# === LANCEMENT ===
if __name__ == "__main__":
    log("CORD v14 – 100µs SPAM ON")
    try: import webbrowser; webbrowser.open("http://localhost:5000")
    except: pass
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)