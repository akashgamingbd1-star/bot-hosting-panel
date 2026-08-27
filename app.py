import os
import sys
import sqlite3
import subprocess
import time
import shutil
import zipfile
import secrets
from io import BytesIO
from flask import Flask, render_template_string, request, redirect, url_for, send_file, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'multi_bot_hosting_platform_2026_premium_sec_key'

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
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            referral_code TEXT UNIQUE
        )
    ''')
    
    # Bots table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            bot_name TEXT NOT NULL,
            folder_path TEXT NOT NULL,
            main_file TEXT NOT NULL,
            status TEXT DEFAULT 'Stopped',
            logs TEXT DEFAULT 'Ready to run...',
            start_timestamp REAL DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    # Global Settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Default admin setting & Telegram URL
    cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', ('telegram_url', 'https://t.me/your_telegram_channel'))
    
    # Create default admin user if not exists (Username: admin, Password: adminpassword)
    cursor.execute('SELECT * FROM users WHERE role = "admin"')
    if not cursor.fetchone():
        admin_pass = generate_password_hash('adminpassword')
        admin_ref = secrets.token_hex(4)
        cursor.execute('INSERT INTO users (username, password, role, referral_code) VALUES (?, ?, ?, ?)', 
                       ('admin', admin_pass, 'admin', admin_ref))

    conn.commit()
    conn.close()

init_db()

MAIN_TEMPLATE = """
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
        
        /* Top Navigation Bar */
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; }
        .nav-btns { display: flex; align-items: center; gap: 12px; }
        .icon-btn { background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.15); color: #fff; width: 42px; height: 42px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 18px; cursor: pointer; transition: 0.3s; text-decoration: none; }
        .icon-btn:hover { background: rgba(255, 255, 255, 0.2); transform: translateY(-2px); }
        .logo-icon { background: linear-gradient(135deg, #a855f7, #6366f1); color: #fff; width: 42px; height: 42px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 20px; box-shadow: 0 4px 15px rgba(168, 85, 247, 0.4); text-decoration: none; }

        /* Navigation Sidebar/Drawer */
        .drawer { position: fixed; top: 0; left: -300px; width: 300px; height: 100%; background: #0f172a; border-right: 1px solid rgba(255,255,255,0.1); z-index: 1000; transition: 0.3s ease; padding: 25px; box-shadow: 10px 0 30px rgba(0,0,0,0.5); }
        .drawer.open { left: 0; }
        .drawer-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); z-index: 999; display: none; }
        .drawer-overlay.show { display: block; }
        .close-drawer { text-align: right; font-size: 20px; cursor: pointer; color: #94a3b8; margin-bottom: 20px; }
        .ref-box { background: rgba(255,255,255,0.05); padding: 15px; border-radius: 12px; border: 1px dashed rgba(255,255,255,0.2); margin-top: 15px; }
        .ref-input { width: 100%; padding: 8px; background: #020617; border: 1px solid #334155; color: #38bdf8; font-size: 11px; border-radius: 6px; margin-top: 8px; outline: none; }

        .premium-banner { background: linear-gradient(135deg, rgba(124, 58, 237, 0.4), rgba(79, 70, 229, 0.4)); backdrop-filter: blur(12px); border-radius: 20px; padding: 22px; margin-bottom: 22px; text-align: center; border: 1px solid rgba(255,255,255,0.15); box-shadow: 0 10px 30px rgba(0,0,0,0.4); }
        .premium-banner h2 { font-size: 20px; font-weight: 800; letter-spacing: 0.5px; color: #fff; margin-bottom: 6px; display: flex; align-items: center; justify-content: center; gap: 10px; }
        .premium-banner p { font-size: 13px; color: #c7d2fe; }

        .card { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(16px); border-radius: 20px; padding: 22px; margin-bottom: 22px; border: 1px solid rgba(255, 255, 255, 0.1); box-shadow: 0 8px 25px rgba(0,0,0,0.3); }
        .card-title { font-size: 17px; font-weight: 700; margin-bottom: 18px; display: flex; align-items: center; gap: 10px; color: #f1f5f9; }
        
        .input-box { width: 100%; background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 12px; padding: 12px 15px; color: white; margin-bottom: 14px; outline: none; font-size: 14px; }
        .file-input-wrapper { margin-bottom: 12px; }
        .btn-file { width: 100%; padding: 12px; background: rgba(255, 255, 255, 0.05); border: 1px dashed rgba(255, 255, 255, 0.25); border-radius: 12px; color: #cbd5e1; text-align: center; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 10px; font-size: 13px; }
        .btn-deploy { width: 100%; padding: 13px; background: linear-gradient(135deg, #6366f1, #a855f7); border: none; border-radius: 12px; font-weight: 700; cursor: pointer; font-size: 15px; color: white; margin-top: 5px; box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4); }

        .bot-card { background: rgba(15, 23, 42, 0.8); border-radius: 16px; padding: 18px; margin-bottom: 18px; border: 1px solid rgba(255, 255, 255, 0.08); }
        .bot-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .status-badge { font-size: 11px; padding: 4px 10px; border-radius: 20px; font-weight: 700; }
        .status-running { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(52, 211, 153, 0.3); }
        .status-stopped { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(248, 113, 113, 0.3); }

        .bot-actions { display: grid; grid-template-columns: repeat(auto-fit, minmax(75px, 1fr)); gap: 6px; margin-top: 14px; }
        .btn-act { padding: 9px 5px; border-radius: 10px; border: none; font-weight: 600; font-size: 11px; cursor: pointer; text-align: center; text-decoration: none; display: flex; align-items: center; justify-content: center; gap: 4px; color: white; }
        .btn-run { background: #10b981; }
        .btn-stop-bot { background: #f59e0b; }
        .btn-code-edit { background: #8b5cf6; }
        .btn-data { background: #06b6d4; }
        .btn-backup { background: #3b82f6; }
        .btn-del { background: #ef4444; }

        .console-box { background: #020617; border-radius: 10px; padding: 10px 12px; font-family: 'Fira Code', monospace; font-size: 11px; color: #4ade80; max-height: 85px; overflow-y: auto; margin-top: 10px; border: 1px solid rgba(255,255,255,0.05); }
    </style>
</head>
<body>

<div class="drawer-overlay" id="overlay" onclick="toggleDrawer()"></div>

<!-- Navigation Drawer -->
<div class="drawer" id="drawer">
    <div class="close-drawer" onclick="toggleDrawer()"><i class="fa-solid fa-xmark"></i></div>
    <h3><i class="fa-solid fa-bars" style="color:#a855f7;"></i> Navigation</h3>
    <p style="font-size: 12px; color: #94a3b8; margin-top: 5px;">Logged in as: <b>{{ current_user }}</b></p>
    
    {% if is_admin %}
    <div class="ref-box">
        <div style="font-size: 13px; font-weight: bold; color: #38bdf8;"><i class="fa-solid fa-share-nodes"></i> Admin Referral Link</div>
        <p style="font-size: 10px; color: #94a3b8; margin-top: 4px;">শেয়ার করে ইউজার রেজিস্ট্রেশন করাতে পারবেন:</p>
        <input type="text" readonly class="ref-input" value="{{ request.host_url }}register?ref={{ admin_ref_code }}">
    </div>
    {% endif %}

    <div style="margin-top: 25px;">
        <a href="/logout" style="color: #ef4444; text-decoration: none; font-size: 14px; font-weight: bold;"><i class="fa-solid fa-right-from-bracket"></i> Logout Account</a>
    </div>
</div>

<div class="container">
    <div class="header">
        <div class="nav-btns">
            <!-- 3 Lines Drawer Toggle -->
            <button class="icon-btn" onclick="toggleDrawer()"><i class="fa-solid fa-bars"></i></button>
            <i class="fa-solid fa-rotate-right" style="font-size: 18px; cursor: pointer; color: #94a3b8; margin-left: 5px;" onclick="location.reload()"></i>
        </div>
        
        <div class="nav-btns">
            <!-- Admin Panel Button (If Admin) -->
            {% if is_admin %}
            <a href="/admin" class="icon-btn" title="Admin Panel" style="background: rgba(168, 85, 247, 0.2); border-color: #a855f7;"><i class="fa-solid fa-user-shield" style="color:#a855f7;"></i></a>
            {% endif %}
            <!-- Dynamic Telegram Link Logo -->
            <a href="{{ telegram_url }}" target="_blank" class="logo-icon" title="Join Telegram"><i class="fa-paper-plane fa-brands"></i></a>
        </div>
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
    </div>

    <!-- Managed Bots -->
    <div class="card">
        <div class="card-title"><i class="fa-solid fa-server" style="color:#38bdf8;"></i> Managed Bots List</div>
        {% if bots %}
            {% for bot in bots %}
            <div class="bot-card">
                <div class="bot-header">
                    <div class="bot-title" style="font-weight: bold;"><i class="fa-solid fa-robot" style="color:#818cf8;"></i> {{ bot['bot_name'] }}</div>
                    {% if bot['status'] == 'Running' %}
                        <span class="status-badge status-running">● RUNNING</span>
                    {% else %}
                        <span class="status-badge status-stopped">○ STOPPED</span>
                    {% endif %}
                </div>
                <div style="font-size: 12px; color: #94a3b8;">Main File: {{ bot['main_file'] }}</div>
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
                    <a href="/delete/{{ bot['id'] }}" class="btn-act btn-del" onclick="return confirm('ডিলিট করতে চান?')"><i class="fa-solid fa-trash"></i> Del</a>
                </div>
            </div>
            {% endfor %}
        {% else %}
            <div style="text-align: center; color: #64748b; font-size: 13px; padding: 15px;">কোনো বট পাওয়া যায়নি।</div>
        {% endif %}
    </div>
</div>

<script>
function toggleDrawer() {
    document.getElementById('drawer').classList.toggle('open');
    document.getElementById('overlay').classList.toggle('show');
}
function updateLabel(input, labelId, defaultText) {
    const label = document.getElementById(labelId);
    if (input.files.length > 0) { label.innerText = "Selected: " + input.files[0].name; } 
    else { label.innerText = defaultText; }
}
</script>
</body>
</html>
"""

ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <title>Admin Dashboard</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: sans-serif; }
        body { background: #0f172a; color: white; padding: 25px; }
        .container { max-width: 600px; margin: 0 auto; }
        .card { background: #1e293b; padding: 20px; border-radius: 12px; margin-bottom: 20px; border: 1px solid rgba(255,255,255,0.1); }
        h2 { font-size: 18px; margin-bottom: 15px; color: #a855f7; display: flex; align-items: center; gap: 10px; }
        input[type="text"] { width: 100%; padding: 10px; background: #0f172a; border: 1px solid #334155; border-radius: 8px; color: white; margin-bottom: 10px; }
        .btn { padding: 10px 15px; background: #10b981; border: none; border-radius: 8px; color: white; font-weight: bold; cursor: pointer; }
        .btn-back { background: #475569; text-decoration: none; display: inline-block; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="btn btn-back"><i class="fa-solid fa-arrow-left"></i> Back to Home</a>
        
        <div class="card">
            <h2><i class="fa-paper-plane fa-brands"></i> Update Telegram Link</h2>
            <form method="POST" action="/admin/update_telegram">
                <label style="font-size: 12px; color: #94a3b8;">লোগোতে ক্লিক করলে যে Telegram Link খুলবে:</label>
                <input type="text" name="telegram_url" value="{{ telegram_url }}" required style="margin-top: 5px;">
                <button type="submit" class="btn">Update Link</button>
            </form>
        </div>
    </div>
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <title>Login - Hosting Panel</title>
    <style>
        body { background: #0f172a; color: white; display: flex; align-items: center; justify-content: center; height: 100vh; font-family: sans-serif; }
        .box { background: #1e293b; padding: 30px; border-radius: 16px; width: 320px; border: 1px solid rgba(255,255,255,0.1); }
        input { width: 100%; padding: 10px; margin-bottom: 12px; border-radius: 8px; border: 1px solid #334155; background: #0f172a; color: white; box-sizing: border-box; }
        button { width: 100%; padding: 10px; background: #6366f1; border: none; border-radius: 8px; color: white; font-weight: bold; cursor: pointer; }
    </style>
</head>
<body>
    <div class="box">
        <h2 style="text-align: center; margin-bottom: 20px;">Hosting Panel Login</h2>
        <form method="POST" action="/login">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
    </div>
</body>
</html>
"""

# --- ROUTES & CONTROLLERS ---

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))

    conn = get_db()
    cursor = conn.cursor()

    # Telegram URL settings
    cursor.execute('SELECT value FROM settings WHERE key = "telegram_url"')
    tg_row = cursor.fetchone()
    telegram_url = tg_row['value'] if tg_row else '#'

    # Admin Info
    cursor.execute('SELECT role, referral_code FROM users WHERE id = ?', (session['user_id'],))
    user_data = cursor.fetchone()
    is_admin = (user_data['role'] == 'admin')
    admin_ref_code = user_data['referral_code'] if is_admin else ''

    # Get User Bots
    cursor.execute('SELECT * FROM bots WHERE user_id = ? ORDER BY id DESC', (session['user_id'],))
    db_bots = cursor.fetchall()
    
    bots = []
    for bot in db_bots:
        bot_dict = dict(bot)
        if bot_dict['status'] == 'Running' and bot_dict['id'] in active_processes:
            if active_processes[bot_dict['id']]['process'].poll() is not None:
                cursor.execute('UPDATE bots SET status = "Stopped" WHERE id = ?', (bot_dict['id'],))
                conn.commit()
                bot_dict['status'] = 'Stopped'
        bots.append(bot_dict)

    conn.close()
    return render_template_string(MAIN_TEMPLATE, bots=bots, telegram_url=telegram_url, is_admin=is_admin, admin_ref_code=admin_ref_code, current_user=session.get('username'))

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('index'))
            
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

# --- ADMIN ROUTES ---

@app.route('/admin')
def admin_panel():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = "telegram_url"')
    tg_row = cursor.fetchone()
    telegram_url = tg_row['value'] if tg_row else ''
    conn.close()

    return render_template_string(ADMIN_TEMPLATE, telegram_url=telegram_url)

@app.route('/admin/update_telegram', methods=['POST'])
def update_telegram():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))

    new_url = request.form.get('telegram_url')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES ("telegram_url", ?)', (new_url,))
    conn.commit()
    conn.close()

    return redirect(url_for('admin_panel'))

# --- BOT MANAGEMENT ---

@app.route('/upload', methods=['POST'])
def upload():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))

    bot_name = request.form.get('bot_name')
    bot_file = request.files.get('bot_file')

    if not bot_file or not bot_file.filename:
        return redirect(url_for('index'))

    folder_name = f"bot_{session['user_id']}_{int(time.time())}"
    bot_dir = os.path.join(UPLOAD_FOLDER, folder_name)
    os.makedirs(bot_dir, exist_ok=True)

    main_filename = bot_file.filename
    main_path = os.path.join(bot_dir, main_filename)
    bot_file.save(main_path)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO bots (user_id, bot_name, folder_path, main_file, status, logs) VALUES (?, ?, ?, ?, ?, ?)',
                   (session['user_id'], bot_name, bot_dir, main_filename, 'Stopped', "Ready to Run."))
    conn.commit()
    conn.close()

    return redirect(url_for('index'))

@app.route('/start/<int:bot_id>')
def start_bot(bot_id):
    if 'user_id' not in session: return redirect(url_for('login_page'))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, session['user_id']))
    bot = cursor.fetchone()

    if bot:
        proc = subprocess.Popen([sys.executable, bot['main_file']], cwd=bot['folder_path'])
        active_processes[bot_id] = {'process': proc, 'start_time': time.time()}
        cursor.execute('UPDATE bots SET status = "Running", logs = "Bot is running live!" WHERE id = ?', (bot_id,))
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
    cursor.execute('UPDATE bots SET status = "Stopped", logs = "Bot stopped by user." WHERE id = ?', (bot_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/delete/<int:bot_id>')
def delete_bot(bot_id):
    stop_bot(bot_id)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT folder_path FROM bots WHERE id = ? AND user_id = ?', (bot_id, session['user_id']))
    bot = cursor.fetchone()
    if bot:
        shutil.rmtree(bot['folder_path'], ignore_errors=True)
        cursor.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
        conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)