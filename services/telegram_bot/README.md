# Telegram Listener Service

This is an autonomous routing service built to comply with the project's strict `services-first` micro-architecture.

## Features
- Infinite long-polling loop via Telegram API
- Strict Chat ID validation ensuring military-grade authorization
- Regex extraction to identify YouTube URLs in chat payloads
- Non-blocking asynchronous routing of URLs to the background `upload_and_clean.sh` agent

## Running
Run inside a screen to persist across sessions:
`screen -dmS tgbot python3 telegram_listener.py`
