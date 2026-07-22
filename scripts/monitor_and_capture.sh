#!/usr/bin/env bash
set -euo pipefail

# Determine script directory to locate configs
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

# Source environment
if [ -f "$BASE_DIR/.env" ]; then
    source "$BASE_DIR/.env"
else
    echo "Warning: .env not found, using defaults"
fi

STAGING_DIR="${STAGING_DIR:-$BASE_DIR/staging}"
LOGS_DIR="${BASE_DIR}/logs"
mkdir -p "$STAGING_DIR" "$LOGS_DIR"

CONFIG_FILE="$BASE_DIR/config/channels.json"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: channels.json not found!"
    exit 1
fi

# Function to monitor and capture a single URL
capture_stream() {
    local name="$1"
    local url="$2"
    
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Starting monitor loop for $name: $url"
    
    while true; do
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] yt-dlp polling $url..."
        
        # Capture stream using yt-dlp
        # --wait-for-video to keep polling
        # -f best to get best quality that doesn't need re-encoding
        # --exec to call upload script when done
        yt-dlp \
            --wait-for-video 60 \
            -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" \
            -o "$STAGING_DIR/%(uploader)s_%(title)s_%(id)s_%(upload_date)s.%(ext)s" \
            --exec "$SCRIPT_DIR/upload_and_clean.sh {}" \
            "$url" || true
            
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] Stream ended or interrupted for $name. Waiting 10 seconds before retry..."
        sleep 10
    done
}

# Read channels and start a background process for each
mapfile -t channels < <(jq -c '.[]' "$CONFIG_FILE")

for row in "${channels[@]}"; do
    name=$(echo "$row" | jq -r '.name')
    url=$(echo "$row" | jq -r '.url')
    
    if [[ "$url" != "null" && -n "$url" ]]; then
        capture_stream "$name" "$url" &
    fi
done

# Wait for all background jobs
wait
