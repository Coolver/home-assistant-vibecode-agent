#!/usr/bin/with-contenv bashio

# Get configuration from add-on options
PORT=$(bashio::config 'port')
LOG_LEVEL=$(bashio::config 'log_level')
ENABLE_GIT=$(bashio::config 'enable_git_versioning')
GIT_VERSIONING_AUTO=$(bashio::config 'git_versioning_auto')
MAX_BACKUPS=$(bashio::config 'max_backups')

# Get Home Assistant details
HA_TOKEN="${SUPERVISOR_TOKEN}"
HA_URL="http://supervisor/core"

# Export environment variables
export PORT="${PORT}"
export LOG_LEVEL="${LOG_LEVEL}"
export ENABLE_GIT="${ENABLE_GIT}"
export GIT_VERSIONING_AUTO="${GIT_VERSIONING_AUTO}"
export MAX_BACKUPS="${MAX_BACKUPS}"
export HA_TOKEN="${HA_TOKEN}"
export HA_URL="${HA_URL}"
export CONFIG_PATH="/config"

# Initialize Git repo if enabled
if [ "${ENABLE_GIT}" = "true" ]; then
    bashio::log.info "Initializing Git repository for config versioning..."
    cd /config
    if [ ! -d ".git" ]; then
        git init
        git config user.name "HA Cursor Agent"
        git config user.email "agent@homeassistant.local"
        git add -A
        git commit -m "Initial commit by HA Cursor Agent" || true
        bashio::log.info "Git repository initialized"
    fi
    cd /app
fi

bashio::log.info "Starting HA Cursor Agent on port ${PORT}..."
bashio::log.info "Log level: ${LOG_LEVEL}"
bashio::log.info "Git versioning: ${ENABLE_GIT}"
bashio::log.info "Git versioning auto: ${GIT_VERSIONING_AUTO}"

# Start FastAPI application
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" --log-level "${LOG_LEVEL}"

