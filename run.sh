#!/usr/bin/with-contenv bashio

# Get configuration from add-on options
PORT=$(bashio::config 'port')
LOG_LEVEL=$(bashio::config 'log_level')
GIT_VERSIONING_AUTO=$(bashio::config 'git_versioning_auto')
MAX_BACKUPS=$(bashio::config 'max_backups')

# Get Home Assistant details
HA_TOKEN="${SUPERVISOR_TOKEN}"
HA_URL="http://supervisor/core"

# Export environment variables
export PORT="${PORT}"
export LOG_LEVEL="${LOG_LEVEL}"
export GIT_VERSIONING_AUTO="${GIT_VERSIONING_AUTO}"
export MAX_BACKUPS="${MAX_BACKUPS}"
export HA_TOKEN="${HA_TOKEN}"
export HA_URL="${HA_URL}"
export CONFIG_PATH="/config"

bashio::log.info "Starting HA Vibecode Agent on port ${PORT}..."
bashio::log.info "Log level: ${LOG_LEVEL}"
bashio::log.info "Git versioning auto: ${GIT_VERSIONING_AUTO}"

# Start FastAPI application
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" --log-level "${LOG_LEVEL}"

