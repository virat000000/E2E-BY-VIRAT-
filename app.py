import os
import asyncio
import aiohttp
from flask import Flask, render_template, request, jsonify
from datetime import datetime

app = Flask(__name__)

# --- Configuration ---
# Render port check karne ke liye
PORT = int(os.environ.get('PORT', 5000))

# --- Helper Functions ---
async def fetch_data(session, url, headers):
    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.text()
            else:
                return f"Status Code: {response.status}"
    except Exception as e:
        return str(e)

@app.route('/')
def index():
    """Home page render karega"""
    return render_template('index.html')

@app.route('/api/hack', methods=['POST'])
async def start_hack():
    """API endpoint for the hack tool"""
    data = await request.get_json()
    
    username = data.get('username', '')
    user_id = data.get('user_id', '')
    appeal_text = data.get('appeal_text', 'Default English Appeal')

    if not username:
        return jsonify({'status': 'error', 'message': 'Username required'}), 400

    # --- Simulating the Hack/Brute Force Process (Async) ---
    # Yahan aap apna actual logic daal sakte hain
    
    try:
        # Example: Async API Call (Render par fast chalega)
        async with aiohttp.ClientSession() as session:
            # Mock URL (Aap apni real API URL yahan daal sakte hain)
            url = f"https://api.example.com/endpoint?user={username}&id={user_id}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/json'
            }
            
            result = await fetch_data(session, url, headers)
            
            # Fake Progress Bar Logic for Demo
            progress_steps = [10, 25, 50, 75, 90, 100]
            final_result = "Success! Account details fetched."
            
            return jsonify({
                'status': 'success',
                'message': f"Processing for {username}...",
                'details': result,
                'progress': progress_steps,
                'final_status': final_result
            })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    # Render par run karne ke liye yeh line zaroori hai
    app.run(host='0.0.0.0', port=PORT, debug=True)
