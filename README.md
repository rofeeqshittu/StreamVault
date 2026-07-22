# StreamVault

StreamVault is a production-grade automated media and intelligence pipeline. It continuously monitors target YouTube Live channels, records streams in real-time, extracts transcripts/audio, runs the Gemini API to synthesize an executive meeting brief, uploads both the video and the document to Google Drive, and purges local storage to stay within strict disk limits.

## Architecture
- **Server Target:** Optimized for GCP `e2-micro` (Ubuntu 24.04 LTS).
- **Media Tools:** `yt-dlp`, `ffmpeg`.
- **Cloud Storage:** `rclone` (Google Drive OAuth).
- **AI Engine:** Google GenAI SDK (`gemini-1.5-pro` or `gemini-2.5-flash`).
- **Alerts:** Telegram Bot API.
- **Orchestration:** `systemd`.

---

## 1. Installation & Prerequisites

SSH into your Google Cloud VM and install the required tools:

```bash
sudo apt update
sudo apt install -y git ffmpeg yt-dlp rclone python3 python3-pip python3-venv curl
```

Install the Google GenAI SDK globally (or via a venv):
```bash
sudo pip3 install google-genai --break-system-packages
```

---

## 2. Setting Up StreamVault

Clone the repository to `/opt/StreamVault`:
```bash
sudo git clone https://github.com/rofeeqshittu/StreamVault.git /opt/StreamVault
cd /opt/StreamVault
sudo chmod +x scripts/*.sh scripts/*.py
```

Create required directories:
```bash
sudo mkdir -p staging logs
```

---

## 3. Configuration & API Keys

Copy the environment template:
```bash
sudo cp config/env.template .env
```

Edit the `.env` file:
```bash
sudo nano .env
```

### Required Keys:
1. **GEMINI_API_KEY:** Get a free API key from [Google AI Studio](https://aistudio.google.com/).
2. **TELEGRAM_BOT_TOKEN:** Talk to `@BotFather` on Telegram to create a bot and get the token.
3. **TELEGRAM_CHAT_ID:** Send a message to your bot, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates` to find your `chat_id`.

Edit your target channels:
```bash
sudo nano config/channels.json
```
*(Ensure you use the `/live` URL format, e.g., `https://www.youtube.com/@ChannelName/live`)*

---

## 4. Google Drive Connection

Run the rclone interactive setup:
```bash
rclone config
```
1. Press `n` for New remote.
2. Name it `gdrive`.
3. Select `drive` (Google Drive).
4. Leave Client ID/Secret blank.
5. Choose scope `1` (Full access).
6. Skip advanced config.
7. Say `N` to auto-config (since you are headless).
8. **Follow the instructions to authorize rclone from your personal computer** and paste the token back into the VM.

---

## 5. Enable the Background Service

Once configured, tell Linux to start the system daemon:

```bash
sudo cp systemd/streamvault.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now streamvault
```

To watch the live logs:
```bash
tail -f /opt/StreamVault/logs/streamvault.log
```

## System Behavior
- **Zero Transcoding:** Video is captured directly using stream-copy.
- **Automatic Chunking:** If streams are extremely long, `yt-dlp` captures them safely. 
- **Storage Limits:** Kept under 15 GB local limit. A health check ensures old orphaned files are wiped.
- **AI Docs:** Subtitles are automatically extracted and pushed to Gemini to generate high-density notes.
