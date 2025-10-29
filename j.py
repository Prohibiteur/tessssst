#!/usr/bin/env python3
# Cord iSH – Interface Blanche Simple
# python3 cord_white.py → http://localhost:5000

import requests
import json
import time
import threading
import random
import os
from flask import Flask, render_template_string, request, jsonify
from datetime import datetime

API_BASE = "https://discord.com/api/v9"
TOKENS_FILE = "tokens.json"
IMAGES_DIR = "images/"
LOGS_DIR = "logs/"
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

app = Flask(__name__)
logs = []
lock = threading.Lock()

class DiscordBot:
    def __init__(self, token):
        self.token = token.strip()
        self.headers = {
            "Authorization": self.token,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.online = True
        self.start_heartbeat()

    def start_heartbeat(self):
        def hb():
            while self.online:
                try:
                    self.session.get(f"{API_BASE}/users/@me", timeout=10)
                    time.sleep(25 + random.uniform(0, 5))
                except:
                    time.sleep(5)
        threading.Thread(target=hb, daemon=True).start()

    def send_typing(self, channel_id):
        try:
            self.session.post(f"{API_BASE}/channels/{channel_id}/typing", timeout=5)
        except: pass

    def send_message(self, channel_id, content="", file_path=None):
        self.send_typing(channel_id)
        url = f"{API_BASE}/channels/{channel_id}/messages"
        payload = {"content": content}
        files = None

        if file_path:
            if file_path.endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    payload["content"] = f.read() + (f"\n{content}" if content else "")
            else:
                files = {'file': (os.path.basename(file_path), open(file_path, 'rb'), 'image/png')}

        try:
            r = self.session.post(url, data=json.dumps(payload) if not files else None, files=files, timeout=10)
            if r.status_code == 429:
                retry = r.json().get("retry_after", 1)
                log(f"Rate limit – Attente {retry + 1}s")
                time.sleep(retry + 1)
                return self.send_message(channel_id, content, file_path)
            return r.status_code in (200, 201)
        except Exception as e:
            log(f"Erreur: {e}")
            return False
        finally:
            if files: files['file'][1].close()

def load_tokens():
    if os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, 'r') as f:
            return [t for t in json.load(f) if t.strip()]
    return []

def save_tokens(tokens):
    with open(TOKENS_FILE, 'w') as f:
        json.dump([t.strip() for t in tokens if t.strip()], f, indent=2)

def build_ping_message(base_msg, target1, target2):
    pings = f"<@{target1}> " * 5 + f"<@{target2}> " * 5
    return f"#{base_msg}\n{pings}".strip()

def spam_task(channel_id, message, count, file_path, target1, target2, bots):
    for i in range(count):
        content = build_ping_message(message, target1, target2)
        for bot in bots:
            if not bot.online: continue
            success = bot.send_message(channel_id, content, file_path)
            log(f"[{bot.token[:8]}...] → {i+1}/{count} : {'OK' if success else 'FAIL'}")
            time.sleep(0.001)
        time.sleep(0.05)
    log("Spam terminé.")

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    with lock:
        logs.append(entry)
        if len(logs) > 200: logs.pop(0)
    print(entry)
    with open(f"{LOGS_DIR}cord.log", "a", encoding="utf-8") as f:
        f.write(entry + "\n")

HTML = '''
<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Cord iSH</title>
<style>
    body {background:#fff;color:#000;font-family:Arial;padding:16px;}
    input,button {background:#eee;color:#000;border:1px solid #ccc;padding:10px;margin:5px;border-radius:6px;width:100%;}
    button {background:#ddd;font-weight:bold;cursor:pointer;}
    .section {margin:16px 0;padding:12px;border:1px solid #ccc;border-radius:8px;background:#f9f9f9;}
    #logs {background:#fff;height:300px;overflow:auto;padding:10px;border:1px solid #ccc;white-space:pre;font-size:12px;}
    .checkbox {width:auto;display:inline;}
</style></head><body>
<h1 style="text-align:center;">Cord iSH</h1>

<div class="section">
    <h3>Ajouter Token</h3>
    <input type="text" id="token" placeholder="d1X..."><button onclick="add()">Ajouter</button>
</div>

<div class="section">
    <h3>Spam</h3>
    <input type="text" id="channel" placeholder="Channel ID">
    <input type="text" id="msg" placeholder="Message (sera en #gros)">
    <input type="number" id="count" value="20">
    <input type="text" id="target1" placeholder="User ID 1 (5 pings)">
    <input type="text" id="target2" placeholder="User ID 2 (5 pings)">
    <br><input type="file" id="file" accept=".txt,image/*">
    <button onclick="start()">Lancer Spam</button>
</div>

<div class="section"><h3>Logs</h3><div id="logs">Chargement...</div></div>

<script>
function add() {
    const t = document.getElementById('token').value.trim();
    if(!t) return alert("Token vide");
    fetch('/token', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({t})})
        .then(r=>r.json()).then(d=> {alert(d.msg); document.getElementById('token').value='';});
}
function start() {
    const c = document.getElementById('channel').value;
    const m = document.getElementById('msg').value;
    const n = document.getElementById('count').value;
    const t1 = document.getElementById('target1').value;
    const t2 = document.getElementById('target2').value;
    const f = document.getElementById('file').files[0];
    if(!c || !t1 || !t2) return alert("Channel + 2 cibles requises");

    const form = new FormData();
    form.append('c', c); form.append('m', m); form.append('n', n);
    form.append('t1', t1); form.append('t2', t2);
    if(f) form.append('file', f);

    fetch('/spam', {method:'POST', body:form})
        .then(r=>r.json()).then(d=>alert(d.msg));
}
setInterval(() => {
    fetch('/logs').then(r=>r.text()).then(t=> {
        const l = document.getElementById('logs');
        l.textContent = t;
        if(l.scrollTop > l.scrollHeight - l.clientHeight - 50) l.scrollTop = l.scrollHeight;
    });
}, 1500);
</script>
</body></html>
'''

@app.route('/'); def index(): return HTML
@app.route('/logs'); def get_logs(): return '\n'.join(logs[-100:]) + '\n'

@app.route('/token', methods=['POST'])
def add_token():
    t = request.json.get('t', '').strip()
    if len(t) < 50: return jsonify({"msg": "Invalide"}), 400
    tokens = load_tokens()
    if t not in tokens: tokens.append(t); save_tokens(tokens); log(f"Token ajouté")
    return jsonify({"msg": "Ajouté"})

@app.route('/spam', methods=['POST'])
def spam():
    c, m, n = request.form['c'], request.form['m'], int(request.form['n'])
    t1, t2 = request.form['t1'], request.form['t2']
    file = request.files.get('file')
    file_path = None
    if file:
        file_path = os.path.join(IMAGES_DIR, file.filename)
        file.save(file_path)
        log(f"Upload: {file.filename}")

    tokens = load_tokens()
    if not tokens: return jsonify({"msg": "Pas de token"}), 400
    bots = [DiscordBot(t) for t in tokens]
    log(f"Spam lancé → {len(bots)} comptes | {n} msg | @ {t1} & {t2}")
    threading.Thread(target=spam_task, args=(c, m, n, file_path, t1, t2, bots), daemon=True).start()
    return jsonify({"msg": "Spam lancé"})

if __name__ == '__main__':
    log("Cord démarré → http://localhost:5000")
    try: import webbrowser; webbrowser.open('http://localhost:5000')
    except: pass
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)