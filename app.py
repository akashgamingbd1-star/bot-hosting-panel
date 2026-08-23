import os
import sys
import sqlite3
import subprocess
import time
import shutil
import zipfile
from io import BytesIO
from flask import Flask, render_template_string, request, redirect, url_for, send_file, flash

app = Flask(__name__)
app.secret_key = 'multi_bot_hosting_platform_2026_premium'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'user_bots')
DATABASE = os.path.join(BASE_DIR, 'platform.db')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Active processes dictionary: {bot_id: {'process': proc_obj, 'start_time': timestamp, 'log_file': log_file_path}}
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
            folder_path TEXT NOT NULL,
            main_file TEXT NOT NULL,
            status TEXT DEFAULT 'Stopped',
            logs TEXT DEFAULT 'Ready to run...',
            start_timestamp REAL DEFAULT 0
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
    <title>Multi-Bot Telegram Hosting Panel</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', 'Segoe UI', sans-serif; }
        body { background: radial-gradient(circle at top left, #1e1b4b, #0f172a); color: #f8fafc; min-height: 100vh; padding: 25px 15px; }
        
        .container { max-width: 550px; margin: 0 auto; }
        
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; }
        .logo-icon { background: linear-gradient(135deg, #a855f7, #6366f1); color: #fff; width: 48px; height: 48px; border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 22px; box-shadow: 0 4px 15px rgba(168, 85, 247, 0.4); }
        
        .premium-banner { background: linear-gradient(135deg, rgba(124, 58, 237, 0.4), rgba(79, 70, 229, 0.4)); backdrop-filter: blur(12px); border-radius: 20px; padding: 22px; margin-bottom: 22px; text-align: center; border: 1px solid rgba(255,255,255,0.15); box-shadow: 0 10px 30px rgba(0,0,0,0.4); }
        .premium-banner h2 { font-size: 20px; font-weight: 800; letter-spacing: 0.5px; color: #fff; margin-bottom: 6px; display: flex; align-items: center; justify-content: center; gap: 10px; }
        .premium-banner p { font-size: 13px; color: #c7d2fe; }

        .card { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(16px); border-radius: 20px; padding: 22px; margin-bottom: 22px; border: 1px solid rgba(255, 255, 255, 0.1); box-shadow: 0 8px 25px rgba(0,0,0,0.3); }
        .card-title { font-size: 17px; font-weight: 700; margin-bottom: 18px; display: flex; align-items: center; gap: 10px; color: #f1f5f9; }
        
        .input-box { width: 100%; background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 12px; padding: 12px 15px; color: white; margin-bottom: 14px; outline: none; font-size: 14px; transition: all 0.3s; }
        .input-box:focus { border-color: #818cf8; box-shadow: 0 0 10px rgba(129, 140, 248, 0.3); }

        .file-input-wrapper { margin-bottom: 12px; }
        .btn-file { width: 100%; padding: 12px; background: rgba(255, 255, 255, 0.05); border: 1px dashed rgba(255, 255, 255, 0.25); border-radius: 12px; color: #cbd5e1; text-align: center; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 10px; font-size: 13px; transition: 0.3s; }
        .btn-file:hover { background: rgba(255, 255, 255, 0.1); border-color: #a855f7; color: #fff; }

        .btn-deploy { width: 100%; padding: 13px; background: linear-gradient(135deg, #6366f1, #a855f7); border: none; border-radius: 12px; font-weight: 700; cursor: pointer; font-size: 15px; color: white; margin-top: 5px; box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4); transition: 0.3s; }
        .btn-deploy:hover { opacity: 0.9; transform: translateY(-1px); }

        .bot-card { background: rgba(15, 23, 42, 0.8); border-radius: 16px; padding: 18px; margin-bottom: 18px; border: 1px solid rgba(255, 255, 255, 0.08); }
        .bot-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .bot-title { font-size: 16px; font-weight: 700; color: #ffffff; }
        
        .status-badge { font-size: 11px; padding: 4px 10px; border-radius: 20px; font-weight: 700; letter-spacing: 0.5px; }
        .status-running { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(52, 211, 153, 0.3); }
        .status-stopped { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(248, 113, 113, 0.3); }

        .bot-actions { display: grid; grid-template-columns: repeat(auto-fit, minmax(75px, 1fr)); gap: 6px; margin-top: 14px; }
        .btn-act { padding: 9px 5px; border-radius: 10px; border: none; font-weight: 600; font-size: 11px; cursor: pointer; text-align: center; text-decoration: none; display: flex; align-items: center; justify-content: center; gap: 4px; color: white; transition: 0.2s; }
        .btn-act:hover { opacity: 0.85; transform: scale(0.98); }
        .btn-run { background: #10b981; }
        .btn-stop-bot { background: #f59e0b; }
        .btn-code-edit { background: #8b5cf6; }
        .btn-data { background: #06b6d4; }
        .btn-backup { background: #3b82f6; }
        .btn-del { background: #ef4444; }

        .console-box { background: #020617; border-radius: 10px; padding: 10px 12px; font-family: 'Fira Code', monospace; font-size: 11px; color: #4ade80; max-height: 120px; overflow-y: auto; margin-top: 10px; border: 1px solid rgba(255,255,255,0.05); white-space: pre-wrap; word-break: break-all; }

        .restore-box { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 12px; margin-top: 12px; }
    </style>
</head>
<body>

<div class="container">
    <div class="header">
        <div class="logo">
            <div class="logo-icon"><i class="fa-solid fa-paper-plane"></i></div>
        </div>
        <i class="fa-solid fa-rotate-right" style="font-size: 20px; cursor: pointer; color: #94a3b8;" onclick="location.reload()"></i>
    </div>

    <div class="premium-banner">
        <h2><i class="fa-solid fa-crown" style="color:#f59e0b;"></i> PREMIUM HOSTING PANEL</h2>
        <p>Manage, Backup & Edit Your Python Bots Live</p>
    </div>

    <!-- Upload Bot -->
    <div class="card">
        <div class="card-title"><i class="fa-solid fa-cloud-arrow-up" style="color:#a855f7;"></i> Upload New Bot</div>
        
        <form action="/upload" method="POST" enctype="multipart/form-data">
            <input type="text" name="bot_name" class="input-box" placeholder="বটের নাম লিখুন (যেমন: Bot One)" required>
            
            <div class="file-input-wrapper">
                <label for="bot_file" class="btn-file" id="botLabel"><i class="fa-solid fa-code"></i> Choose main.py</label>
                <input type="file" id="bot_file" name="bot_file" accept=".py" required style="display:none;" onchange="updateLabel(this, 'botLabel', 'Choose main.py')">
            </div>

            <div class="file-input-wrapper">
                <label for="req_file" class="btn-file" id="reqLabel"><i class="fa-solid fa-list-check"></i> Choose requirements.txt (Optional)</label>
                <input type="file" id="req_file" name="req_file" accept=".txt" style="display:none;" onchange="updateLabel(this, 'reqLabel', 'Choose requirements.txt (Optional)')">
            </div>

            <button type="submit" class="btn-deploy">Save & Deploy Bot</button>
        </form>

        <!-- Restore Section -->
        <div class="restore-box">
            <div style="font-size: 13px; font-weight: 600; margin-bottom: 8px; color: #38bdf8;"><i class="fa-solid fa-rotate-left"></i> Restore Bot from Backup (.zip)</div>
            <form action="/restore" method="POST" enctype="multipart/form-data" style="display: flex; gap: 8px;">
                <input type="file" name="backup_zip" accept=".zip" required style="font-size: 11px; color: #94a3b8; width: 70%;">
                <button type="submit" style="padding: 6px 12px; background: #0284c7; border: none; border-radius: 8px; color: white; font-weight: bold; font-size: 11px; cursor: pointer;">Restore</button>
            </form>
        </div>
    </div>

    <!-- Managed Bots -->
    <div class="card">
        <div class="card-title"><i class="fa-solid fa-server" style="color:#38bdf8;"></i> Managed Bots List</div>
        
        {% if bots %}
            {% for bot in bots %}
            <div class="bot-card">
                <div class="bot-header">
                    <div class="bot-title"><i class="fa-solid fa-robot" style="color:#818cf8;"></i> {{ bot['bot_name'] }}</div>
                    {% if bot['status'] == 'Running' %}
                        <span class="status-badge status-running">● RUNNING</span>
                    {% else %}
                        <span class="status-badge status-stopped">○ STOPPED</span>
                    {% endif %}
                </div>

                <div style="font-size: 12px; color: #94a3b8;">Main File: {{ bot['main_file'] }}</div>
                
                {% if bot['status'] == 'Running' and bot['uptime_str'] %}
                    <div style="font-size: 11px; color: #34d399; margin-top: 4px;"><i class="fa-solid fa-clock"></i> Uptime: {{ bot['uptime_str'] }}</div>
                {% endif %}
                
                <div class="console-box">{{ bot['logs'] }}</div>

                <div class="bot-actions">
                    {% if bot['status'] == 'Running' %}
                        <a href="/stop/{{ bot['id'] }}" class="btn-act btn-stop-bot"><i class="fa-solid fa-pause"></i> Stop</a>
                    {% else %}
                        <a href="/start/{{ bot['id'] }}" class="btn-act btn-run"><i class="fa-solid fa-play"></i> Run</a>
                    {% endif %}
                    <a href="/edit_code/{{ bot['id'] }}" class="btn-act btn-code-edit"><i class="fa-solid fa-code"></i> Code</a>
                    <a href="/user_data/{{ bot['id'] }}" class="btn-act btn-data"><i class="fa-solid fa-database"></i> Data</a>
                    <a href="/backup/{{ bot['id'] }}" class="btn-act btn-backup"><i class="fa-solid fa-download"></i> Backup</a>
                    <a href="/delete/{{ bot['id'] }}" class="btn-act btn-del" onclick="return confirm('এই বটটি সম্পূর্ণ ডিলিট করতে চান?')"><i class="fa-solid fa-trash"></i> Del</a>
                </div>
            </div>
            {% endfor %}
        {% else %}
            <div style="text-align: center; color: #64748b; font-size: 13px; padding: 20px;">
                কোনো বট আপলোড করা হয়নি। ওপরের ফর্ম ব্যবহার করে বট যোগ করুন!
            </div>
        {% endif %}
    </div>
</div>

<script>
function updateLabel(input, labelId, defaultText) {
    const label = document.getElementById(labelId);
    if (input.files.length > 0) {
        label.innerText = "Selected: " + input.files[0].name;
    } else {
        label.innerText = defaultText;
    }
}
</script>

</body>
</html>
"""
CODE_EDIT_TEMPLATE = """
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Editor - {{ bot['bot_name'] }}</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Fira Code', 'Courier New', monospace; }
        body { background: #0b0f19; color: white; min-height: 100vh; display: flex; flex-direction: column; }
        
        .editor-header { display: flex; justify-content: space-between; align-items: center; background: #111827; padding: 12px 20px; border-bottom: 1px solid rgba(255,255,255,0.1); font-family: sans-serif; }
        .editor-title { font-size: 15px; font-weight: bold; color: #f3e8ff; display: flex; align-items: center; gap: 8px; }
        
        .action-btns { display: flex; gap: 10px; }
        .btn-top { padding: 8px 14px; border-radius: 8px; border: none; font-weight: bold; font-size: 12px; cursor: pointer; text-decoration: none; color: white; display: flex; align-items: center; gap: 6px; }
        .btn-back { background: #374151; }
        .btn-save { background: #10b981; }

        .editor-container { display: flex; flex: 1; background: #030712; margin: 12px; border-radius: 12px; overflow: hidden; border: 1px solid rgba(255, 255, 255, 0.1); }
        .line-numbers { background: #0b0f19; color: #475569; padding: 15px 10px; text-align: right; font-size: 13px; line-height: 1.5; user-select: none; border-right: 1px solid rgba(255, 255, 255, 0.05); min-width: 45px; }
        .code-area { width: 100%; flex: 1; background: transparent; border: none; padding: 15px; color: #38bdf8; font-size: 13px; line-height: 1.5; resize: none; outline: none; white-space: pre; overflow-x: auto; tab-size: 4; }
    </style>
</head>
<body>
    <form method="POST" style="display: flex; flex-direction: column; flex: 1;">
        <div class="editor-header">
            <div class="editor-title"><i class="fa-solid fa-code" style="color:#a855f7;"></i> Editing: {{ filename }}</div>
            <div class="action-btns">
                <button type="submit" class="btn-top btn-save"><i class="fa-solid fa-floppy-disk"></i> Save Code</button>
                <a href="/" class="btn-top btn-back"><i class="fa-solid fa-arrow-left"></i> Back</a>
            </div>
        </div>

        <div class="editor-container">
            <div id="lineNumbers" class="line-numbers">1</div>
            <textarea name="bot_code" id="codeArea" class="code-area" required spellcheck="false" oninput="updateLines()" onscroll="syncScroll()">{{ code_content }}</textarea>
        </div>
    </form>

    <script>
        const codeArea = document.getElementById('codeArea');
        const lineNumbers = document.getElementById('lineNumbers');

        function updateLines() {
            const lines = codeArea.value.split('\\n').length;
            let numbersStr = '';
            for (let i = 1; i <= lines; i++) { numbersStr += i + '<br>'; }
            lineNumbers.innerHTML = numbersStr;
        }

        function syncScroll() { lineNumbers.scrollTop = codeArea.scrollTop; }
        codeArea.addEventListener('scroll', syncScroll);
        window.onload = updateLines;
    </script>
</body>
</html>
"""

USER_DATA_TEMPLATE = """
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>User Data & File Manager</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background: #0f172a; color: white; padding: 20px; }
        .container { max-width: 700px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 12px; }
        .file-list { background: #1e293b; border-radius: 12px; overflow: hidden; border: 1px solid rgba(255,255,255,0.08); }
        .file-item { display: flex; justify-content: space-between; align-items: center; padding: 14px 18px; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .file-item:last-child { border-bottom: none; }
        .file-name { font-size: 14px; font-weight: 500; display: flex; align-items: center; gap: 10px; color: #e2e8f0; }
        .btn-view { padding: 6px 14px; background: #3b82f6; border-radius: 8px; color: white; text-decoration: none; font-size: 12px; font-weight: 600; }
        .btn-back { padding: 8px 16px; background: #475569; border-radius: 8px; color: white; text-decoration: none; font-size: 13px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h3><i class="fa-solid fa-folder-open" style="color:#06b6d4;"></i> Files & User Data ({{ bot['bot_name'] }})</h3>
            <a href="/" class="btn-back"><i class="fa-solid fa-arrow-left"></i> Back</a>
        </div>

        <div class="file-list">
            {% if files %}
                {% for file in files %}
                <div class="file-item">
                    <div class="file-name">
                        <i class="fa-solid fa-file-code" style="color:#a855f7;"></i> {{ file['name'] }}
                        <span style="font-size: 11px; color: #64748b;">({{ file['size'] }} KB)</span>
                    </div>
                    <a href="/edit_file/{{ bot['id'] }}?filename={{ file['name'] }}" class="btn-view">Edit / View Data</a>
                </div>
                {% endfor %}
            {% else %}
                <div style="padding: 20px; text-align: center; color: #64748b;">কোনো ফাইল বা ডাটাবেস খুঁজে পাওয়া যায়নি।</div>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""

def format_uptime(start_timestamp):
    if not start_timestamp:
        return ""
    diff = int(time.time() - start_timestamp)
    days = diff // 86400
    hours = (diff % 86400) // 3600
    minutes = (diff % 3600) // 60
    seconds = diff % 60

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m {seconds}s")
    return " ".join(parts)

@app.route('/')
def index():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bots ORDER BY id DESC')
    db_bots = cursor.fetchall()

    bots = []
    for bot in db_bots:
        bot_dict = dict(bot)
        bot_id = bot_dict['id']
        bot_dir = bot_dict['folder_path']
        log_file_path = os.path.join(bot_dir, 'bot.log')

        if bot_dict['status'] == 'Running':
            is_alive = False
            if bot_id in active_processes:
                if active_processes[bot_id]['process'].poll() is None:
                    is_alive = True

            if not is_alive:
                crash_log = "Bot stopped unexpectedly."
                if os.path.exists(log_file_path):
                    try:
                        with open(log_file_path, 'r', encoding='utf-8') as lf:
                            logs_content = lf.read().strip()
                            if logs_content:
                                crash_log = logs_content[-1000:]
                    except Exception:
                        pass

                cursor.execute('UPDATE bots SET status = "Stopped", logs = ?, start_timestamp = 0 WHERE id = ?', (crash_log, bot_id))
                conn.commit()
                bot_dict['status'] = 'Stopped'
                bot_dict['logs'] = crash_log
                bot_dict['uptime_str'] = ''
            else:
                start_ts = active_processes[bot_id]['start_time']
                bot_dict['uptime_str'] = format_uptime(start_ts)
                if os.path.exists(log_file_path):
                    try:
                        with open(log_file_path, 'r', encoding='utf-8') as lf:
                            logs_content = lf.read().strip()
                            if logs_content:
                                bot_dict['logs'] = logs_content[-1000:]
                    except Exception:
                        pass
        else:
            bot_dict['uptime_str'] = ''

        bots.append(bot_dict)

    conn.close()
    return render_template_string(HTML_TEMPLATE, bots=bots)

@app.route('/upload', methods=['POST'])
def upload():
    bot_name = request.form.get('bot_name')
    bot_file = request.files.get('bot_file')
    req_file = request.files.get('req_file')

    if not bot_file or not bot_file.filename:
        return redirect(url_for('index'))

    folder_name = f"bot_{int(time.time())}_{bot_name.replace(' ', '_')}"
    bot_dir = os.path.join(UPLOAD_FOLDER, folder_name)
    os.makedirs(bot_dir, exist_ok=True)

    main_filename = bot_file.filename
    main_path = os.path.join(bot_dir, main_filename)
    bot_file.save(main_path)

    log_msg = "Files uploaded successfully.\n"

    if req_file and req_file.filename:
        req_path = os.path.join(bot_dir, 'requirements.txt')
        req_file.save(req_path)
        try:
            log_msg += "Installing requirements...\n"
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_path], capture_output=True, text=True)
            log_msg += "Packages installed successfully!\n"
        except Exception as e:
            log_msg += f"Install error: {str(e)}\n"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO bots (bot_name, folder_path, main_file, status, logs, start_timestamp) VALUES (?, ?, ?, ?, ?, ?)',
                   (bot_name, bot_dir, main_filename, 'Stopped', log_msg + "Ready to Run.", 0))
    conn.commit()
    conn.close()

    return redirect(url_for('index'))

@app.route('/start/<int:bot_id>')
def start_bot(bot_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bots WHERE id = ?', (bot_id,))
    bot = cursor.fetchone()

    if bot:
        bot_dir = bot['folder_path']
        main_file = bot['main_file']
        log_file_path = os.path.join(bot_dir, 'bot.log')

        if bot_id in active_processes and active_processes[bot_id]['process'].poll() is None:
            active_processes[bot_id]['process'].terminate()

        log_file = open(log_file_path, 'w', encoding='utf-8')
        proc = subprocess.Popen([sys.executable, "-u", main_file], cwd=bot_dir, stdout=log_file, stderr=subprocess.STDOUT)
        
        current_time = time.time()
        active_processes[bot_id] = {'process': proc, 'start_time': current_time, 'log_file': log_file}

        cursor.execute('UPDATE bots SET status = "Running", logs = "Bot started live...", start_timestamp = ? WHERE id = ?', (current_time, bot_id))
        conn.commit()

    conn.close()
    return redirect(url_for('index'))

@app.route('/stop/<int:bot_id>')
def stop_bot(bot_id):
    if bot_id in active_processes:
        proc_info = active_processes[bot_id]
        proc_info['process'].terminate()
        try:
            proc_info['log_file'].close()
        except Exception:
            pass
        del active_processes[bot_id]

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE bots SET status = "Stopped", logs = "Bot stopped by user.", start_timestamp = 0 WHERE id = ?', (bot_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('index'))

@app.route('/edit_code/<int:bot_id>', methods=['GET', 'POST'])
def edit_code(bot_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bots WHERE id = ?', (bot_id,))
    bot = cursor.fetchone()
    conn.close()

    if not bot:
        return redirect(url_for('index'))

    file_path = os.path.join(bot['folder_path'], bot['main_file'])

    if request.method == 'POST':
        new_code = request.form.get('bot_code')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_code)

        if bot['status'] == 'Running':
            stop_bot(bot_id)

        return redirect(url_for('index'))

    code_content = ""
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            code_content = f.read()

    return render_template_string(CODE_EDIT_TEMPLATE, bot=bot, code_content=code_content, filename=bot['main_file'])

@app.route('/user_data/<int:bot_id>')
def user_data(bot_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bots WHERE id = ?', (bot_id,))
    bot = cursor.fetchone()
    conn.close()

    if not bot:
        return redirect(url_for('index'))

    bot_dir = bot['folder_path']
    files_list = []

    if os.path.exists(bot_dir):
        for root, _, files in os.walk(bot_dir):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), bot_dir)
                full_path = os.path.join(root, file)
                size_kb = round(os.path.getsize(full_path) / 1024, 2)
                files_list.append({'name': rel_path, 'size': size_kb})

    return render_template_string(USER_DATA_TEMPLATE, bot=bot, files=files_list)

@app.route('/edit_file/<int:bot_id>', methods=['GET', 'POST'])
def edit_file(bot_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bots WHERE id = ?', (bot_id,))
    bot = cursor.fetchone()
    conn.close()

    filename = request.args.get('filename', bot['main_file'])
    file_path = os.path.join(bot['folder_path'], filename)

    if request.method == 'POST':
        new_code = request.form.get('bot_code')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_code)
        return redirect(url_for('user_data', bot_id=bot_id))

    code_content = ""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code_content = f.read()
        except Exception:
            code_content = "[Binary/Database File - Cannot edit directly as text]"

    return render_template_string(CODE_EDIT_TEMPLATE, bot=bot, code_content=code_content, filename=filename)

@app.route('/backup/<int:bot_id>')
def backup_bot(bot_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bots WHERE id = ?', (bot_id,))
    bot = cursor.fetchone()
    conn.close()

    if not bot or not os.path.exists(bot['folder_path']):
        return redirect(url_for('index'))

    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(bot['folder_path']):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, bot['folder_path'])
                zf.write(full_path, rel_path)

    memory_file.seek(0)
    zip_name = f"{bot['bot_name']}_backup.zip".replace(' ', '_')
    return send_file(memory_file, download_name=zip_name, as_attachment=True)

@app.route('/restore', methods=['POST'])
def restore_bot():
    backup_file = request.files.get('backup_zip')
    if not backup_file or not backup_file.filename.endswith('.zip'):
        return redirect(url_for('index'))

    bot_name = os.path.splitext(backup_file.filename)[0].replace('_backup', '')
    folder_name = f"bot_{int(time.time())}_{bot_name}"
    bot_dir = os.path.join(UPLOAD_FOLDER, folder_name)
    os.makedirs(bot_dir, exist_ok=True)

    with zipfile.ZipFile(backup_file, 'r') as zf:
        zf.extractall(bot_dir)

    main_file = "main.py"
    files_in_dir = os.listdir(bot_dir)
    py_files = [f for f in files_in_dir if f.endswith('.py')]
    if py_files:
        main_file = py_files[0]

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO bots (bot_name, folder_path, main_file, status, logs, start_timestamp) VALUES (?, ?, ?, ?, ?, ?)',
                   (bot_name.replace('_', ' '), bot_dir, main_file, 'Stopped', 'Restored from Backup zip.', 0))
    conn.commit()
    conn.close()

    return redirect(url_for('index'))

@app.route('/delete/<int:bot_id>')
def delete_bot(bot_id):
    stop_bot(bot_id)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT folder_path FROM bots WHERE id = ?', (bot_id,))
    bot = cursor.fetchone()

    if bot:
        bot_dir = bot['folder_path']
        if os.path.exists(bot_dir):
            shutil.rmtree(bot_dir, ignore_errors=True)

        cursor.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
        conn.commit()

    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
