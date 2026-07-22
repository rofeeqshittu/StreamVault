#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

# Source environment and export variables to child processes
if [ -f "$BASE_DIR/.env" ]; then
    set -a
    source "$BASE_DIR/.env"
    set +a
fi

GDRIVE_REMOTE="${GDRIVE_REMOTE:-gdrive}"
GDRIVE_PATH="${GDRIVE_PATH:-StreamVault_Archives}"
STAGING_DIR="${STAGING_DIR:-$BASE_DIR/staging}"

FILE_PATH="$1"
FILENAME=$(basename "$FILE_PATH")

echo "[$(date +'%Y-%m-%d %H:%M:%S')] Starting post-processing for $FILENAME"

# File integrity check (basic size check > 0)
if [ ! -f "$FILE_PATH" ]; then
    echo "Error: File $FILE_PATH does not exist."
    exit 1
fi

FILE_SIZE=$(stat -c%s "$FILE_PATH")
if [ "$FILE_SIZE" -eq 0 ]; then
    echo "Error: File $FILE_PATH is empty. Deleting."
    rm -f "$FILE_PATH"
    exit 1
fi

# 1. Generate AI Executive Brief
echo "Triggering AI Documentation Engine..."
python3 "$SCRIPT_DIR/generate_ai_docs.py" "$FILE_PATH"

DOCX_PATH="${FILE_PATH%.*}.docx"

START_TIME=$(date +%s)

# 2. Telegram Alert with Attached Document
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
    echo "Sending Telegram alert with AI Document attached..."
    if [ -f "$DOCX_PATH" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendDocument" \
            -F chat_id="${TELEGRAM_CHAT_ID}" \
            -F document=@"$DOCX_PATH" \
            -F caption="✅ *StreamVault Success!*
            
Video uploaded for: \`${FILENAME}\`
Here is your complete AI Executive Brief.

Check your Google Drive folder: \`${GDRIVE_PATH}\`" \
            -F parse_mode="Markdown" > /dev/null
    else
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d chat_id="${TELEGRAM_CHAT_ID}" \
            -d text="✅ *StreamVault Success!* (AI brief failed to generate)
            
Video uploaded for: \`${FILENAME}\`

Check your Google Drive folder: \`${GDRIVE_PATH}\`" \
            -d parse_mode="Markdown" > /dev/null
    fi
fi

# 3. Upload Video and Document via rclone move
echo "Executing rclone move for media and documents..."
rclone move "$FILE_PATH" "${GDRIVE_REMOTE}:/${GDRIVE_PATH}/" -v --stats-one-line || {
    echo "Error: rclone move failed for $FILENAME"
    exit 1
}

if [ -f "$DOCX_PATH" ]; then
    rclone move "$DOCX_PATH" "${GDRIVE_REMOTE}:/${GDRIVE_PATH}/" -v --stats-one-line || true
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "[$(date +'%Y-%m-%d %H:%M:%S')] Successfully uploaded $FILENAME in ${DURATION}s."

# 4. Secondary verification: ensure local staging is clean
if [ -f "$FILE_PATH" ]; then
    rm -f "$FILE_PATH"
fi
if [ -f "$DOCX_PATH" ]; then
    rm -f "$DOCX_PATH"
fi
# Clean any VTT files left behind
VTT_PATH="${FILE_PATH%.*}.vtt"
VTT_EN_PATH="${FILE_PATH%.*}.en.vtt"
[ -f "$VTT_PATH" ] && rm -f "$VTT_PATH" || true
[ -f "$VTT_EN_PATH" ] && rm -f "$VTT_EN_PATH" || true

