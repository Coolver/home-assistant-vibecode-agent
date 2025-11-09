# Changelog

All notable changes to this project will be documented in this file.

## [2.3.4] - 2025-11-09

### 🐛 Critical Bug Fix

**Supervisor API Endpoint Fix:**
- ✅ Fixed all Supervisor API endpoints to use correct `/supervisor/` prefix
- ✅ Changed from `http://supervisor/addons` to `http://supervisor/supervisor/addons`
- ✅ All add-on management operations now work correctly

**What was wrong:**
- All endpoints were missing the `/supervisor/` prefix
- Resulted in 403 Forbidden errors from Supervisor API
- Supervisor API requires: `http://supervisor/supervisor/{endpoint}`

**Fixed endpoints:**
- ✅ `supervisor/addons` (list all)
- ✅ `supervisor/addons/{slug}/info` (get info)
- ✅ `supervisor/addons/{slug}/logs` (get logs)
- ✅ `supervisor/addons/{slug}/install` (install)
- ✅ `supervisor/addons/{slug}/uninstall` (uninstall)
- ✅ `supervisor/addons/{slug}/start` (start)
- ✅ `supervisor/addons/{slug}/stop` (stop)
- ✅ `supervisor/addons/{slug}/restart` (restart)
- ✅ `supervisor/addons/{slug}/update` (update)
- ✅ `supervisor/addons/{slug}/options` (configure)
- ✅ `supervisor/store/repositories` (repositories)

**Impact:**
- All add-on management endpoints now return correct data instead of 403 errors
- Full add-on lifecycle management now functional ✅

## [2.3.3] - 2025-11-09

### 🐛 Critical Bug Fix

**Router Prefix Fix:**
- ✅ Fixed duplicate `/api/addons` prefix in `addons.py`
- ✅ Changed `router = APIRouter(prefix="/api/addons", ...)` to `router = APIRouter()`
- ✅ All add-on management endpoints now work correctly

**What was wrong:**
- Prefix was defined both in `addons.py` AND `main.py`
- URLs became `/api/addons/api/addons/installed` → 404
- Other routers (files, hacs) correctly use no prefix in router definition

**Impact:**
- Fixes all add-on management endpoints returning 404
- `/api/addons/installed` now correctly maps to `/api/addons/installed` ✅

## [2.3.2] - 2025-11-09

### 🔧 Build Fix

**Force Docker Rebuild:**
- ✅ Added version comment to `Dockerfile` to break Docker cache
- ✅ Ensures all new files (addons.py, supervisor_client.py) are included in build
- ✅ Fixes 404 error for add-on management endpoints

**Why this fix:**
- Home Assistant was using cached Docker image from v2.3.0
- New files weren't being copied into the container
- Cache-busting comment forces full rebuild

## [2.3.1] - 2025-11-09

### 🐛 Bug Fix

**Critical Import Fix:**
- ✅ Fixed ImportError in `app/api/addons.py`
- ✅ Changed `from app.models import Response` to `from app.models.schemas import Response`
- ✅ Agent now starts correctly

**Impact:**
- Fixes agent startup failure in v2.3.0
- All add-on management features now work correctly

## [2.3.0] - 2025-11-09

### 🚀 MAJOR: Complete Add-on Management (Phase 1.2) 🔥

**Full add-on lifecycle management** - Install, configure, and control Home Assistant add-ons!

### What's New

**Add-on Management:**
- ✅ List all available and installed add-ons
- ✅ Install/uninstall add-ons (Zigbee2MQTT, Node-RED, ESPHome, etc)
- ✅ Start/stop/restart add-ons
- ✅ Configure add-on options
- ✅ Update add-ons to latest versions
- ✅ Read add-on logs for troubleshooting
- ✅ Powered by Supervisor API

**12 New API Endpoints:**
- `GET /api/addons/available` - List all add-ons
- `GET /api/addons/installed` - List installed add-ons
- `GET /api/addons/{slug}/info` - Get add-on details
- `GET /api/addons/{slug}/logs` - Get add-on logs
- `POST /api/addons/{slug}/install` - Install add-on
- `POST /api/addons/{slug}/uninstall` - Uninstall add-on
- `POST /api/addons/{slug}/start` - Start add-on
- `POST /api/addons/{slug}/stop` - Stop add-on
- `POST /api/addons/{slug}/restart` - Restart add-on
- `POST /api/addons/{slug}/update` - Update add-on
- `GET /api/addons/{slug}/options` - Get configuration
- `POST /api/addons/{slug}/options` - Set configuration

**12 New MCP Tools:**
- `ha_list_addons` - List all add-ons
- `ha_list_installed_addons` - List installed only
- `ha_addon_info` - Get add-on details
- `ha_addon_logs` - Read logs
- `ha_install_addon` - Install add-on
- `ha_uninstall_addon` - Uninstall add-on
- `ha_start_addon` - Start service
- `ha_stop_addon` - Stop service
- `ha_restart_addon` - Restart service
- `ha_update_addon` - Update add-on
- `ha_get_addon_options` - Get configuration
- `ha_set_addon_options` - Set configuration

**AI Instructions:**
- ✅ Comprehensive add-on management guide
- ✅ Common add-on slugs (Mosquitto, Zigbee2MQTT, Node-RED)
- ✅ 3 detailed use cases with workflows
- ✅ Installation time expectations
- ✅ Troubleshooting guide

**Technical Implementation:**
- New `SupervisorClient` service (`app/services/supervisor_client.py`)
- Full Supervisor API integration
- Timeout handling for long operations (install/update)
- Error handling and user-friendly messages

### Use Cases Now Supported

**"Install Zigbee2MQTT for my Sonoff dongle"**
- Installs add-on (3-5 minutes)
- Auto-detects USB device
- Configures serial port
- Starts service
- Monitors logs
- Guides user to web UI

**"Setup complete smart home infrastructure"**
- Install Mosquitto MQTT broker
- Install Zigbee2MQTT
- Install Node-RED
- Configure integrations
- Start all services

**"My Zigbee2MQTT isn't working - help"**
- Check add-on state
- Read logs
- Identify issue
- Fix configuration
- Restart service
- Verify fix

### Roadmap Progress

- ✅ **Phase 1.1**: HACS Management (v2.2.0)
- ✅ **Phase 1.2**: Add-on Management (v2.3.0)  ← YOU ARE HERE
- 🔜 **Phase 1.3**: Enhanced Backup Management
- 🔜 **Phase 2.1**: Lovelace Dashboard Generator
- 🔜 **Phase 2.2**: Zigbee2MQTT Helper

**Impact:**
- Enables one-click infrastructure setup
- Simplifies Zigbee/MQTT configuration
- Automates add-on troubleshooting
- #2 most requested feature delivered!

## [2.2.3] - 2025-11-09

### 📝 Documentation Improvements

**HACS Setup Instructions**
- ✅ Fixed HACS post-installation instructions in AI Instructions
- ✅ Removed incorrect mention of automatic notification after HACS installation
- ✅ Added clear step-by-step guide: wait for restart → manually add HACS integration → configure GitHub token
- ✅ Clarified that user needs to go to Settings → Devices & Services → + ADD INTEGRATION → search for HACS

**README Enhancement**
- ✅ Added "📦 Extend with Community" section to main description
- ✅ Highlights HACS installation, search, and integration management
- ✅ Better visibility of community integrations feature

**Impact:**
- Accurate user guidance after HACS installation
- No confusion about non-existent notifications
- Clear manual integration setup process
- Better feature discoverability

## [2.2.2] - 2025-11-09

### 🧠 AI Instructions Enhancement

**Proactive HACS Installation**
- ✅ Added comprehensive HACS section to AI Instructions
- ✅ AI now proactively offers HACS installation when user requests custom integrations
- ✅ Clear workflow: Check status → Offer installation → Guide through setup
- ✅ Example scenarios and troubleshooting guide included

**Impact:**
- Better AI behavior - automatically suggests HACS when needed
- Improved user experience - no need to manually discover HACS
- Clear guidance on HACS installation and configuration flow

## [2.2.1] - 2025-11-09

### 🐛 Bug Fixes

**Critical Fix: Circular Import**
- ✅ Fixed `ImportError: cannot import name 'verify_token'` that prevented agent startup
- ✅ Moved authentication logic to separate `app/auth.py` module
- ✅ Resolved circular dependency between `app/main.py` and `app/api/hacs.py`

**Impact:**
- Agent now starts correctly without import errors
- No functional changes - all features work as before

## [2.2.0] - 2025-11-09

### 🚀 MAJOR: Full HACS Support with WebSocket

**Complete HACS Management** - Browse, search, and install 1000+ integrations!

### WebSocket Integration

Added **persistent WebSocket client** for real-time Home Assistant communication:
- ✅ Auto-authentication on startup
- ✅ Message routing with request/response matching
- ✅ Auto-reconnect with exponential backoff (1s → 60s max)
- ✅ Thread-safe operations
- ✅ Graceful shutdown handling
- ✅ Background task management

**Technical:**
- New `HAWebSocketClient` service (`app/services/ha_websocket.py`)
- Integrated into startup/shutdown lifecycle
- Enabled only in add-on mode (uses SUPERVISOR_TOKEN)

### Enhanced HACS API Endpoints

**All endpoints now use WebSocket for real-time data:**

- `POST /api/hacs/install` - Install HACS from GitHub (file operation)
- `GET /api/hacs/status` - Check installation and version
- `GET /api/hacs/repositories?category=integration` - List repositories via WebSocket ✨
- `GET /api/hacs/search?query=xiaomi&category=integration` - Search repositories ✨ NEW
- `POST /api/hacs/install_repository` - Install via hacs.download service ✨
- `POST /api/hacs/update_all` - Update all HACS repos ✨ NEW
- `GET /api/hacs/repository/{id}` - Get detailed repo info ✨ NEW

**Full workflow now works:**
```
User: "Install HACS and then install Xiaomi Gateway 3"
AI:
1. Installs HACS from GitHub ✅
2. Restarts Home Assistant ✅
3. Waits for WebSocket connection ✅
4. Searches for "Xiaomi Gateway 3" ✅
5. Installs via hacs.download service ✅
6. Guides through configuration ✅
```

**Features:**
- ✅ Browse all HACS repositories (integrations, themes, plugins)
- ✅ Search by name, author, description
- ✅ Install any repository with one command
- ✅ Update all repositories
- ✅ Get detailed repository info (stars, versions, authors)
- ✅ Category filtering (integration, theme, plugin, appdaemon, etc)

**Requirements:**
- HACS must be configured via UI first time (one-time setup)
- WebSocket requires SUPERVISOR_TOKEN (add-on mode)

## [2.1.0] - 2025-11-09

### ✨ NEW: HACS Support (Initial)

**One-Click HACS Installation** - AI can now install HACS!

Added initial HACS API:
- `POST /api/hacs/install` - Download and install HACS from GitHub
- `GET /api/hacs/status` - Check if HACS is installed

**Note:** v2.1.0 only supported installation. v2.2.0 adds full repository management.

## [2.0.1] - 2025-11-09

### Fixed
- **API endpoint naming** - added `/api/system/check-config` endpoint
  - MCP was calling `/check-config` (with dash)
  - Agent only had `/check_config` (with underscore)
  - Now supports both for compatibility
  - Fixes 404 Not Found error when checking configuration

## [2.0.0] - 2025-11-08

### 🚨 BREAKING CHANGES

- **Removed `HA_TOKEN` support** - only `HA_AGENT_KEY` is accepted now
  - Old configurations with `HA_TOKEN` will **STOP WORKING**
  - Must update to `HA_AGENT_KEY` in mcp.json
  - Cleaner API without legacy code

### Migration Required

**If you're using `HA_TOKEN`:**
```json
// OLD (will not work):
{
  "env": {
    "HA_TOKEN": "your-key"
  }
}

// NEW (required):
{
  "env": {
    "HA_AGENT_KEY": "your-key"
  }
}
```

**How to migrate:**
1. Update add-on to v2.0.0
2. Update MCP to v2.0.0
3. Change `HA_TOKEN` → `HA_AGENT_KEY` in your mcp.json
4. Restart Cursor

### Why This Change?

- ✅ Cleaner, more accurate naming
- ✅ No confusion with Home Assistant tokens
- ✅ Simpler codebase (no legacy support)
- ✅ Clear API semantics

## [1.0.18] - 2025-11-08

### Fixed
- **UI text consistency** - removed reference to manual file editing
  - Was: "Copy it to ~/.cursor/mcp.json"
  - Now: "Copy and paste it in Cursor Settings"
  - Aligned with Step 2 instructions (Settings → Tools & MCP)

## [1.0.17] - 2025-11-08

### Fixed
- **Documentation correction** - Ingress Panel access path
  - Correct: Settings → Add-ons → HA Cursor Agent → "Open Web UI"
  - Incorrect (removed): "Sidebar → 🔑 API Key" (this doesn't exist)
- **All documentation updated** with correct path to Web UI

## [1.0.16] - 2025-11-08

### Changed
- **Updated setup instructions** - now use Cursor Settings UI instead of manual file editing
  - Primary method: Settings → Tools & MCP → New MCP Server → Add Custom MCP Server
  - Manual file editing as alternative (for advanced users)
  - Clearer, more user-friendly workflow
  - Aligned with official Cursor MCP setup process

## [1.0.15] - 2025-11-08

### Fixed
- **Clipboard API error** - fixed "Cannot read properties of undefined (reading 'writeText')"
  - Added fallback to legacy `document.execCommand('copy')` method
  - Works in non-HTTPS contexts (Home Assistant Ingress)
  - Graceful error handling with manual copy instructions
  - Copy button now works reliably in all browsers

### Technical
- Implemented smart clipboard detection: tries modern API → falls back to legacy
- Better error messages if both methods fail

## [1.0.14] - 2025-11-08

### Changed
- **Consistent naming:** "API Key" → "Agent Key" throughout UI
  - Better alignment with `HA_AGENT_KEY` variable name
  - Clearer distinction from Home Assistant tokens
- **Simplified security info:** Removed technical details about SUPERVISOR_TOKEN
  - Less confusing for end users
  - Focused on what matters: "Agent Key authenticates you"

## [1.0.13] - 2025-11-08

### Improved
- **Copy button feedback** - better visual confirmation when copying
  - Button changes to "✅ Copied!" for 2 seconds
  - Button pulses on click
  - Center popup notification
  - Clear success/error states

### Fixed
- Copy button now has clear visual feedback (was not obvious before)

## [1.0.12] - 2025-11-08

### Changed
- **Improved Ingress Panel UX** - complete redesign focused on user workflow
  - **Primary focus:** Ready-to-use JSON configuration (copy entire config)
  - **One-click copy:** "Copy Configuration to Clipboard" button
  - **Clear steps:** Step-by-step instructions for Cursor setup
  - **Advanced section:** API key view/regenerate moved to collapsed section
  - **Better flow:** User copies JSON → pastes → restarts Cursor → done!

### Added
- New `ingress_panel.py` module for cleaner HTML template management
- Advanced section with key visibility toggle
- Regenerate key button (UI prepared, backend TBD)

### UX Improvements
- No need to manually construct JSON - it's ready to copy
- Masked key by default in advanced section
- Clear visual hierarchy (config first, key details later)

## [1.0.11] - 2025-11-08

### Changed
- **Renamed environment variable** - `HA_TOKEN` → `HA_AGENT_KEY` (more accurate naming)
- **Backward compatible** - agent still accepts old `HA_TOKEN` name
- **Updated all documentation** - shows `HA_AGENT_KEY` in examples
- **Updated Ingress Panel** - displays `HA_AGENT_KEY` in setup instructions
- **Updated MCP client** - accepts both `HA_AGENT_KEY` and `HA_TOKEN`

### Migration
- **Recommended:** Update `~/.cursor/mcp.json` to use `HA_AGENT_KEY` instead of `HA_TOKEN`
- **Optional:** Old `HA_TOKEN` still works for backward compatibility

## [1.0.10] - 2025-11-08

### Fixed
- **Notification logic** - moved into get_or_generate_api_key() function
- Removed problematic `@app.on_event("startup")` decorator
- Fixed async context for notification sending
- Application now starts correctly with notification feature enabled

## [1.0.9] - 2025-11-08

### 🔒 Security & UX Improvements

**Breaking Change:** API authentication changed from Home Assistant Long-Lived Token to dedicated API Key.

### Added
- **Dedicated API Key system** - separate from HA tokens
  - Auto-generates secure API key (32 bytes, cryptographically secure)
  - Optional: set custom API key in add-on configuration
  - Stored in `/config/.ha_cursor_agent_key`
- **Ingress Panel** - beautiful web UI in Home Assistant sidebar
  - Shows current API key (masked by default, click to reveal)
  - Copy to clipboard button
  - Step-by-step setup instructions
  - Direct links to documentation
- **Optional notifications** - get notified when API key is generated
  - Configurable in add-on settings

### Changed
- **Authentication simplified** - no need to create HA Long-Lived Token
- **Ingress enabled** - panel appears in sidebar as "API Key"
- **Panel icon** changed to `mdi:key-variant`
- Agent now uses dedicated API key instead of user's HA token
- Agent still uses SUPERVISOR_TOKEN internally for HA API operations

### Security
- ✅ No more transmitting HA Long-Lived Token over network
- ✅ API key is independent from HA authentication
- ✅ Can regenerate key without affecting HA access
- ✅ Simpler security model

### Migration
If upgrading from v1.0.8 or earlier:
1. Update add-on to v1.0.9
2. Open Sidebar → API Key (new panel will appear)
3. Copy your new API key
4. Update `~/.cursor/mcp.json` with new key
5. Restart Cursor

Old HA tokens will no longer work (this is intentional for security).

## [1.0.8] - 2025-11-08

### Added
- **CLIMATE_CONTROL_BEST_PRACTICES.md** - Comprehensive guide with 10+ real-world edge cases
  - TRV state changes during cooldown (with solution)
  - Sensor update delay after state changes (10 second rule)
  - Minimum boiler runtime protection (buffer radiators)
  - Predictive shutdown timing (0.3°C threshold)
  - Adaptive cooldown duration based on runtime
  - Multiple trigger automations for reliability
  - State tracking with input helpers
  - Buffer radiators coordination
  - System enable/disable transitions
  - Periodic check as safety net
- **Climate Control section in AI Instructions:**
  - Mandatory checklist for TRV/boiler automations
  - Critical edge cases to handle
  - Required sensors and helpers
  - Core automations (Priority 1, 2, 3)
  - Timing guidelines
  - Common mistakes to avoid
  - Testing checklist

### Documentation
- Added comprehensive climate control best practices based on production testing
- Real-world performance data (7+ days continuous operation)
- Architecture patterns for state-based automations
- Golden rules for reliable automation
- Lessons applicable to ANY state-based automation system

### Impact
- AI agents will now implement climate control with proven edge case handling
- Prevents common failures (stuck states, missed triggers, short-cycling)
- Saves debugging time by implementing solutions from day one
- Applicable to other automation systems beyond climate control

## [1.0.7] - 2025-11-08

### Changed
- **AI-controlled reload workflow:** Files API no longer auto-reloads after writes
  - Safer: AI must explicitly check config validity before reload
  - Faster: Batch multiple changes → single reload at the end
  - More control: AI decides when to reload based on change scope

### Added
- **Comprehensive modification workflow in AI Instructions:**
  - 6-step process: Backup → Write → Check → Reload → Verify → Commit
  - Configuration validation before reload (prevents broken HA state)
  - Rollback guidance if validation fails
  - Example workflows for common scenarios

### Fixed
- **Safety improvement:** Removed automatic reload that could apply invalid configurations
- **Performance:** No more multiple reloads when making batch changes

## [1.0.6] - 2025-11-08

### Changed
- **Updated documentation for MCP integration** - New recommended way to connect Cursor AI
- Added link to [@coolver/mcp-home-assistant](https://www.npmjs.com/package/@coolver/mcp-home-assistant) NPM package
- Simplified connection instructions using Model Context Protocol
- Updated README with MCP badge and links

### Documentation
- Replaced old prompt-based connection method with MCP configuration
- Added step-by-step MCP setup guide
- Added examples of natural language usage with MCP

## [1.0.5] - 2025-11-08

### Added
- **GET /api/helpers/list** endpoint to list all input helpers
- Better agent logs support with level filtering (DEBUG, INFO, WARNING, ERROR)

### Changed
- Improved MCP client logs handling with proper parameter names (limit, level)
- Updated tool descriptions for better clarity

## [1.0.4] - 2025-11-08

### Fixed
- **Token validation in add-on mode:** Fixed "Invalid token" errors when using Long-Lived Access Tokens
- Agent no longer tries to validate user tokens through supervisor URL (which doesn't accept them)
- In add-on mode, agent simply checks that a token is provided and uses SUPERVISOR_TOKEN for HA API operations

### Changed
- Simplified token validation logic for better reliability
- Improved token validation logging

## [1.0.3] - 2025-11-08

### Added
- **Enhanced debugging:** Detailed logging for token configuration at startup
- **Token validation logging:** Logs token validation attempts with response details
- **HA API request logging:** Logs all HA API requests with token preview
- **HAClient initialization logging:** Shows which token source is being used
- **Success/failure indicators:** Visual ✅/❌ indicators in logs

### Changed
- Version bumped to 1.0.3
- Improved error messages with token context for easier debugging

### Fixed
- Made "Invalid token" errors much easier to diagnose with detailed logging
- Added visibility into SUPERVISOR_TOKEN vs DEV_TOKEN usage

## [1.0.1] - 2024-11-07

### Fixed
- Fixed Docker base images to use correct Python 3.12-alpine3.20 versions
- Now builds successfully on Raspberry Pi (aarch64, armv7) and all other architectures
- Resolved "base image not found" error during add-on installation

### Added
- Cursor AI integration guide in README with ready-to-use prompt templates
- Example use cases for autonomous Home Assistant management
- Proper Cursor branding icons (icon.png, logo.png)

### Changed
- Removed unnecessary GitHub Actions builder workflow  
- Cleaned up documentation (removed redundant files)
- Integrated Quick Start guide directly into README
- Updated to multi-architecture support with build.json

## [1.0.0] - 2024-11-07

### Added
- Initial release of HA Cursor Agent
- FastAPI REST API with 29 endpoints
- File management (read/write/list/append/delete)
- Home Assistant integration (entities, services, reloads)
- Component management (helpers, automations, scripts)
- Git versioning with automatic backups
- Rollback functionality
- Agent logs API
- Health check endpoint
- Swagger UI documentation (`/docs`)
- Multi-architecture Docker support
- Home Assistant Add-on configuration

### Features
- **Files API**: Manage configuration files
- **Entities API**: Query devices and entities
- **Helpers API**: Create/delete input helpers
- **Automations API**: Manage automations
- **Scripts API**: Manage scripts
- **System API**: Reload components, check config
- **Backup API**: Git commit, history, rollback
- **Logs API**: Agent operation logs

### Documentation
- README with installation guide
- DOCS with full API reference
- INSTALLATION guide
- Quick Start guide
- Changelog
