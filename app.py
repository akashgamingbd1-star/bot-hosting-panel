import os
import sys
import sqlite3
import subprocess
from flask import Flask, render_template_string, request, redirect, url_for

app = Flask(__name__)
app.secret_key = 'cloud_bot_hosting_secret_key_2026'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'user_bots')
DATABASE = os.path.join(BASE_DIR, 'platform.db')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

active_processes = {}

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
    <title>Cloud Bot Hosting Platform - Pro Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0b0f19;
            --card-bg: #111827;
            --card-border: #1f2937;
            --accent: #6366f1;
            --accent-hover: #4f46e5;
            --text-main: #f9fafb;
            --text-muted: #9ca3af;
            --success: #10b981;
            --danger: #ef4444;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }
        body { background-color: var(--bg-dark); color: var(--text-main); min-height: 100vh; padding: 30px 20px; }
        .container { max-width: 1000px; margin: 0 auto; }

        header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 25px; border-bottom: 1px solid var(--card-border); margin-bottom: 30px; }
        .logo-title h1 { font-size: 24px; font-weight: 700; background: linear-gradient(135deg, #818cf8 0%, #c084fc 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .logo-title p { font-size: 13px; color: var(--text-muted); margin-top: 4px; }

        .badge-live { background: rgba(16, 185, 129, 0.1); color: var(--success); border: 1px solid rgba(16, 185, 129, 0.3); padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 600; display: flex; align-items: center; gap: 6px; }
        .pulse-dot { width: 8px; height: 8px; background-color: var(--success); border-radius: 50%; animation: pulse 1.5s infinite; }

        @keyframes pulse {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }

        .grid { display: grid; grid-template-columns: 1fr 2fr; gap: 25px; }
        @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }

        .card { background-color: var(--card-bg); border: 1px solid var(--card-border); border-radius: 16px; padding: 24px; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5); }
        .card-header { font-size: 16px; font-weight: 600; margin-bottom: 18px; color: var(--text-main); }

        .form-group { margin-bottom: 16px; }
        .form-group label { display: block; font-size: 12px; font-weight: 600; color: var(--text-muted); margin-bottom: 6px; text-transform: uppercase; }
        .form-group input[type="text"], .form-group input[type="file"] { width: 100%; padding: 12px; background: #1f2937; border: 1px solid #374151; border-radius: 8px; color: #fff; font-size: 14px; outline: none; }

        .btn { width: 100%; padding: 12px; background: var(--accent); color: white; border: none; border-radius: 8px; font-weight: 600; font-size: 14px; cursor: pointer; }
        .btn:hover { background: var(--accent-hover); }
        
        .btn-sm { width: auto; padding: 6px 12px; font-size: 12px; border-radius: 6px; text-decoration: none; display: inline-block; }
        .btn-start { background: rgba(16, 185, 129, 0.2); color: var(--success); border: 1px solid var(--success); }
        .btn-stop { background: rgba(239, 68, 68, 0.2); color: var(--danger); border: 1px solid var(--danger); }
        .btn-delete { background: rgba(156, 163, 175, 0.1); color: var(--text-muted); border: 1px solid var(--card-border); margin-left: 4px; }

        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th { text-align: left; padding: 12px; font-size: 12px; color: var(--text-muted); border-bottom: 1px solid var(--card-border); text-transform: uppercase; }
        td { padding: 14px 12px; font-size: 14px; border-bottom: 1px solid var(--card-border); }

        .status-pill { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
        .status-running { background: rgba(16, 185, 129, 0.15); color: var(--success); }
        .status-stopped { background: rgba(239, 68, 68, 0.15); color: var(--danger); }
    </style>
</head>
<body>

<div class="container">
    <header>
        <div class="logo-title">
            <h1>⚡ Cloud Bot Hosting Platform</h1>
            <p>24/7 Commercial Automated Telegram Bot Manager</p>
        </div>
        <div class="badge-live">
            <div class="pulse-dot"></div> Server Online
        </div>
    </header>

    <div class="grid">
        <div class="card">
            <div class="card-header">📦 Deploy New Bot</div>
            <form action="/upload" method="POST" enctype="multipart/form-data">
                <div class="form-group">
                    <label>Bot Display Name</label>
                    <input type="text" name="bot_name" placeholder="e.g. Store Support Bot" required>
                </div>
                <div class="form-group">
                    <label>Bot Script File (.py)</label>
                    <input type="file" name="bot_file" accept=".py" required>
                </div>
                <button type="submit" class="btn">Upload & Deploy</button>
            </form>
        </div>

        <div class="card">
            <div class="card-header">🚀 Managed Telegram Bots</div>
            {% if bots %}
            <table>
                <thead>
                    <tr>
                        <th>Bot Name</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for bot in bots %}
                    <tr>
                        <td>
                            <strong>{{ bot['bot_name'] }}</strong>
                            <div style="font-size: 11px; color: var(--text-muted);">{{ bot['filename'] }}</div>
                        </td>
                        <td>
                            {% if bot['status'] == 'Running' %}
                                <span class="status-pill status-running">● Active</span>
                            {% else %}
                                <span class="status-pill status-stopped">○ Offline</span>
                            {% endif %}
                        </td>
                        <td>
                            {% if bot['status'] == 'Running' %}
                                <a href="/stop/{{ bot['id'] }}" class="btn-sm btn-stop">Stop</a>
                            {% else %}
                                <a href="/start/{{ bot['id'] }}" class="btn-sm btn-start">Start</a>
                            {% endif %}
                            <a href="/delete/{{ bot['id'] }}" class="btn-sm btn-delete" onclick="return confirm('Delete this bot?')">Delete</a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <div style="text-align: center; padding: 40px; color: var(--text-muted);">
                No bots deployed yet. Upload your main.py file from the left panel to get started!
            </div>
            {% endif %}
        </div>
    </div>
</div>

</body>
</html>
"""

@app.route('/')
def index():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bots ORDER BY id DESC')
    bots = cursor.fetchall()
    conn.close()
    return render_template_string(HTML_TEMPLATE, bots=bots)

@app.route('/upload', methods=['POST'])
def upload():
    bot_name = request.form.get('bot_name')
    file = request.files.get('bot_file')

    if file and file.filename.endswith('.py'):
        filename = file.filename
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(save_path)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO bots (bot_name, filename, status) VALUES (?, ?, ?)',
                       (bot_name, filename, 'Stopped'))
        conn.commit()
        conn.close()

    return redirect(url_for('index'))

@app.route('/start/<int:bot_id>')
def start_bot(bot_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT filename FROM bots WHERE id = ?', (bot_id,))
    bot = cursor.fetchone()

    if bot:
        filepath = os.path.join(UPLOAD_FOLDER, bot['filename'])
        
        if bot_id in active_processes and active_processes[bot_id].poll() is None:
            pass
        else:
            proc = subprocess.Popen(["python", filepath], cwd=UPLOAD_FOLDER)
            active_processes[bot_id] = proc

            cursor.execute('UPDATE bots SET status = "Running" WHERE id = ?', (bot_id,))
            conn.commit()

    conn.close()
    return redirect(url_for('index'))

@app.route('/stop/<int:bot_id>')
def stop_bot(bot_id):
    if bot_id in active_processes:
        proc = active_processes[bot_id]
        proc.terminate()
        del active_processes[bot_id]

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE bots SET status = "Stopped" WHERE id = ?', (bot_id,))
    conn.commit()
    conn.close()

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
