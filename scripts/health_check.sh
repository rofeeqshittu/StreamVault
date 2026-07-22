#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
STAGING_DIR="${STAGING_DIR:-$BASE_DIR/staging}"

echo "[$(date +'%Y-%m-%d %H:%M:%S')] Running health check..."

# Check disk usage (root filesystem or /)
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')

if [ "$DISK_USAGE" -gt 70 ]; then
    echo "WARNING: Disk usage is at ${DISK_USAGE}%! Triggering emergency cleanup."
    
    # Optional: Send webhook alert
    # if [ -n "$DISCORD_WEBHOOK_URL" ]; then ... fi

    if [ -d "$STAGING_DIR" ]; then
        echo "Cleaning orphaned .part and .tmp files older than 2 hours in $STAGING_DIR..."
        find "$STAGING_DIR" -type f \( -name "*.part" -o -name "*.tmp" \) -mmin +120 -exec rm -v {} \;
        
        # Check again
        NEW_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
        echo "Disk usage after cleanup: ${NEW_USAGE}%"
    else
        echo "Staging directory $STAGING_DIR not found."
    fi
else
    echo "Disk usage is normal: ${DISK_USAGE}%"
fi
