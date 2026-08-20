import os
import sys
import sqlite3
import subprocess
import time
from flask import Flask, render_template_string, request, redirect, url_for

app = Flask(__name__)
app.secret_key = 'multi_bot_hosting_platform_2026'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'user_bots')
DATABASE = os.path.join(BASE_DIR, 'platform.db')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Active processes dictionary: {bot_id: {'process': proc_obj, 'start_time': timestamp}}
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
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        body { background: linear-gradient(135deg, #4a3b8d 0%, #2b1f5c 100%); color: white; min-height: 100vh; padding: 20px 15px; }
        
        .container { max-width: 500px; margin: 0 auto; }
        
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; }
        .logo-icon { background: white; color: #4a3b8d; width: 45px; height: 45px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 20px; }
        
        .profile-card { display: flex; align-items: center; gap: 15px; margin-bottom: 25px; }
        .avatar { width: 60px; height: 60px; border-radius: 50%; background: #ccc; }
        .user-info h2 { font-size: 20px; font-weight: 700; }
        .user-info p { color: #bcaaa4; font-size: 14px; }

        .card { background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-radius: 20px; padding: 20px; margin-bottom: 20px; border: 1px solid rgba(255, 255, 255, 0.15); }
        .card-title { font-size: 18px; margin-bottom: 15px; display: flex; align-items: center; gap: 10px; color: #f3e8ff; }
        
        .input-box { width: 100%; background: rgba(0, 0, 0, 0.2); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 10px; padding: 12px; color: white; margin-bottom: 12px; outline: none; font-size: 14px; }
        
        .file-input-wrapper { margin-bottom: 12px; }
        .btn-file { width: 100%; padding: 12px; background: rgba(255, 255, 255, 0.15); border: 1px dashed rgba(255, 255, 255, 0.4); border-radius: 12px; color: white; text-align: center; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 10px; font-size: 14px; }

        .btn-deploy { width: 100%; padding: 12px; background: #6d28d9; border: none; border-radius: 12px; font-weight: bold; cursor: pointer; font-size: 15px; color: white; margin-top: 5px; }
        .btn-deploy:hover { background: #5b21b6; }

        .bot-card { background: rgba(18, 11, 41, 0.7); border-radius: 15px; padding: 15px; margin-bottom: 15px; border: 1px solid rgba(255, 255, 255, 0.1); }
        .bot-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
        .bot-title { font-size: 16px; font-weight: bold; color: #ffffff; }
        
        .status-badge { font-size: 11px; padding: 4px 10px; border-radius: 20px; font-weight: bold; }
        .status-running { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #34d399; }
        .status-stopped { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #f87171; }

        .bot-actions { display: flex; gap: 6px; margin-top: 12px; }
        .btn-act { flex: 1; padding: 8px; border-radius: 8px; border: none; font-weight: bold; font-size: 12px; cursor: pointer; text-align: center; text-decoration: none; display: inline-block; }
        .btn-run { background: #10b981; color: white; }
        .btn-stop-bot { background: #f59e0b; color: white; }
        .btn-edit { background: #3b82f6; color: white; }
        .btn-del { background: #ef4444; color: white; flex: 0.5; }

        .console-box { background: #0c0a1d; border-radius: 8px; padding: 10px; font-family: monospace; font-size: 11px; color: #33ff77; max-height: 80px; overflow-y: auto; margin-top: 8px; white-space: pre-wrap; }
    </style>
</head>
<body>

<div class="container">
    <div class="header">
        <div class="logo">
            <div class="logo-icon"><i class="fa-solid fa-paper-plane"></i></div>
        </div>
        <i class="fa-solid fa-right-from-bracket" style="font-size: 20px; cursor: pointer;" onclick="location.reload()"></i>
    </div>

    <div class="profile-card">
        <div class="avatar" style="background-image: url('https://via.placeholder.com/60'); background-size: cover;"></div>
        <div class="user-info">
            <p>Hello,</p>
            <h2>AKASH DANGEOWNER</h2>
            <p>akashdangerowner@gmail.com</p>
        </div>
    </div>

    <!-- Upload Card -->
    <div class="card">
        <div class="card-title"><i class="fa-solid fa-cloud-arrow-up"></i> Upload New Bot</div>
        
        <form action="/upload" method="POST" enctype="multipart/form-data">
            <input type="text" name="bot_name" class="input-box" placeholder="বটের নাম লিখুন (যেমন: Bot One)" required>
            
            <div class="file-input-wrapper">
                <label for="bot_file" class="btn-file" id="botLabel"><i class="fa-solid fa-code"></i> Choose main.py</label>
                <input type="file" id="bot_file" name="bot_file" accept=".py" required style="display:none;" onchange="updateLabel(this, 'botLabel', 'Choose main.py')">
            </div>

            <div class="file-input-wrapper">
                <label for="req_file" class="btn-file" id="reqLabel"><i class="fa-solid fa-list-check"></i> Choose requirements.txt</label>
                <input type="file" id="req_file" name="req_file" accept=".txt" required style="display:none;" onchange="updateLabel(this, 'reqLabel', 'Choose requirements.txt')">
            </div>

            <button type="submit" class="btn-deploy">Save & Deploy Bot</button>
        </form>
    </div>

    <!-- Managed Bots List -->
    <div class="card">
        <div class="card-title"><i class="fa-solid fa-server"></i> Managed Bots List</div>
        
        {% if bots %}
            {% for bot in bots %}
            <div class="bot-card">
                <div class="bot-header">
                    <div class="bot-title"><i class="fa-solid fa-robot"></i> {{ bot['bot_name'] }}</div>
                    {% if bot['status'] == 'Running' %}
                        <span class="status-badge status-running">● RUNNING</span>
                    {% else %}
                        <span class="status-badge status-stopped">○ STOPPED</span>
                    {% endif %}
                </div>

                <div style="font-size: 12px; color: #bcaaa4;">File: {{ bot['main_file'] }}</div>
                
                {% if bot['status'] == 'Running' and bot['uptime_str'] %}
                    <div style="font-size: 11px; color: #34d399; margin-top: 4px;"><i class="fa-solid fa-clock"></i> Uptime: {{ bot['uptime_str'] }}</div>
                {% endif %}
                
                <div class="console-box">{{ bot['logs'] }}</div>

                <div class="bot-actions">
                    {% if bot['status'] == 'Running' %}
                        <a href="/stop/{{ bot['id'] }}" class="btn-act btn-stop-bot">Stop</a>
                    {% else %}
                        <a href="/start/{{ bot['id'] }}" class="btn-act btn-run">Run</a>
                    {% endif %}
                    <a href="/edit/{{ bot['id'] }}" class="btn-act btn-edit">Edit</a>
                    <a href="/delete/{{ bot['id'] }}" class="btn-act btn-del" onclick="return confirm('এই বটটি ডিলিট করতে চান?')">Delete</a>
                </div>
            </div>
            {% endfor %}
        {% else %}
            <div style="text-align: center; color: #bcaaa4; font-size: 13px; padding: 15px;">
                কোনো বট আপলোড করা হয়নি। ওপরে ফর্ম পূরণ করে বট যোগ করুন!
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

EDIT_TEMPLATE = """
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Edit Bot - Hosting Panel</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', sans-serif; }
        body { background: linear-gradient(135deg, #4a3b8d 0%, #2b1f5c 100%); color: white; min-height: 100vh; padding: 20px; display: flex; align-items: center; justify-content: center; }
        .card { background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-radius: 20px; padding: 25px; width: 100%; max-width: 400px; border: 1px solid rgba(255, 255, 255, 0.15); }
        .input-box { width: 100%; background: rgba(0, 0, 0, 0.2); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 10px; padding: 12px; color: white; margin-bottom: 15px; outline: none; font-size: 14px; }
        .btn-save { width: 100%; padding: 12px; background: #10b981; border: none; border-radius: 12px; font-weight: bold; cursor: pointer; color: white; font-size: 15px; }
        .back-link { display: block; text-align: center; margin-top: 15px; color: #f3e8ff; text-decoration: none; font-size: 13px; }
    </style>
</head>
<body>
    <div class="card">
        <h3 style="margin-bottom: 20px;"><i class="fa-solid fa-pen-to-square"></i> Edit Bot Details</h3>
        <form method="POST">
            <label style="font-size: 13px; color: #bcaaa4;">Bot Name:</label>
            <input type="text" name="bot_name" class="input-box" value="{{ bot['bot_name'] }}" required style="margin-top: 5px;">
            
            <label style="font-size: 13px; color: #bcaaa4;">Main File Name (.py):</label>
            <input type="text" name="main_file" class="input-box" value="{{ bot['main_file'] }}" required style="margin-top: 5px;">
            
            <button type="submit" class="btn-save">Update Database</button>
        </form>
        <a href="/" class="back-link"><i class="fa-solid fa-arrow-left"></i> Back to Dashboard</a>
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
        if bot_dict['status'] == 'Running' and bot_dict['id'] in active_processes:
            if active_processes[bot_dict['id']]['process'].poll() is not None:
                cursor.execute('UPDATE bots SET status = "Stopped", start_timestamp = 0 WHERE id = ?', (bot_dict['id'],))
                conn.commit()
                bot_dict['status'] = 'Stopped'
                bot_dict['uptime_str'] = ''
            else:
                start_ts = active_processes[bot_dict['id']]['start_time']
                bot_dict['uptime_str'] = format_uptime(start_ts)
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

        if bot_id in active_processes and active_processes[bot_id]['process'].poll() is None:
            pass
        else:
            proc = subprocess.Popen([sys.executable, main_file], cwd=bot_dir)
            current_time = time.time()
            active_processes[bot_id] = {'process': proc, 'start_time': current_time}

            cursor.execute('UPDATE bots SET status = "Running", logs = "Bot is running live!", start_timestamp = ? WHERE id = ?', (current_time, bot_id))
            conn.commit()

    conn.close()
    return redirect(url_for('index'))

@app.route('/stop/<int:bot_id>')
def stop_bot(bot_id):
    if bot_id in active_processes:
        active_processes[bot_id]['process'].terminate()
        del active_processes[bot_id]

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE bots SET status = "Stopped", logs = "Bot stopped by user.", start_timestamp = 0 WHERE id = ?', (bot_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('index'))

@app.route('/edit/<int:bot_id>', methods=['GET', 'POST'])
def edit_bot(bot_id):
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        new_name = request.form.get('bot_name')
        new_file = request.form.get('main_file')
        cursor.execute('UPDATE bots SET bot_name = ?, main_file = ? WHERE id = ?', (new_name, new_file, bot_id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
        
    cursor.execute('SELECT * FROM bots WHERE id = ?', (bot_id,))
    bot = cursor.fetchone()
    conn.close()
    
    if not bot:
        return redirect(url_for('index'))
        
    return render_template_string(EDIT_TEMPLATE, bot=bot)

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
            import shutil
            shutil.rmtree(bot_dir, ignore_errors=True)

        cursor.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
        conn.commit()

    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
