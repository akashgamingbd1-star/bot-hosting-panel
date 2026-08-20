import os
import sys
import sqlite3
import subprocess
from flask import Flask, render_template_string, request, redirect, url_for

app = Flask(__name__)
app.secret_key = 'cloud_bot_hosting_secret_2026'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'user_bots')
DATABASE = os.path.join(BASE_DIR, 'platform.db')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

active_processes = {}
console_logs = "Installing requirements.txt..."

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_name TEXT NOT NULL,
            filename TEXT NOT NULL,
            status TEXT DEFAULT 'Stopped',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cloud Bot Hosting Platform</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }
        body { background-color: #121026; color: #ffffff; min-height: 100vh; padding: 20px; display: flex; flex-direction: column; align-items: center; }
        
        .container { width: 100%; max-width: 450px; }
        
        .top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .icon-circle { width: 45px; height: 45px; background: #6d28d9; border-radius: 50%; display: flex; align-items: center; justify-content: center; }
        
        .user-section { margin-bottom: 20px; }
        .user-section h3 { font-size: 14px; color: #a78bfa; font-weight: 400; }
        .user-section h1 { font-size: 20px; font-weight: 700; color: #ffffff; margin: 2px 0; }
        .user-section p { font-size: 12px; color: #9ca3af; }

        .card { background: #1e1b3c; border-radius: 20px; padding: 20px; margin-bottom: 20px; border: 1px solid #2d2657; box-shadow: 0 10px 25px rgba(0,0,0,0.4); }
        .card-title { font-size: 15px; font-weight: 600; margin-bottom: 15px; display: flex; align-items: center; gap: 8px; color: #f3e8ff; }

        .file-select-btn { display: block; width: 100%; background: #2d2657; border: 1px dashed #7c3aed; border-radius: 12px; padding: 12px; text-align: center; color: #d8b4fe; font-size: 13px; font-weight: 600; margin-bottom: 10px; cursor: pointer; text-overflow: ellipsis; overflow: hidden; white-space: nowrap; }
        
        .btn-group { display: flex; gap: 10px; margin-top: 15px; }
        .btn { flex: 1; padding: 12px; border-radius: 12px; border: none; font-weight: 600; font-size: 14px; cursor: pointer; text-align: center; text-decoration: none; }
        .btn-deploy { background: #6d28d9; color: #ffffff; }
        .btn-stop { background: #37306b; color: #d8b4fe; }
        .btn-start { background: #10b981; color: #ffffff; }
        .btn-delete { background: #ef4444; color: #ffffff; padding: 6px 10px; font-size: 12px; border-radius: 8px; }

        .console-box { background: #0c0a1d; border-radius: 12px; padding: 12px; font-family: monospace; font-size: 12px; color: #4ade80; min-height: 90px; max-height: 130px; overflow-y: auto; white-space: pre-wrap; border: 1px solid #231f42; }
        
        .bot-row { background: #25214d; padding: 12px; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
    </style>
</head>
<body>

<div class="container">
    <div class="top-bar">
        <div class="icon-circle">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg>
        </div>
        <div style="background: #2d2657; padding: 8px; border-radius: 50%; color: #d8b4fe; cursor: pointer;" onclick="location.reload()">➔</div>
    </div>

    <div class="user-section">
        <h3>Hello,</h3>
        <h1>AKASH DANGEOWNER</h1>
        <p>akashdangerowner@gmail.com</p>
    </div>

    <!-- Upload Form with 2 separate file selectors -->
    <div class="card">
        <div class="card-title">📁 Upload Files</div>
        <form action="/upload" method="POST" enctype="multipart/form-data">
            
            <label class="file-select-btn" id="py-label">
                Select main.py
                <input type="file" name="main_file" accept=".py" required style="display:none;" onchange="document.getElementById('py-label').innerText = 'Selected: ' + this.files[0].name">
            </label>

            <label class="file-select-btn" id="req-label">
                Select requirements.txt
                <input type="file" name="req_file" accept=".txt" required style="display:none;" onchange="document.getElementById('req-label').innerText = 'Selected: ' + this.files[0].name">
            </label>
            
            <div class="btn-group">
                <button type="submit" class="btn btn-deploy">Deploy / Run</button>
            </div>
        </form>
    </div>

    <!-- Console Section -->
    <div class="card">
        <div class="card-title" style="justify-content: space-between;">
            <span>Console</span>
            <span style="font-size: 12px; color: #a78bfa; cursor: pointer;" onclick="location.reload()">🔄 Clear</span>
        </div>
        <div class="console-box">{{ logs }}</div>
    </div>

    <!-- Managed Bot List -->
    {% if bots %}
    <div class="card">
        <div class="card-title">🚀 Managed Bots</div>
        {% for bot in bots %}
        <div class="bot-row">
            <div>
                <div style="font-weight: 600; font-size: 14px;">{{ bot['filename'] }}</div>
                <div style="font-size: 11px; color: {% if bot['status'] == 'Running' %}#10b981{% else %}#ef4444{% endif %};">
                    Status: {{ bot['status'] }}
                </div>
            </div>
            <div style="display: flex; gap: 6px; align-items: center;">
                {% if bot['status'] == 'Running' %}
                    <a href="/stop/{{ bot['id'] }}" class="btn btn-stop" style="padding: 6px 12px; font-size: 12px;">Stop</a>
                {% else %}
                    <a href="/start/{{ bot['id'] }}" class="btn btn-start" style="padding: 6px 12px; font-size: 12px;">Start</a>
                {% endif %}
                <a href="/delete/{{ bot['id'] }}" class="btn-delete" onclick="return confirm('Delete bot?')">X</a>
            </div>
        </div>
        {% endfor %}
    </div>
    {% endif %}
</div>

</body>
</html>
"""

@app.route('/')
def index():
    global console_logs
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bots ORDER BY id DESC')
    bots = cursor.fetchall()
    conn.close()
    return render_template_string(HTML_TEMPLATE, bots=bots, logs=console_logs)

@app.route('/upload', methods=['POST'])
def upload():
    global console_logs
    main_file = request.files.get('main_file')
    req_file = request.files.get('req_file')

    if main_file and main_file.filename:
        main_filename = main_file.filename
        main_path = os.path.join(UPLOAD_FOLDER, main_filename)
        main_file.save(main_path)
        console_logs = f"Uploaded: {main_filename}\n"

    if req_file and req_file.filename:
        req_path = os.path.join(UPLOAD_FOLDER, 'requirements.txt')
        req_file.save(req_path)
        console_logs += "Installing requirements.txt...\n"
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_path], capture_output=True, text=True)
            console_logs += "Packages Installed Successfully!\n"
        except Exception as e:
            console_logs += f"Install Error: {str(e)}\n"

    if main_file and main_file.filename:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO bots (bot_name, filename, status) VALUES (?, ?, ?)',
                       ("Telegram Bot", main_file.filename, 'Stopped'))
        conn.commit()
        conn.close()
        console_logs += "Ready! Click Start on your bot below."

    return redirect(url_for('index'))

@app.route('/start/<int:bot_id>')
def start_bot(bot_id):
    global console_logs
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT filename FROM bots WHERE id = ?', (bot_id,))
    bot = cursor.fetchone()

    if bot:
        filepath = os.path.join(UPLOAD_FOLDER, bot['filename'])
        if bot_id in active_processes and active_processes[bot_id].poll() is None:
            console_logs = "Bot is already running."
        else:
            proc = subprocess.Popen([sys.executable, filepath], cwd=UPLOAD_FOLDER)
            active_processes[bot_id] = proc
            cursor.execute('UPDATE bots SET status = "Running" WHERE id = ?', (bot_id,))
            conn.commit()
            console_logs = f"Bot {bot['filename']} started successfully!"

    conn.close()
    return redirect(url_for('index'))

@app.route('/stop/<int:bot_id>')
def stop_bot(bot_id):
    global console_logs
    if bot_id in active_processes:
        proc = active_processes[bot_id]
        proc.terminate()
        del active_processes[bot_id]

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE bots SET status = "Stopped" WHERE id = ?', (bot_id,))
    conn.commit()
    conn.close()

    console_logs = "Bot stopped."
    return redirect(url_for('index'))

@app.route('/delete/<int:bot_id>')
def delete_bot(bot_id):
    stop_bot(bot_id)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT filename FROM bots WHERE id = ?', (bot_id,))
    bot = cursor.fetchone()

    if bot:
        filepath = os.path.join(UPLOAD_FOLDER, bot['filename'])
        if os.path.exists(filepath):
            os.remove(filepath)
        cursor.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
        conn.commit()

    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
