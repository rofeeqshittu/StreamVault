# StreamVault VPS Cheatsheet

This document contains all the essential commands you will ever need to manage StreamVault directly on your VPS.

## 🚀 The "Perfect Restart"
If anything ever goes wrong, gets stuck, or if you just pulled new code, run this block of commands exactly as written to perfectly reset the engine and bring everything back online safely:

```bash
cd /opt/StreamVault
sudo git pull
sudo pkill -f "yt-dlp" || true
sudo pkill -f "smart_monitor.py" || true
sudo pkill -f "monitor_and_capture.sh" || true
sudo pkill -f "telegram_listener.py" || true
sudo nohup python3 -u services/telegram_bot/telegram_listener.py > bot.log 2>&1 &
sudo nohup bash scripts/monitor_and_capture.sh > monitor.log 2>&1 &
```

---

## 📊 Live Monitoring
Use these commands to see exactly what the system is doing right now without waiting for the Telegram bot.

**Check the Background Engine Logs (Real-time)**
```bash
tail -f /opt/StreamVault/monitor.log
```
*(Press `Ctrl+C` to exit the log view)*

**Check the Telegram Bot Logs (Real-time)**
```bash
tail -f /opt/StreamVault/bot.log
```
*(Press `Ctrl+C` to exit the log view)*

**Check Active Download File Sizes**
```bash
sudo ls -lh /opt/StreamVault/staging/session_*
```
*(Run this multiple times; if the `.mp4.part` size is growing, the stream is downloading successfully!)*

**Check Active yt-dlp Process**
```bash
ps aux | grep yt-dlp
```
*(If you see a long line with your YouTube URL, it is actively downloading! If it says `--wait-for-video`, it is actively waiting for the creator to go live!)*

---

## 🧹 Maintenance & Disk Space
Use these commands if your server ever completely runs out of disk space.

**Check Available Disk Space**
```bash
df -h /
```
*(Look at the `Avail` column. You want this to be greater than 1.0G).*

**Emergency Nuke: Delete All Staging Files**
If the disk is 100% full and everything is crashed, this will instantly clear space:
```bash
sudo rm -rf /opt/StreamVault/staging/session_*
sudo rm -f /opt/StreamVault/staging/*.mp4
sudo rm -f /opt/StreamVault/staging/*.mp3
```
*(Warning: This immediately deletes any partial downloads that haven't been uploaded yet).*
