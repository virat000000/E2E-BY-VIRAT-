from flask import Flask, render_template_string, request, jsonify, session
from flask_cors import CORS
from datetime import datetime
import sqlite3
import os
import threading
import queue
import time
import json
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import logging

# ==================== APP SETUP ====================
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
CORS(app)

# ==================== LOGGING ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== DATABASE ====================
DB_NAME = 'e2e_tool.db'

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS credentials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        type TEXT,
        value TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        target_uid TEXT,
        target_name TEXT,
        delay_seconds REAL,
        message_text TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_sent INTEGER DEFAULT 0,
        total_failed INTEGER DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER,
        log_type TEXT,
        message TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()
    logger.info("Database ready")

init_db()

# ==================== GLOBAL VARIABLES ====================
JOB_QUEUE = queue.Queue()
active_jobs = {}
console_logs = {}

# ==================== DECORATOR ====================
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Login required'}), 401
        return f(*args, **kwargs)
    return wrap

# ==================== JOB PROCESSOR ====================
class JobProcessor:
    def __init__(self):
        self.running = True
        self.thread = threading.Thread(target=self.process_queue, daemon=True)
        self.thread.start()
    
    def process_queue(self):
        while self.running:
            try:
                job_id = JOB_QUEUE.get(timeout=1)
                if job_id in active_jobs:
                    self.run_job(job_id)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Queue error: {e}")
                time.sleep(1)
    
    def run_job(self, job_id):
        job = active_jobs[job_id]
        self.log(job_id, 'info', f'🚀 Job Started - Target: {job["target_name"]}')
        
        conn = get_db()
        creds = conn.execute('SELECT value FROM credentials WHERE user_id=?', 
                            (job['user_id'],)).fetchall()
        conn.close()
        
        if not creds:
            self.log(job_id, 'error', '❌ No credentials found')
            self.update_status(job_id, 'failed')
            return
        
        credentials = [c[0] for c in creds]
        total = len(credentials)
        success = 0
        failed = 0
        
        self.log(job_id, 'info', f'📊 Loaded {total} credentials')
        
        cycle = 1
        while job_id in active_jobs and active_jobs[job_id]['status'] == 'running':
            self.log(job_id, 'info', f'🔄 Cycle {cycle} started')
            
            for i, cred in enumerate(credentials, 1):
                if job_id not in active_jobs or active_jobs[job_id]['status'] != 'running':
                    break
                
                # Simulate sending (replace with actual API call)
                time.sleep(0.3)
                
                if i % 10 != 0:  # 90% success rate
                    success += 1
                    self.log(job_id, 'success', f'✅ Message {i} sent to {job["target_name"]}')
                else:
                    failed += 1
                    self.log(job_id, 'error', f'❌ Message {i} failed')
                
                # Update DB
                conn = get_db()
                conn.execute('UPDATE jobs SET total_sent=?, total_failed=? WHERE id=?',
                           (success, failed, job_id))
                conn.commit()
                conn.close()
                
                if i < total:
                    time.sleep(job['delay_seconds'])
            
            if job_id in active_jobs and active_jobs[job_id]['status'] == 'running':
                self.log(job_id, 'success', f'✅ Cycle {cycle} done: {success} sent, {failed} failed')
                cycle += 1
                time.sleep(job['delay_seconds'] * 2)
        
        self.update_status(job_id, 'stopped')
        self.log(job_id, 'info', '🏁 Job stopped')
    
    def log(self, job_id, log_type, message):
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        if job_id not in console_logs:
            console_logs[job_id] = []
        console_logs[job_id].append({'timestamp': timestamp, 'type': log_type, 'message': message})
        
        if len(console_logs[job_id]) > 200:
            console_logs[job_id] = console_logs[job_id][-200:]
    
    def update_status(self, job_id, status):
        conn = get_db()
        conn.execute('UPDATE jobs SET status=? WHERE id=?', (status, job_id))
        conn.commit()
        conn.close()

job_processor = JobProcessor()

# ==================== HTML TEMPLATE ====================
HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>End to end Tool by Virat Rajput</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #fff 0%, #E3F2FD 50%, #BBDEFB 100%); min-height: 100vh; }
        .header { background: linear-gradient(135deg, #0D47A1, #1565C0); color: white; padding: 25px; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.2); }
        .header h1 { font-size: 2em; font-weight: 800; }
        .header h3 { color: #00BCD4; margin-top: 10px; }
        .container { max-width: 1200px; margin: 20px auto; padding: 20px; }
        .card { background: white; border-radius: 15px; box-shadow: 0 8px 32px rgba(21,101,192,0.1); margin-bottom: 20px; }
        .card-header { background: linear-gradient(135deg, #1565C0, #1976D2); color: white; border-radius: 15px 15px 0 0; padding: 15px 20px; font-weight: 700; }
        .card-body { padding: 20px; }
        .btn { padding: 10px 25px; font-weight: 600; border-radius: 10px; transition: all 0.3s; }
        .btn-danger { background: #F44336; border: none; color: white; font-size: 1.1em; }
        .btn-warning { background: #FF9800; border: none; color: white; font-size: 1.1em; }
        .btn-primary { background: #1565C0; border: none; color: white; }
        .console { background: #0A1929; color: #00FF41; font-family: 'Courier New', monospace; padding: 15px; border-radius: 10px; height: 400px; overflow-y: auto; border: 2px solid #00BCD4; }
        .console .log-entry { padding: 3px 0; border-bottom: 1px solid rgba(0,255,65,0.05); }
        .timestamp { color: #FFD700; font-weight: bold; }
        .success { color: #4CAF50; }
        .error { color: #F44336; }
        .info { color: #2196F3; }
        .footer { background: linear-gradient(135deg, #0D47A1, #1565C0); color: white; text-align: center; padding: 30px; margin-top: 50px; }
        .neon-text { color: #00BCD4; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔐 End to End Offline Tool by Virat Rajput</h1>
        <h3>🚀 Offline Tool Non-Stop E2E Advanced System</h3>
    </div>
    
    <div class="container">
        <div id="auth-section">
            <div class="card">
                <div class="card-header">🔑 Account Access</div>
                <div class="card-body">
                    <div id="login-form">
                        <h4 class="mb-4">Login</h4>
                        <div class="mb-3"><label>Username</label><input type="text" class="form-control" id="login-username"></div>
                        <div class="mb-3"><label>Password (Min 8 chars)</label><input type="password" class="form-control" id="login-password"></div>
                        <button class="btn btn-primary" onclick="login()">Login</button>
                        <button class="btn btn-link" onclick="showRegister()">Create Account</button>
                    </div>
                    <div id="register-form" style="display:none;">
                        <h4 class="mb-4">Create Account</h4>
                        <div class="mb-3"><label>Email</label><input type="email" class="form-control" id="reg-email"></div>
                        <div class="mb-3"><label>Username</label><input type="text" class="form-control" id="reg-username"></div>
                        <div class="mb-3"><label>Password (Min 8 chars)</label><input type="password" class="form-control" id="reg-password"></div>
                        <div class="mb-3"><label>Confirm Password</label><input type="password" class="form-control" id="reg-confirm"></div>
                        <button class="btn btn-primary" onclick="register()">Create Account</button>
                        <button class="btn btn-link" onclick="showLogin()">Back to Login</button>
                    </div>
                </div>
            </div>
        </div>
        
        <div id="dashboard-section" style="display:none;">
            <div class="card">
                <div class="card-body">
                    <h5>👋 Welcome, <span id="user-display"></span></h5>
                    <button class="btn btn-danger btn-sm" onclick="logout()">Logout</button>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">📋 Cookies & Tokens</div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label>Cookies (One per line)</label>
                            <textarea class="form-control" id="cookies-input" rows="3"></textarea>
                        </div>
                        <div class="col-md-6 mb-3">
                            <label>Tokens (One per line)</label>
                            <textarea class="form-control" id="tokens-input" rows="3"></textarea>
                        </div>
                    </div>
                    <button class="btn btn-primary" onclick="addCredentials()">Add Credentials</button>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">⚙️ Job Configuration</div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-4 mb-3">
                            <label>Target UID</label>
                            <input type="text" class="form-control" id="target-uid" placeholder="Facebook User ID">
                        </div>
                        <div class="col-md-4 mb-3">
                            <label>Target Name (Hater's Name)</label>
                            <input type="text" class="form-control" id="target-name" placeholder="Target name">
                        </div>
                        <div class="col-md-4 mb-3">
                            <label>Delay (Seconds)</label>
                            <input type="number" class="form-control" id="delay" value="5" min="1">
                        </div>
                    </div>
                    <div class="mb-3">
                        <label>Message</label>
                        <textarea class="form-control" id="message-text" rows="3"></textarea>
                    </div>
                    <button class="btn btn-danger" onclick="startJob()">🚀 START SENDING</button>
                    <button class="btn btn-warning ms-2" onclick="stopJob()">⏹ STOP</button>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">📟 Live Console</div>
                <div class="card-body">
                    <div class="console" id="console">
                        <div class="log-entry"><span class="info">Console ready...</span></div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="footer">
        <p><strong>Made by Virat Rajput (Software Developer)</strong></p>
        <p>End to End Offline Server</p>
        <p>All rights reserved 2026</p>
        <p class="neon-text">⚡ 24/7 Running | 🔒 Secure | 🚀 High Performance</p>
    </div>
    
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script>
        let currentJobId = null;
        let consoleInterval = null;
        
        function showRegister() { $('#login-form').hide(); $('#register-form').show(); }
        function showLogin() { $('#register-form').hide(); $('#login-form').show(); }
        
        async function register() {
            const data = {
                email: $('#reg-email').val().trim(),
                username: $('#reg-username').val().trim(),
                password: $('#reg-password').val(),
                confirm_password: $('#reg-confirm').val()
            };
            
            if (!data.email || !data.username || !data.password || !data.confirm_password)
                return alert('All fields required');
            if (data.password.length < 8) return alert('Password min 8 characters');
            if (data.password !== data.confirm_password) return alert('Passwords do not match');
            
            const res = await fetch('/api/register', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            const result = await res.json();
            alert(result.message || result.error);
            if (result.success) showLogin();
        }
        
        async function login() {
            const data = {
                username: $('#login-username').val().trim(),
                password: $('#login-password').val()
            };
            
            if (!data.username || !data.password) return alert('Enter username and password');
            
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            const result = await res.json();
            if (result.success) {
                $('#auth-section').hide();
                $('#dashboard-section').show();
                $('#user-display').text(result.user.username);
            } else {
                alert(result.error);
            }
        }
        
        async function logout() {
            await fetch('/api/logout', {method: 'POST'});
            location.reload();
        }
        
        async function addCredentials() {
            const data = {
                cookies: $('#cookies-input').val(),
                tokens: $('#tokens-input').val()
            };
            
            if (!data.cookies && !data.tokens) return alert('Enter cookies or tokens');
            
            const res = await fetch('/api/credentials/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            const result = await res.json();
            alert(result.message);
            if (result.success) $('#cookies-input, #tokens-input').val('');
        }
        
        async function startJob() {
            const data = {
                target_uid: $('#target-uid').val().trim(),
                target_name: $('#target-name').val().trim(),
                delay: parseFloat($('#delay').val()),
                message: $('#message-text').val().trim()
            };
            
            if (!data.target_uid && !data.target_name) return alert('Enter target details');
            if (!data.message) return alert('Enter message');
            
            const res = await fetch('/api/jobs/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            const result = await res.json();
            if (result.success) {
                currentJobId = result.job_id;
                alert('✅ Job started!');
                startConsole();
            } else {
                alert(result.error);
            }
        }
        
        async function stopJob() {
            if (!currentJobId) return alert('No active job');
            
            const res = await fetch('/api/jobs/stop', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({job_id: currentJobId})
            });
            const result = await res.json();
            if (result.success) {
                stopConsole();
                currentJobId = null;
                alert('Job stopped');
            }
        }
        
        function startConsole() {
            if (consoleInterval) return;
            consoleInterval = setInterval(updateConsole, 1000);
        }
        
        function stopConsole() {
            if (consoleInterval) {
                clearInterval(consoleInterval);
                consoleInterval = null;
            }
        }
        
        async function updateConsole() {
            if (!currentJobId) return;
            try {
                const res = await fetch('/api/jobs/logs/' + currentJobId);
                const data = await res.json();
                if (data.success && data.logs) {
                    const div = $('#console');
                    div.empty();
                    data.logs.forEach(log => {
                        div.append(`<div class="log-entry"><span class="timestamp">[${log.timestamp}]</span> <span class="${log.type}">${log.message}</span></div>`);
                    });
                    div.scrollTop(div[0].scrollHeight);
                }
            } catch(e) {}
        }
        
        setInterval(async () => {
            try { await fetch('/api/health'); } catch(e) {}
        }, 30000);
    </script>
</body>
</html>'''

# ==================== ROUTES ====================
@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        email = data.get('email', '').strip()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        confirm = data.get('confirm_password', '')
        
        if not all([email, username, password, confirm]):
            return jsonify({'error': 'All fields required'}), 400
        if len(password) < 8:
            return jsonify({'error': 'Password min 8 characters'}), 400
        if password != confirm:
            return jsonify({'error': 'Passwords do not match'}), 400
        
        conn = get_db()
        existing = conn.execute('SELECT id FROM users WHERE username=? OR email=?', 
                               (username, email)).fetchone()
        if existing:
            conn.close()
            return jsonify({'error': 'Username/Email already exists'}), 400
        
        hash_pw = generate_password_hash(password)
        conn.execute('INSERT INTO users (username, email, password_hash) VALUES (?,?,?)',
                    (username, email, hash_pw))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Account created! Please login.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return jsonify({'success': True, 'user': {'username': user['username']}})
        
        return jsonify({'error': 'Invalid credentials'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/credentials/add', methods=['POST'])
@login_required
def add_credentials():
    try:
        data = request.get_json()
        cookies = data.get('cookies', '')
        tokens = data.get('tokens', '')
        
        conn = get_db()
        count = 0
        
        for line in cookies.split('\n'):
            line = line.strip()
            if line:
                conn.execute('INSERT INTO credentials (user_id, type, value) VALUES (?,?,?)',
                           (session['user_id'], 'cookie', line))
                count += 1
        
        for line in tokens.split('\n'):
            line = line.strip()
            if line:
                conn.execute('INSERT INTO credentials (user_id, type, value) VALUES (?,?,?)',
                           (session['user_id'], 'token', line))
                count += 1
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'Added {count} credentials'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/start', methods=['POST'])
@login_required
def start_job():
    try:
        data = request.get_json()
        target_uid = data.get('target_uid', '').strip()
        target_name = data.get('target_name', '').strip()
        delay = float(data.get('delay', 5))
        message = data.get('message', '').strip()
        
        if not target_name:
            return jsonify({'error': 'Target name required'}), 400
        if not message:
            return jsonify({'error': 'Message required'}), 400
        
        conn = get_db()
        
        running = conn.execute('SELECT id FROM jobs WHERE user_id=? AND status="running"',
                              (session['user_id'],)).fetchone()
        if running:
            conn.close()
            return jsonify({'error': 'Stop current job first'}), 400
        
        conn.execute('INSERT INTO jobs (user_id, target_uid, target_name, delay_seconds, message_text, status) VALUES (?,?,?,?,?,"pending")',
                    (session['user_id'], target_uid, target_name, delay, message))
        job_id = conn.lastrowid
        conn.commit()
        conn.close()
        
        active_jobs[job_id] = {
            'user_id': session['user_id'],
            'target_uid': target_uid,
            'target_name': target_name,
            'delay_seconds': delay,
            'message_text': message,
            'status': 'pending'
        }
        
        console_logs[job_id] = []
        
        JOB_QUEUE.put(job_id)
        
        conn = get_db()
        conn.execute('UPDATE jobs SET status="running" WHERE id=?', (job_id,))
        conn.commit()
        conn.close()
        
        if job_id in active_jobs:
            active_jobs[job_id]['status'] = 'running'
        
        return jsonify({'success': True, 'job_id': job_id, 'message': 'Job started'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/stop', methods=['POST'])
@login_required
def stop_job():
    try:
        data = request.get_json()
        job_id = data.get('job_id')
        
        if job_id and job_id in active_jobs:
            active_jobs[job_id]['status'] = 'stopped'
            del active_jobs[job_id]
        else:
            for jid in list(active_jobs.keys()):
                if active_jobs[jid]['user_id'] == session['user_id']:
                    del active_jobs[jid]
        
        conn = get_db()
        conn.execute('UPDATE jobs SET status="stopped" WHERE user_id=? AND status="running"',
                    (session['user_id'],))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Job stopped'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/logs/<int:job_id>')
@login_required
def get_logs(job_id):
    logs = console_logs.get(job_id, [])
    return jsonify({'success': True, 'logs': logs[-50:]})

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)