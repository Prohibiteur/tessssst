#!/usr/bin/env python3
# CORD ULTIMATE v13 – SPAM VOCAL + STATUS RANDOM + 1ms + TOKEN SWITCH
# python3 cord_ultimate_v13.py → http://localhost:5000

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

# === STATUS LIST ===
STATUSES = ["online", "idle", "dnd", "invisible"]

# === USER AGENTS ===
user_agents = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
    "Mozilla/5.0 (Linux; Android 13; SM-S901B)"
]

# === DISCORD SELF-BOT CLASS ===
class DiscordBot:
    def __init__(self, token):
        self.token = token.strip()
        self.session = requests.Session()
        self.online = True
        self.current_channel = None
        self.setup_headers()
        self.start_heartbeat()
        self.change_status_random()

    def setup_headers(self):
        self.session.headers.update({
            "Authorization": self.token,
            "Content-Type": "application/json",
            "User-Agent": random.choice(user_agents),
            "Origin": "https://discord.com",
            "Referer": "https://discord.com/channels/@me"
        })

    def start_heartbeat(self):
        def hb():
            while self.online:
                try:
                    self.session.get(f"{API_BASE}/users/@me", timeout=10)
                    time.sleep(25 + random.uniform(0, 5))
                except:
                    time.sleep(5)
        threading.Thread(target=hb, daemon=True).start()

    def change_status_random(self):
        status = random.choice(STATUSES)
        payload = {"status": status}
        try:
            self.session.patch(f"{API_BASE}/users/@me/settings", json=payload)
            log(f"Status → {status}")
        except:
            pass

    def join_random_voice(self, guild_id):
        try:
            r = self.session.get(f"{API_BASE}/guilds/{guild_id}")
            if r.status_code != 200: return
            guild = r.json()
            voice_channels = [c for c in guild.get("channels", []) if c["type"] == 2]
            if not voice_channels: return
            vc = random.choice(voice_channels)
            payload = {
                "channel_id": vc["id"],
                "guild_id": guild_id,
                "self_mute": False,
                "self_deaf": False
            }
            self.session.patch(f"{API_BASE}/users/@me/voice-state", json=payload)
            log(f"Join vocal: {vc['name']} ({vc['id']})")
        except Exception as e:
            log(f"Erreur vocal: {e}")

    def send_typing(self, channel_id):
        try:
            self.session.post(f"{API_BASE}/channels/{channel_id}/typing", timeout=5)
        except:
            pass

    def send_message(self, channel_id, content="", file_path=None):
        self.send_typing(channel_id)
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
            r = self.session.post(url, data=json.dumps(payload) if not files else None, files=files, timeout=15)
            if r.status_code == 429:
                return "RATE_LIMIT", r.json()
            return "OK", r.status_code in (200, 201)
        except Exception as e:
            return "ERROR", str(e)
        finally:
            if files:
                files['file'][1].close()

# === TOKENS ===
def load_tokens():
    if os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, 'r') as f:
            return [t for t in json.load(f) if t.strip()]
    return []

def save_tokens(tokens):
    with open(TOKENS_FILE, 'w') as f:
        json.dump([t.strip() for t in tokens if t.strip()], f, indent=2)

# === PING BUILDER ===
def build_message(base_msg, target1, target2):
    pings = f"<@{target1}> " * 5 + f"<@{target2}> " * 5
    return f"#{base_msg}\n{pings}".strip()

# === SPAM ENGINE (1ms + TOKEN SWITCH) ===
def spam_task(channel_id, message, count, media_paths, target1, target2, bots, use_switch):
    cycle = media_paths * max(1, count // len(media_paths) + 1) if media_paths else [None] * count
    active_bots = bots.copy()

    for i in range(count):
        content = build_message(message, target1, target2)
        file_path = cycle[i % len(cycle)]

        # Rotation des bots
        bot = active_bots[i % len(active_bots)]
        status, result = bot.send_message(channel_id, content, file_path)

        if status == "RATE_LIMIT" and use_switch:
            retry_after = result.get("retry_after", 1)
            log(f"Rate limit → Switch token ({retry_after}s)")
            # Retire le bot en rate limit
            if bot in active_bots:
                active_bots.remove(bot)
            if not active_bots:
                log("Plus de tokens dispo")
                break
            bot = active_bots[i % len(active_bots)]  # Nouveau bot
            status, _ = bot.send_message(channel_id, content, file_path)

        log(f"[{bot.token[:8]}...] {i+1}/{count}: {status}")
        time.sleep(0.001)  # 1ms – ultra-rapide

    log("Spam terminé.")

# === VOCAL SPAM ===
def vocal_spam(guild_id, bots):
    for bot in bots:
        threading.Thread(target=bot.join_random_voice, args=(guild_id,), daemon=True).start()
    log(f"Spam vocal lancé sur {len(bots)} comptes")

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

# === HTML INTERFACE ===
HTML = '''<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Cord v13</title>
<style>
    body {background:#fff;color:#000;font-family:Arial;padding:16px;margin:0;}
    h1 {text-align:center;margin:20px 0;}
    input,button {background:#f8f8f8;color:#000;border:1px solid #ddd;padding:12px;margin:6px;border-radius:8px;width:100%;font-size:14px;}
    button {background:#eee;font-weight:bold;cursor:pointer;}
    button:hover {background:#ddd;}
    .section {margin:20px 0;padding:16px;border:1px solid #eee;border-radius:12px;background:#fcfcfc;}
    #logs {background:#fff;height:320px;overflow:auto;padding:12px;border:1px solid #eee;white-space:pre;font-family:monospace;font-size:12px;}
    .file-list {max-height:120px;overflow:auto;margin:8px 0;padding:8px;background:#f0f0f0;border-radius:6px;}
    .checkbox {width:auto;display:inline;}
</style></head><body>
<h1>Cord Ultimate v13</h1>

<div class="section">
    <h3>Token</h3>
    <input type="text" id="token" placeholder="Token...">
    <button onclick="add()">Ajouter</button>
</div>

<div class="section">
    <h3>Spam</h3>
    <input type="text" id="channel" placeholder="Channel ID">
    <input type="text" id="msg" placeholder="Message (#gros)">
    <input type="number" id="count" value="100">
    <input type="text" id="t1" placeholder="User ID 1 (5 pings)">
    <input type="text" id="t2" placeholder="User ID 2 (5 pings)">
    <br>
    <input type="file" id="files" multiple accept=".txt,.jpg,.png,.gif,.mp4,.webm,.mov">
    <button onclick="upload()">Uploader</button>
    <div class="file-list" id="list">Aucun</div>
    <br>
    <label><input type="checkbox" id="switch" class="checkbox"> Token Switch Anti-Rate</label>
    <button onclick="start()">Lancer Spam (1ms)</button>
</div>

<div class="section">
    <h3>Vocal Spam</h3>
    <input type="text" id="guild" placeholder="Guild ID">
    <button onclick="vocal()">Rejoindre Vocal Aléatoire</button>
</div>

<div class="section">
    <h3>Logs</h3>
    <div id="logs">Chargement...</div>
</div>

<script>
let files = [];
function add() {
    const t = document.getElementById('token').value.trim();
    if (!t) return alert("Token vide");
    fetch('/token', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({t})})
        .then(r=>r.json()).then(d=>{alert(d.msg); document.getElementById('token').value='';});
}
function upload() {
    const f = document.getElementById('files').files;
    if (f.length===0) return alert("Aucun fichier");
    const form = new FormData();
    for (let file of f) form.append('file', file);
    fetch('/upload', {method:'POST', body:form})
        .then(r=>r.json()).then(d=>{
            files = d.files;
            document.getElementById('list').innerHTML = files.map(x=>`• ${x.split('/').pop()}`).join('<br>');
            alert("Upload OK: " + files.length);
        });
}
function start() {
    const c = document.getElementById('channel').value;
    const m = document.getElementById('msg').value;
    const n = document.getElementById('count').value;
    const t1 = document.getElementById('t1').value;
    const t2 = document.getElementById('t2').value;
    const sw = document.getElementById('switch').checked;
    if (!c || !t1 || !t2) return alert("Remplis tout");
    fetch('/spam', {method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({c, m, n, t1, t2, files, sw})})
        .then(r=>r.json()).then(d=>alert(d.msg));
}
function vocal() {
    const g = document.getElementById('guild').value;
    if (!g) return alert("Guild ID requis");
    fetch('/vocal', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({g})})
        .then(r=>r.json()).then(d=>alert(d.msg));
}
setInterval(() => {
    fetch('/logs').then(r=>r.text()).then(t=>{
        const l = document.getElementById('logs');
        l.textContent = t;
        if (l.scrollTop > l.scrollHeight - l.clientHeight - 50) l.scrollTop = l.scrollHeight;
    });
}, 1000);
</script>
</body></html>'''

# === ROUTES ===
@app.route("/")
def index():
    return HTML

@app.route("/logs")
def get_logs():
    with lock:
        return "\n".join(logs[-200:]) + "\n"

@app.route("/token", methods=["POST"])
def add_token():
    t = request.json.get("t", "").strip()
    if len(t) < 50: return jsonify({"msg": "Invalide"}), 400
    tokens = load_tokens()
    if t not in tokens:
        tokens.append(t)
        save_tokens(tokens)
        log(f"Token ajouté")
    return jsonify({"msg": "Ajouté"})

@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("file")
    saved = []
    for f in files:
        ext = os.path.splitext(f.filename)[1].lower()
        if ext in ['.txt', '.jpg', '.png', '.gif', '.mp4', '.webm', '.mov']:
            folder = TEXTS_DIR if ext == '.txt' else VIDEOS_DIR if ext in ['.mp4','.webm','.mov'] else IMAGES_DIR
            path = os.path.join(folder, f.filename)
            f.save(path)
            saved.append(path)
            log(f"Upload: {f.filename}")
    return jsonify({"files": saved})

@app.route("/spam", methods=["POST"])
def spam():
    data = request.json
    c, m, n = data["c"], data["m"], int(data["n"])
    t1, t2 = data["t1"], data["t2"]
    media = data.get("files", [])
    switch = data.get("sw", False)
    tokens = load_tokens()
    if not tokens: return jsonify({"msg": "Aucun token"}), 400
    bots = [DiscordBot(t) for t in tokens]
    log(f"SPAM 1ms → {len(bots)} comptes | {n} msg | Switch: {switch}")
    threading.Thread(target=spam_task, args=(c, m, n, media, t1, t2, bots, switch), daemon=True).start()
    return jsonify({"msg": "Spam lancé (1ms)"})

@app.route("/vocal", methods=["POST"])
def vocal():
    guild_id = request.json.get("g")
    tokens = load_tokens()
    if not tokens: return jsonify({"msg": "Aucun token"}), 400
    bots = [DiscordBot(t) for t in tokens]
    threading.Thread(target=vocal_spam, args=(guild_id, bots), daemon=True).start()
    return jsonify({"msg": "Spam vocal lancé"})

# === LANCEMENT ===
if __name__ == "__main__":
    log("CORD v13 ON → http://localhost:5000")
    try:
        import webbrowser
        webbrowser.open("http://localhost:5000")
    except:
        pass
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False, threaded=True)