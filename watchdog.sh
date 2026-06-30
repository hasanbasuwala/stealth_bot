#!/bin/bash

# Move to the directory where this script lives
cd "$(dirname "$0")"

# Give the Telegram bot 2 seconds to send the "Deploying Updates..." message
sleep 2

echo "🛑 Cleaning up old processes..."
# 1. Kill any older watchdog loops (so we don't spawn infinite duplicates)
script_pid=$$
for pid in $(pgrep -f "watchdog.sh"); do
    if [ "$pid" != "$script_pid" ]; then
        kill -9 $pid 2>/dev/null || true
    fi
done

# 2. Kill the current Python bot
pkill -9 -f "run.py" || true

echo "⬇️ Pulling latest code from GitHub..."
git pull origin main

echo "🚀 Starting the auto-restart loop..."
# The infinite loop keeps the bot alive even if it crashes
while true; do
    python3 run.py
    echo "⚠️ Bot stopped or crashed! Restarting in 5 seconds..."
    sleep 5
done
