import os
import subprocess
import sys
import threading
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

bot_process = None
console_logs = []

# --- ১. ব্যাকগ্রাউন্ডে বট ও প্যাকেজ রান করার ফাংশন ---
def run_bot_script(bot_path):
    global bot_process, console_logs
    try:
        req_path = os.path.join(UPLOAD_FOLDER, 'requirements.txt')
        if os.path.exists(req_path):
            console_logs.append("Installing requirements.txt...")
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_path], check=True)
            console_logs.append("Requirements installed successfully!")

        console_logs.append("Starting bot...")
        bot_process = subprocess.Popen(
            [sys.executable, bot_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        for line in iter(bot_process.stdout.readline, ''):
            console_logs.append(line.strip())
            if len(console_logs) > 100:
                console_logs.pop(0)

        bot_process.wait()
    except Exception as e:
        console_logs.append(f"Error: {str(e)}")

# --- ২. এক ফাইলেই এইচটিএমএল ইন্টারফেস (UI Design) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GSM Telegram Bot Hosting</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        body { background: linear-gradient(135deg, #4a3b8d 0%, #2b1f5c 100%); color: white; min-height: 100vh; padding: 20px 15px; }
        
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
        .logo-icon { background: white; color: #4a3b8d; width: 45px; height: 45px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 20px; }
        
        .profile-card { display: flex; align-items: center; gap: 15px; margin-bottom: 25px; }
        .avatar { width: 60px; height: 60px; border-radius: 50%; background: #ccc; }
        .user-info h2 { font-size: 20px; font-weight: 700; letter-spacing: 0.5px; }
        .user-info p { color: #bcaaa4; font-size: 14px; }

        .card { background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); border-radius: 20px; padding: 20px; margin-bottom: 20px; border: 1px solid rgba(255, 255, 255, 0.15); }
        .card-title { font-size: 18px; margin-bottom: 15px; display: flex; align-items: center; gap: 10px; }
        
        .file-input-wrapper { margin-bottom: 15px; position: relative; }
        .file-input-wrapper input[type="file"] { display: none; }
        .btn-file { width: 100%; padding: 12px; background: rgba(255, 255, 255, 0.2); border: 1px dashed rgba(255, 255, 255, 0.4); border-radius: 12px; color: white; text-align: center; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 10px; font-size: 15px; }

        .btn-group { display: flex; gap: 10px; margin-top: 20px; }
        .btn { flex: 1; padding: 12px; border: none; border-radius: 12px; font-weight: bold; cursor: pointer; font-size: 15px; }
        .btn-deploy { background: #5c41a8; color: white; }
        .btn-stop { background: #3c2a78; color: #a593e0; }

        .console-card { background: #120b29; border-radius: 15px; padding: 15px; border: 1px solid #2d1e5f; }
        .console-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid #2d1e5f; }
        .console-body { font-family: monospace; font-size: 13px; color: #33ff77; height: 120px; overflow-y: auto; white-space: pre-wrap; }
    </style>
</head>
<body>

    <div class="header">
        <div class="logo">
            <div class="logo-icon"><i class="fa-solid fa-paper-plane"></i></div>
        </div>
        <i class="fa-solid fa-right-from-bracket" style="font-size: 20px;"></i>
    </div>

    <div class="profile-card">
        <div class="avatar" style="background-image: url('https://via.placeholder.com/60'); background-size: cover;"></div>
        <div class="user-info">
            <p>Hello,</p>
            <h2>AKASH DANGEOWNER</h2>
            <p>akashdangerowner@gmail.com</p>
        </div>
    </div>

    <div class="card">
        <div class="card-title"><i class="fa-regular fa-file"></i> Upload Files</div>
        
        <form id="uploadForm">
            <div class="file-input-wrapper">
                <label for="bot_file" class="btn-file" id="botLabel"><i class="fa-solid fa-code"></i> Choose bot.py</label>
                <input type="file" id="bot_file" name="bot_file" accept=".py" onchange="updateLabel(this, 'botLabel', 'Choose bot.py')">
            </div>

            <div class="file-input-wrapper">
                <label for="req_file" class="btn-file" id="reqLabel"><i class="fa-solid fa-list-check"></i> Choose requirements.txt</label>
                <input type="file" id="req_file" name="req_file" accept=".txt" onchange="updateLabel(this, 'reqLabel', 'Choose requirements.txt')">
            </div>

            <div class="btn-group">
                <button type="button" onclick="deployBot()" class="btn btn-deploy">Deploy / Run</button>
                <button type="button" onclick="stopBot()" class="btn btn-stop">Stop</button>
            </div>
        </form>
    </div>

    <div class="console-card">
        <div class="console-header">
            <span>Console</span>
            <div>
                <i class="fa-regular fa-copy" style="cursor: pointer; margin-right: 10px;" onclick="copyLogs()"></i>
                <i class="fa-solid fa-rotate-right" style="cursor: pointer;" onclick="fetchLogs()"></i>
            </div>
        </div>
        <div class="console-body" id="consoleLogs">No bot deployed yet.</div>
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

        async function deployBot() {
            const formData = new FormData(document.getElementById('uploadForm'));
            document.getElementById('consoleLogs').innerText = "Uploading and deploying...";
            
            const response = await fetch('/deploy', { method: 'POST', body: formData });
            const result = await response.json();
            alert(result.message);
        }

        async function stopBot() {
            const response = await fetch('/stop', { method: 'POST' });
            const result = await response.json();
            alert(result.message);
        }

        async function fetchLogs() {
            const response = await fetch('/logs');
            const data = await response.json();
            const consoleBox = document.getElementById('consoleLogs');
            if (data.logs.length > 0) {
                consoleBox.innerText = data.logs.join('\\n');
                consoleBox.scrollTop = consoleBox.scrollHeight;
            }
        }

        function copyLogs() {
            const logs = document.getElementById('consoleLogs').innerText;
            navigator.clipboard.writeText(logs);
            alert("Logs copied to clipboard!");
        }

        setInterval(fetchLogs, 2000);
    </script>
</body>
</html>
"""

# --- ৩. সার্ভার রাউটিং (API Endpoints) ---
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/deploy', methods=['POST'])
def deploy():
    global bot_process, console_logs
    if bot_process and bot_process.poll() is None:
        return jsonify({"status": "error", "message": "A bot is already running!"})

    bot_file = request.files.get('bot_file')
    req_file = request.files.get('req_file')

    if not bot_file:
        return jsonify({"status": "error", "message": "Please select a bot.py file!"})

    console_logs = []
    
    bot_path = os.path.join(UPLOAD_FOLDER, 'bot.py')
    bot_file.save(bot_path)

    if req_file:
        req_path = os.path.join(UPLOAD_FOLDER, 'requirements.txt')
        req_file.save(req_path)

    thread = threading.Thread(target=run_bot_script, args=(bot_path,))
    thread.daemon = True
    thread.start()

    return jsonify({"status": "success", "message": "Bot deployment started!"})

@app.route('/stop', methods=['POST'])
def stop():
    global bot_process, console_logs
    if bot_process and bot_process.poll() is None:
        bot_process.terminate()
        bot_process = None
        console_logs.append("Bot stopped by user.")
        return jsonify({"status": "success", "message": "Bot stopped!"})
    return jsonify({"status": "error", "message": "No running bot found!"})

@app.route('/logs')
def get_logs():
    return jsonify({"logs": console_logs})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
