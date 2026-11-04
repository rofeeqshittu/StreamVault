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

CONFIG_FILE="${CHANNELS_FILE:-$BASE_DIR/config/channels.json}"
channels=()

if [ -n "${TARGET_CHANNELS:-}" ]; then
    trimmed_targets="$(echo "$TARGET_CHANNELS" | sed -e 's/^[[:space:]]*//')"
    if [[ "$trimmed_targets" =~ ^\[ ]]; then
        mapfile -t channels < <(echo "$TARGET_CHANNELS" | jq -c '.[]')
    else
        IFS=',' read -ra URL_LIST <<< "$TARGET_CHANNELS"
        for item in "${URL_LIST[@]}"; do
            clean_url="$(echo "$item" | xargs)"
            if [ -n "$clean_url" ]; then
                channel_label="$(echo "$clean_url" | sed -nE 's/.*(@[a-zA-Z0-9_.-]+).*/\1/p')"
                [ -z "$channel_label" ] && channel_label="LiveStream"
                channels+=("{\"name\":\"$channel_label\",\"url\":\"$clean_url\"}")
            fi
        done
    fi
elif [ -f "$CONFIG_FILE" ]; then
    mapfile -t channels < <(jq -c '.[]' "$CONFIG_FILE")
else
    echo "Error: No channels configured!"
    echo "To configure target channels, either:"
    echo "  1. Copy config/channels.template.json to config/channels.json and edit it:"
    echo "     cp $BASE_DIR/config/channels.template.json $BASE_DIR/config/channels.json"
    echo "  2. Or set TARGET_CHANNELS in .env:"
    echo "     TARGET_CHANNELS=\"https://www.youtube.com/@ChannelName/live\""
    exit 1
fi

if [ ${#channels[@]} -eq 0 ]; then
    echo "Error: No valid channels found to monitor."
    exit 1
fi


# Function to monitor and capture a single URL
capture_stream() {
    local name="$1"
    local url="$2"
    
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Starting monitor loop for $name: $url"
    
    while true; do
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] Launching smart_monitor for $name ($url)..."
        
        # smart_monitor.py handles intermittent network drops and merging
        python3 "$SCRIPT_DIR/smart_monitor.py" "$url" || true
            
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] Broadcast ended for $name. Waiting 5 minutes before polling for new live streams..."
        sleep 300
    done
}

# Start a background capture process for each target channel
for row in "${channels[@]}"; do

    name=$(echo "$row" | jq -r '.name')
    url=$(echo "$row" | jq -r '.url')
    
    if [[ "$url" != "null" && -n "$url" ]]; then
        capture_stream "$name" "$url" &
    fi
done

# Wait for all background jobs
wait
