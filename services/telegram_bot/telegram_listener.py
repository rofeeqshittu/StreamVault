#!/usr/bin/env python3
import os
import sys
import time
import requests
import re
import subprocess
from pathlib import Path

# Fix path to point to root project
SERVICE_DIR = Path(__file__).resolve().parent
BASE_DIR = SERVICE_DIR.parent.parent

# Load .env
env_file = BASE_DIR / '.env'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, val = line.strip().split('=', 1)
                os.environ[key] = val.strip('"').strip("'")

API_URL = ""

def send_message(text):
    global API_URL
    ALLOWED_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
    requests.post(f"{API_URL}/sendMessage", data={
        "chat_id": ALLOWED_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    })

import threading

def run_download_task(cmd, url):
    process = subprocess.run(cmd, capture_output=True, text=True)
    if process.returncode != 0:
        # If it failed, grab the last few lines of the error to help debug
        error_lines = process.stderr.strip().split('\n')
        error_msg = '\n'.join(error_lines[-5:]) if error_lines else "Unknown error"
        send_message(f"❌ *Download Failed!*\n\nCould not download: `{url}`\n\n*Error details:*\n`{error_msg}`")

def trigger_download(url):
    staging_dir = BASE_DIR / 'staging'
    staging_dir.mkdir(exist_ok=True)
    
    upload_script = BASE_DIR / 'scripts' / 'upload_and_clean.sh'
    
    cmd = [
        "yt-dlp",
        "--extractor-args", "youtube:player_client=ios,android,web",
        "--write-auto-sub",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "-o", f"{staging_dir}/ondemand_%(uploader)s_%(id)s.%(ext)s",
        "--exec", f"{upload_script} {{}}",
        url
    ]
    
    print(f"Triggering background download for: {url}")
    # Spawn in background thread to catch errors without blocking bot loop
    thread = threading.Thread(target=run_download_task, args=(cmd, url))
    thread.daemon = True
    thread.start()

def extract_url(text):
    match = re.search(r'(https?://[^\s]+)', text)
    return match.group(1) if match else None

def main():
    global API_URL
    BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    ALLOWED_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

    if not BOT_TOKEN or not ALLOWED_CHAT_ID:
        print("Error: Missing Telegram credentials in .env")
        sys.exit(1)

    API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
    print("Telegram Listener Started. Polling for commands...")
    offset = None
    
    while True:
        try:
            req = requests.get(f"{API_URL}/getUpdates", params={"offset": offset, "timeout": 30})
            data = req.json()
            
            if not data.get("ok"):
                time.sleep(5)
                continue
                
            for update in data.get("result", []):
                offset = update["update_id"] + 1
                
                message = update.get("message")
                if not message:
                    continue
                    
                chat_id = str(message.get("chat", {}).get("id"))
                text = message.get("text", "")
                
                # Military-grade security: Ignore anything not from the owner
                if chat_id != str(ALLOWED_CHAT_ID):
                    print(f"Ignored unauthorized message from chat_id: {chat_id}")
                    continue
                    
                if text.strip().lower() == "/status":
                    screen_out = subprocess.run(["screen", "-list"], capture_output=True, text=True).stdout
                    is_running = "streamvault" in screen_out.lower()
                    
                    status_text = "🟢 *Monitor is ACTIVE* (Running in background)" if is_running else "🔴 *Monitor is OFFLINE* (Not running)"
                    send_message(f"📊 *StreamVault Status*\n\n{status_text}")
                    continue

                url = extract_url(text)
                if url:
                    send_message(f"🚀 *On-Demand Command Received!*\n\nTarget: `{url}`\n\nI have dispatched the background agents to download and process this stream. You will receive the AI Brief when it completes.")
                    trigger_download(url)
                else:
                    send_message("❌ No URL detected. Send a YouTube link to download, or type `/status` to check the live monitor.")
                    
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
