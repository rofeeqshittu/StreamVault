#!/bin/bash

echo "🚀 Starting StreamVault Auto-Update..."

cd /opt/StreamVault || exit

echo "📥 Pulling latest code from GitHub..."
sudo git config --global --add safe.directory /opt/StreamVault
sudo git pull

echo "🧹 Cleaning up old processes (Killing zombies)..."
sudo pkill -f "yt-dlp" || true
sudo pkill -f "smart_monitor.py" || true
sudo pkill -f "monitor_and_capture.sh" || true
sudo pkill -f "telegram_listener.py" || true

echo "♻️ Restarting StreamVault Services via Systemd..."
sudo systemctl restart streamvault
sudo systemctl restart streamvault-bot

echo "✅ Update Complete! StreamVault is now running the latest version."
echo "📲 You can type /status in Telegram to verify."
