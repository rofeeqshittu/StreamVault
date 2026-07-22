#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

# Source environment
if [ -f "$BASE_DIR/.env" ]; then
    source "$BASE_DIR/.env"
fi

GDRIVE_REMOTE="${GDRIVE_REMOTE:-gdrive}"
GDRIVE_PATH="${GDRIVE_PATH:-StreamVault_Archives}"
STAGING_DIR="${STAGING_DIR:-$BASE_DIR/staging}"

FILE_PATH="$1"
FILENAME=$(basename "$FILE_PATH")

echo "[$(date +'%Y-%m-%d %H:%M:%S')] Starting upload for $FILENAME"

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

START_TIME=$(date +%s)

# Use rclone move to upload and delete local file
# --stats-one-line for cleaner logs
echo "Executing rclone move..."
rclone move "$FILE_PATH" "${GDRIVE_REMOTE}:/${GDRIVE_PATH}/" -v --stats-one-line || {
    echo "Error: rclone move failed for $FILENAME"
    # Optional: trigger webhook here
    exit 1
}

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "[$(date +'%Y-%m-%d %H:%M:%S')] Successfully uploaded $FILENAME in ${DURATION}s."

# Secondary verification: ensure local staging is clean of this file
if [ -f "$FILE_PATH" ]; then
    echo "Warning: File $FILE_PATH still exists after rclone move. Forcing delete to preserve disk space."
    rm -f "$FILE_PATH"
fi
