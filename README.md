# StreamVault

StreamVault is a production-grade automated pipeline designed to run on a Google Cloud `e2-micro` instance (Ubuntu 24.04 LTS). It continuously monitors target YouTube Live channels, records streams directly to disk without re-encoding, uploads the completed streams to Google Drive via `rclone`, and immediately deletes local files to preserve the strict 30 GB persistent disk limit.

## Prerequisites

* Google Cloud `e2-micro` instance running Ubuntu 24.04 LTS.
* 30 GB standard persistent disk.
* A Google Drive account.

## Step-by-Step Setup Guide

### 1. Provision the Environment & Install Dependencies

SSH into your `e2-micro` instance and run:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ffmpeg jq curl unzip git
```

Install the latest release of `yt-dlp`:

```bash
sudo wget https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -O /usr/local/bin/yt-dlp
sudo chmod a+rx /usr/local/bin/yt-dlp
```

### 2. Configure Google Drive Authentication (rclone)

Install `rclone` and initiate the configuration wizard:

```bash
sudo -v ; curl https://rclone.org/install.sh | sudo bash
rclone config
```

1. Create a "New remote" by typing `n`.
2. Assign it the name: `gdrive` (this is the default expected by StreamVault).
3. Select the `drive` option for Google Drive.
4. Follow the CLI prompts to complete the OAuth authentication. Leave Client ID/Secret blank if using defaults, and choose `1` for Full Access.

### 3. Repository Clone & Environment Setup

Clone the StreamVault repository to `/opt/StreamVault`:

```bash
sudo git clone https://github.com/rofeeqshittu/StreamVault.git /opt/StreamVault
cd /opt/StreamVault
```

Configure your environment and targets:

1. Copy `.env.template` to `.env`:
   ```bash
   cp config/env.template .env
   ```
   *Edit `.env` if your `rclone` remote name is different from `gdrive`.*

2. Add your target YouTube URLs to `config/channels.json`:
   ```json
   [
     {
       "name": "MyChannel",
       "url": "https://www.youtube.com/@MyChannel/live"
     }
   ]
   ```

Make scripts executable:
```bash
sudo chmod +x scripts/*.sh
```

### 4. Systemd Service Activation

Create the log directory:
```bash
mkdir -p logs
```

Link the systemd service file and enable it to start on boot:

```bash
sudo ln -s /opt/StreamVault/systemd/streamvault.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now streamvault
```

Verify the service is running:
```bash
sudo systemctl status streamvault
tail -f logs/streamvault.log
```

## Architecture

* **Monitor & Capture**: `scripts/monitor_and_capture.sh` polls YouTube for live streams and uses `yt-dlp` to capture them natively to save CPU overhead.
* **Pipeline & Purge**: `scripts/upload_and_clean.sh` triggers post-capture. It uses `rclone move` to directly push the video to Google Drive and delete it locally.
* **Safety**: `scripts/health_check.sh` monitors disk usage. You can schedule this script via `cron` to run periodically to delete orphaned temporary files.

## Scheduling the Health Check

To automatically monitor disk usage, add `health_check.sh` to a cron job:

```bash
sudo crontab -e
```
Add the following line to run the health check every hour:
```
0 * * * * /opt/StreamVault/scripts/health_check.sh >> /opt/StreamVault/logs/health.log 2>&1
```

## License
MIT License
