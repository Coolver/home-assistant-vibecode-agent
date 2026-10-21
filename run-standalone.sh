#!/bin/bash
set -e

# HA Vibecode Agent — Standalone mode (no Supervisor/bashio required)
# For users running Home Assistant Container in Docker/Proxmox without HAOS

# Required environment variables
HA_URL="${HA_URL:?Error: HA_URL is required (e.g. http://192.168.1.100:8123)}"
HA_TOKEN="${HA_TOKEN:?Error: HA_TOKEN is required (Long-Lived Access Token from HA UI -> Profile)}"

# Optional configuration with defaults
PORT="${PORT:-8099}"
LOG_LEVEL="${LOG_LEVEL:-info}"
GIT_VERSIONING_AUTO="${GIT_VERSIONING_AUTO:-true}"
MAX_BACKUPS="${MAX_BACKUPS:-30}"
ALLOW_SENSITIVE_FILES="${ALLOW_SENSITIVE_FILES:-false}"
CONFIG_PATH="${CONFIG_PATH:-/config}"

# Export for the Python application
export PORT
export LOG_LEVEL
export GIT_VERSIONING_AUTO
export MAX_BACKUPS
export ALLOW_SENSITIVE_FILES
export HA_URL
export HA_TOKEN
export CONFIG_PATH

echo "==========================================="
echo " HA Vibecode Agent — Standalone Mode"
echo "==========================================="
echo " HA URL:    ${HA_URL}"
echo " Port:      ${PORT}"
echo " Log level: ${LOG_LEVEL}"
echo " Config:    ${CONFIG_PATH}"
echo "==========================================="

exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" --log-level "${LOG_LEVEL}"
