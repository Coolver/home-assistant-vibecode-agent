# Changelog

All notable changes to this project will be documented in this file.

## [2.10.10] - 2026-01-20

### ✨ LLM-friendly entity listing & YAML safety checks

**Safer, more efficient workflows for large installations and YAML edits**

- ✅ **Token-efficient entity listing**: `/api/entities/list` now supports pagination (`page`, `page_size=250`) and lightweight modes so AI tools never have to dump thousands of full entity states at once
- ✅ **IDs-only & summary modes**: New `ids_only=true` returns just a list of `entity_id` strings, and `summary_only=true` returns compact objects (`entity_id`, `state`, `domain`, `friendly_name`) — ideal for discovering what exists without overloading model context
- ✅ **YAML syntax validation on write/append**: All writes to `*.yaml`/`*.yml` via `/api/files/write` and `/api/files/append` are now validated with `yaml.safe_load` before saving, preventing broken YAML from ever hitting `/config`
- ✅ **Duplicate automation ID protection**: For `automations.yaml`, the agent now detects duplicate `id` values when writing/appending and rejects the change with a clear error message, helping avoid subtle HA behaviour caused by duplicated automations

## [2.10.9] - 2026-01-20

### ✨ Token‑efficient access to scripts and automations

**Focused YAML access to save tokens and speed up AI workflows**

- ✅ **Lightweight listing endpoints**: Added support for listing script IDs and automation IDs without returning full YAML bodies, so AI tools can cheaply discover what exists before deciding what to open
- ✅ **Single‑entity configuration fetch**: New read‑only endpoints return configuration for a single script or automation by its ID, instead of loading entire `scripts.yaml` / `automations.yaml`
- ✅ **Token and context savings**: Designed specifically to reduce prompt/context size and token usage when working with large YAML files, especially in conversational AI scenarios
- ✅ **Faster request handling**: By focusing responses on the one script/automation you are currently working with, the agent can answer faster and IDEs can keep conversations narrow and relevant

## [2.10.8] - 2025-12-18

### 🔧 Git Versioning: Auto/Manual Mode & Shadow Repository

**New Git Versioning Mode:**
- ✅ **Replaced `auto_backup` with `git_versioning_auto`**: More descriptive configuration option
- ✅ **Automatic mode (`git_versioning_auto=true`)**: Commits happen automatically after each operation (default behavior)
- ✅ **Manual mode (`git_versioning_auto=false`)**: Changes are synced to shadow repo but not committed until user explicitly requests via `/api/backup/commit`

**Enhanced Commit API:**
- ✅ **Smart commit endpoint**: `/api/backup/commit` now supports:
  - With `message`: Commits immediately
  - Without `message` in manual mode: Returns suggested commit message (does not commit)
  - AI can show suggestion to user, allow editing, then commit with final message
- ✅ **New `/api/backup/pending` endpoint**: Get information about uncommitted changes (files modified/added/deleted, summary, diff)
- ✅ **Commit message generation**: Automatic generation of commit messages based on file changes (automations, scripts, dashboards, themes, etc.)

**Shadow Repository Architecture:**
- ✅ **Isolated Git operations**: All Git operations now happen in `/config/ha_vibecode_git` shadow repository
- ✅ **No interference with user's Git**: Agent never touches `/config/.git`, preserving user's GitHub remotes and history
- ✅ **Bidirectional sync**: Changes sync from `/config` to shadow repo before commits, and from shadow repo back to `/config` during rollback/restore

**Critical Operations Always Commit:**
- ✅ **Rollback**: Always commits "Before rollback" state (force=True)
- ✅ **Cleanup**: Always commits "Pre-cleanup" state (force=True)
- ✅ **Checkpoint**: Always commits checkpoint state (force=True)

**Updated Files:**
- `config.yaml`: `auto_backup` → `git_versioning_auto`
- `run.sh`: Updated environment variables
- `GitManager`: New `git_versioning_auto` logic, `get_pending_changes()`, `_generate_commit_message_from_changes()`
- All API endpoints: Updated to use `git_versioning_auto` instead of `auto_backup`

## [2.10.7] - 2025-12-18

### 🐛 HACS Repositories Access Fix & Improvements

**Fixed HACS repositories list functionality for HACS 2.0+**

- ✅ **Fixed repository listing**: Changed from reading `sensor.hacs_*` entities (not available in HACS 2.0) to reading `/config/.storage/hacs.repositories` file directly
- ✅ **Corrected data structure parsing**: Fixed parsing to read repositories from `data` object directly (not `data.repositories`)
- ✅ **Fixed field mappings**: Corrected field names to match HACS storage format:
  - `version_installed` instead of `installed_version`
  - `stargazers_count` instead of `stars`
- ✅ **Enhanced repository information**: Now extracts full repository details including name, category, versions, stars, downloads, and descriptions

**Improved installation and update functions:**

- ✅ **Installation verification**: Added automatic verification by checking storage file after repository installation
- ✅ **Version tracking**: Added tracking of repository versions before `update_all` operation for comparison
- ✅ **Enhanced logging**: Improved logging for better diagnostics (verification status, repository counts, WebSocket results)
- ✅ **Detailed API responses**: Functions now return detailed status information including:
  - Installation verification status
  - List of repositories with versions before update
  - WebSocket service call results
  - Next steps guidance

**Technical improvements:**

- ✅ **Better error handling**: Graceful handling of JSON parsing errors and missing storage files
- ✅ **Fallback mechanisms**: Added fallback to alternative data structures if primary structure not found
- ✅ **Comprehensive logging**: Added debug and info logs throughout the process for troubleshooting

## [2.10.5] - 2025-12-09

### ✨ Registry Management & Dead Entity Detection

**New Features:**

- ✅ **Dead Entity Detection**: New `/api/registries/entities/dead` endpoint finds automations and scripts that exist in Entity Registry but are missing from YAML files
  
- ✅ **Automatic Registry Cleanup**: When deleting automations or scripts via API, corresponding Entity Registry entries are automatically removed

- ✅ **Area Registry Operations**: Full support for creating, updating, and deleting areas via API

- ✅ **Device Registry Operations**: Full support for removing devices from Device Registry via API

**Registry API Coverage:**
- Entity Registry: list, get, update, remove
- Area Registry: list, get, create, update, delete
- Device Registry: list, get, update, remove
- Dead Entity Detection: compare registry with YAML files

## [2.10.4] - 2025-12-06

### ✨ Redesigned Git Versioning & Backup System

**Automatic backup system with AI-powered change descriptions**

The built-in Git versioning and backup system has been completely redesigned. Now, every time you modify scripts, dashboards, and configuration files, the agent automatically saves changes to the onboard Git repository and allows you to easily rollback to any previous version.

**Key improvements:**
- ✅ **AI-generated change descriptions**: The agent now uses AI to create meaningful descriptions of what changed and why (e.g., "Add automation: Control lights when motion detected")
- ✅ **Easy change history**: You can ask AI to show a list of recent changes and quickly find what you need
- ✅ **Smart rollback**: Simply describe what you want to rollback to (e.g., "rollback to when I added the motion sensor automation") and AI will find and restore it

**Bug fix:**
- ✅ **Fixed backup size issue**: Previously, large database or media files could accidentally be included in Git backups, causing rapid repository growth. Now only configuration files, scripts, automations, and dashboards are tracked in Git, keeping backups small and efficient.

## [2.10.1] - 2025-12-06

### 🐛 CRITICAL BUGFIX: Git Backup Size Issue

**Fixed massive backup size increase caused by Git repository including large files**

- ✅ **Automatic `.gitignore` creation**: Git repository now automatically creates `.gitignore` file in `/config` directory to exclude large files
- ✅ **Excluded large files from Git**: Database files (`.db`, `.db-shm`, `.db-wal`), logs, media files, and Home Assistant internal directories are now automatically excluded
- ✅ **Smart file tracking**: Only configuration files (YAML, JSON) are tracked in Git, preventing backup size bloat
- ✅ **Automatic cleanup of tracked files**: When `.gitignore` is created, already tracked large files are automatically removed from Git index (but kept on disk)
- ✅ **Backward compatibility**: Existing Git repositories are updated with `.gitignore` on next initialization

**What was fixed:**
- Previously, `git add -A` was adding ALL files from `/config`, including:
  - SQLite database files (can be several GB)
  - Log files
  - Media files (`/www/`, `/media/`)
  - Home Assistant internal storage (`.storage/`, `.homeassistant/`)
- This caused backup size to increase from ~1GB to 10-14GB after using the agent
- Now only configuration files are tracked, keeping backup size minimal

**Impact:**
- New installations: Problem completely resolved
- Existing installations: `.gitignore` will be created automatically, and already tracked large files will be removed from Git index, preventing future large files from being added
- Note: Existing Git history may still contain large files - consider cleaning Git history if needed (using `git filter-branch` or `git filter-repo`)

**Technical details:**
- `.gitignore` is automatically created/updated when Git repository is initialized
- Excludes: `*.db`, `*.log`, `/www/`, `/media/`, `/.storage/`, `/.homeassistant/`, and other large file patterns
- Git operations now respect `.gitignore`, ensuring only config files are versioned

## [2.10.0] - 2025-12-06

### 🎉 MAJOR: Multi-IDE Support & UI Redesign

**Expanded AI Assistant Support:**
- ✅ Added support for VS Code (including free tier) with GitHub Copilot
- ✅ Added support for any IDE that supports MCP (Model Context Protocol)
- ✅ Renamed from "HA Cursor Agent" to "HA Vibecode Agent" to reflect multi-IDE support
- ✅ Updated all documentation to reflect support for multiple AI assistants

**Web UI Improvements:**
- ✅ Redesigned settings interface with tab-based navigation
- ✅ Added dedicated setup instructions for VS Code + GitHub Copilot
- ✅ Added dedicated setup instructions for Cursor AI
- ✅ Replaced emoji icons with SVG icons for better cross-browser compatibility
- ✅ Improved key management with dedicated input field and copy/regenerate buttons
- ✅ Streamlined installation steps for better user experience

**Technical Changes:**
- ✅ Updated MCP configuration generation for both Cursor and VS Code
- ✅ Enhanced ingress panel with responsive tab switching
- ✅ Improved UI accessibility and browser compatibility

## [2.9.17] - 2025-11-23

### 🐛 BUGFIX: Indentation Error in Helpers Delete Function

- ✅ Fixed IndentationError in `app/api/helpers.py` delete helper function
- ✅ Corrected try-except block indentation
- ✅ Agent should now start correctly

## [2.9.16] - 2025-11-23

### ✨ NEW: Automatic Checkpoint System for Git Versioning

**Consistent checkpoint creation at the start of each user request**

- ✅ Added `create_checkpoint()` method to GitManager - creates commit with tag at request start
- ✅ Added `/api/backup/checkpoint` endpoint for creating checkpoints
- ✅ Added `ha_create_checkpoint` and `ha_end_checkpoint` MCP tools
- ✅ Disabled auto-commits during request processing (prevents micro-commits)
- ✅ Checkpoints include timestamp tag (e.g., `checkpoint_20251123_194530`)
- ✅ Updated all `commit_changes()` calls to skip during request processing
- ✅ Updated AI instructions to automatically create checkpoint at request start
- ✅ Updated MCP package version to 3.2.6

**How it works:**
1. At the start of each user request, `ha_create_checkpoint()` is called
2. Creates a commit with current state (if there are changes)
3. Creates a tag with timestamp and user request description
4. Disables auto-commits during request processing
5. All changes within the request are made without intermediate commits
6. At the end, `ha_end_checkpoint()` re-enables auto-commits

**Benefits:**
- Clean git history - one checkpoint per user request instead of many micro-commits
- Easy rollback - each checkpoint is tagged with timestamp and description
- Better organization - each user request is a logical unit in git history

**Example:**
```
User: "Create nice_dark theme"
→ ha_create_checkpoint("Create nice_dark theme")
→ Creates tag: checkpoint_20251123_194530
→ Makes all changes (no intermediate commits)
→ ha_end_checkpoint()
```

## [2.9.15] - 2025-11-23

### ✨ NEW: Theme Management API & MCP Tools

**Complete theme management functionality for Home Assistant**

- ✅ Added `/api/themes` endpoints: list, get, create, update, delete, reload, check_config
- ✅ Added theme management methods to HA client
- ✅ Added 7 MCP tools for theme management:
  - `ha_list_themes` - List all available themes
  - `ha_get_theme` - Get theme content and configuration
  - `ha_create_theme` - Create a new theme
  - `ha_update_theme` - Update an existing theme
  - `ha_delete_theme` - Delete a theme
  - `ha_reload_themes` - Reload themes in Home Assistant
  - `ha_check_theme_config` - Check if themes are configured
- ✅ Updated MCP package version to 3.2.5

**Use Cases:**
- Create custom themes with CSS variables
- Manage themes programmatically via AI
- Check theme configuration status
- Reload themes without restarting HA

**Example:**
```yaml
nice_dark:
  primary-color: "#ffb74d"
  accent-color: "#ffb74d"
  primary-background-color: "#101018"
  card-background-color: "#181824"
  ha-card-border-radius: "18px"
  ...
```

## [2.9.14] - 2025-11-23

### 🐛 FIX: Entity Rename via WebSocket API

**Fixed 404 error when renaming entities**

- ✅ Changed entity rename from REST API to WebSocket API (`config/entity_registry/update`)
- ✅ Added support for optional `new_name` parameter to update friendly name
- ✅ Fixed "404 Not Found" error when renaming entities

**Technical Details:**
- Home Assistant Entity Registry updates must be done via WebSocket API, not REST
- REST endpoint `/api/config/entity_registry/update/{entity_id}` doesn't exist
- WebSocket command `config/entity_registry/update` is the correct method

## [2.9.13] - 2025-11-23

### ✨ NEW: Entity Rename Functionality

- ✅ Added `/api/entities/rename` endpoint to rename entity_id via Entity Registry API
- ✅ Added `renameEntity` method to HA client
- ✅ Added `ha_rename_entity` MCP tool for renaming entities through AI
- ✅ Updated MCP package version to 3.2.4

**Use Cases:**
- Rename entities to more descriptive names (e.g., `climate.sonoff_trvzb_thermostat` → `climate.office_trv_thermostat`)
- Standardize entity naming conventions across Home Assistant
- Automate entity renaming workflows

## [2.9.12] - 2025-11-21

### ✨ NEW: Logbook API & MCP Tool

- ✅ Added `/api/logbook` endpoint with rich filtering (time window, domains, entities, event types, search)
- ✅ Added summary statistics for scripts/automations to quickly inspect recent runs
- ✅ Updated MCP client, handlers, and tool schema with `ha_logbook_entries`
- ✅ Documented new capability and expanded HA agent test suite to cover logbook operations

## [2.9.11] - 2025-11-18

### 🐛 FIX: Entity Registry Result Format Handling

**Handle both wrapped and direct entity registry result formats**

**Changes:**
- ✅ Fixed parsing of entity registry result - API can return data directly or wrapped in `{'result': ...}`
- ✅ Code now handles both formats correctly
- ✅ Allows deletion to proceed for all helpers

**Technical Details:**
- WebSocket API `config/entity_registry/get` can return data in two formats:
  - Wrapped: `{'result': {...}}`
  - Direct: `{...}`
- Code now checks for both formats and extracts entry data correctly

## [2.9.10] - 2025-11-18

### 🐛 FIX: Syntax Error in Entity Registry Deletion

**Fixed try-except block indentation**

**Changes:**
- ✅ Fixed syntax error: `except` block was incorrectly nested inside `if state:` block
- ✅ Moved `except` to correct level to match `try` block
- ✅ Code now compiles correctly

## [2.9.9] - 2025-11-18

### 🔧 IMPROVED: Comprehensive Helper Deletion Strategy

**Delete helpers from all possible locations: YAML, config entry, and entity registry**

**Changes:**
- ✅ Always check and delete from YAML first (if helper exists there)
- ✅ Then try config entry deletion (for storage helpers)
- ✅ Then try entity registry deletion via WebSocket (even if YAML deletion succeeded)
- ✅ This ensures we delete everywhere possible, including restored entities
- ✅ Better logging to show which methods were used

**Technical Details:**
- YAML deletion: removes from YAML file and reloads integration
- Config entry deletion: finds and deletes config entry for storage helpers
- Entity registry deletion: removes from entity registry via WebSocket (works for all helpers)
- For restored entities: deletion from entity registry may work temporarily even after YAML removal

## [2.9.8] - 2025-11-18

### 🔧 IMPROVED: WebSocket Deletion for All Helpers

**Attempt WebSocket deletion for all helpers, not just storage helpers**

**Changes:**
- ✅ Try entity registry removal via WebSocket for all helpers (YAML-managed and storage)
- ✅ YAML-managed helpers may be deleted temporarily (will restore on restart if still in YAML)
- ✅ Storage helpers will be permanently deleted
- ✅ Better logging to distinguish between YAML-managed and storage helpers
- ✅ Clear warnings when YAML-managed helpers are deleted (may restore)

**Technical Details:**
- Uses `config/entity_registry/remove` WebSocket API for all helpers
- YAML-managed helpers: deletion may work temporarily but will restore if still in YAML
- Storage helpers: permanent deletion via entity registry

## [2.9.7] - 2025-11-18

### 🔧 FIX: YAML-Managed Helper Deletion Detection

**Properly detect and handle YAML-managed helpers**

**Changes:**
- ✅ Check if helper is YAML-managed (config_entry_id = None in entity registry)
- ✅ Return clear error message for YAML-managed helpers (cannot be deleted via API)
- ✅ Only attempt entity registry deletion for storage helpers (created via UI)
- ✅ Better error messages explaining that YAML helpers must be removed from YAML files

**Technical Details:**
- YAML-managed helpers have `config_entry_id = None` in entity registry
- These helpers cannot be deleted via API - they must be removed from YAML and HA restarted
- Storage helpers (created via UI) can be deleted via `config/entity_registry/remove`

## [2.9.6] - 2025-11-18

### 🐛 DEBUG: Enhanced Entity Registry Deletion Logging

**Added detailed logging for entity registry deletion debugging**

**Changes:**
- ✅ Added debug logging for entity registry get/remove operations
- ✅ Better error messages with exception details
- ✅ Logs registry entry data and API responses

## [2.9.5] - 2025-11-18

### 🔧 IMPROVED: Helper Deletion for Restored Entities

**Added support for deleting restored helpers via entity registry**

**Changes:**
- ✅ Added entity registry deletion for restored entities
- ✅ Handles helpers with `restored: true` attribute
- ✅ Uses `config/entity_registry/remove` API for cleanup
- ✅ Supports deletion of helpers that were removed from config but still exist in database

**Use Cases:**
- Delete helpers that were removed from YAML but restored by Home Assistant
- Clean up orphaned entities from entity registry
- Complete cleanup of obsolete helpers

## [2.9.4] - 2025-11-18

### 🔧 IMPROVED: Helper Deletion Logic

**Enhanced config entry deletion with multiple matching strategies**

**Changes:**
- ✅ Improved config entry search with multiple matching strategies:
  - Match by title (common for UI-created helpers)
  - Match by entity_id in options
  - Match by entry details (deep search)
- ✅ Added debug logging for config entry search process
- ✅ Better error messages when helper exists but can't be deleted
- ✅ More robust handling of config-entry-based helpers

**Technical Details:**
- Uses `config/config_entries/get` API to get detailed entry information
- Tries multiple matching strategies before giving up
- Provides detailed logging for troubleshooting

## [2.9.3] - 2025-11-18

### 🔧 IMPROVED: Helper Deletion

**Enhanced helper deletion to support config entry helpers**

**Changes:**
- ✅ `DELETE /api/helpers/delete/{entity_id}` now attempts to delete helpers created via UI/API (config entries)
- ✅ First tries YAML deletion (if helper exists in YAML)
- ✅ Then tries config entry deletion (if helper was created via UI/API)
- ✅ Better error messages when helper cannot be deleted automatically

**Use Cases:**
- Delete helpers created via `ha_create_helper` MCP tool
- Delete helpers created manually via Home Assistant UI
- Clean up obsolete helpers from configuration

## [2.9.2] - 2025-11-18

### ✨ NEW: Service Call API Endpoint

**Added API endpoint for calling Home Assistant services**

**New Endpoint:**
- `POST /api/entities/call_service` - Call any Home Assistant service

**Features:**
- ✅ Call any Home Assistant service via REST API
- ✅ Support for service_data and target parameters
- ✅ Proper parameter merging (target fields merged into service_data)
- ✅ Full error handling and logging

**Parameters:**
- `domain` (required) - Service domain (e.g., "number", "light", "climate")
- `service` (required) - Service name (e.g., "set_value", "turn_on", "set_temperature")
- `service_data` (optional) - Service-specific data
- `target` (optional) - Target entity/entities

**Examples:**
```json
// Set number value
{
  "domain": "number",
  "service": "set_value",
  "service_data": {
    "entity_id": "number.alex_trv_local_temperature_offset",
    "value": -2.0
  }
}

// Turn on light
{
  "domain": "light",
  "service": "turn_on",
  "target": {"entity_id": "light.living_room"}
}

// Set climate temperature
{
  "domain": "climate",
  "service": "set_temperature",
  "target": {"entity_id": "climate.bedroom_trv_thermostat"},
  "service_data": {"temperature": 21.0}
}
```

**Use Cases:**
- Configure device parameters (TRV offsets, limits, etc.)
- Control devices (lights, switches, climate)
- Update helper values
- Any Home Assistant service call

**Integration:**
- Used by MCP tool `ha_call_service`
- Enables AI to call services directly
- Full integration with existing ha_client.call_service method

## [2.9.1] - 2025-11-11

### 🐛 FIX: Separate YAML files for each helper type

**Problem in v2.9.0:**
- All helper domains (input_boolean, input_text, etc.) referenced same file `helpers.yaml`
- This caused conflicts - each domain tried to load entire file
- Helpers not appearing after reload

**Solution:**
- Each domain now has its own file:
  - `input_boolean.yaml`
  - `input_text.yaml`
  - `input_number.yaml`
  - `input_datetime.yaml`
  - `input_select.yaml`
- Clean configuration.yaml references:
  ```yaml
  input_boolean: !include input_boolean.yaml
  input_text: !include input_text.yaml
  # ... etc
  ```

**Now helpers ACTUALLY work!** 🎉

## [2.9.0] - 2025-11-11

### 🎉 MAJOR: Helper Creation via YAML Now Works!

**Breaking Discovery:** Helpers CAN be created via API using YAML + reload method!

**Implementation:**
- ✅ Write helper config to `helpers.yaml`
- ✅ Automatically include `helpers.yaml` in `configuration.yaml`
- ✅ Call `input_*.reload` service to apply changes
- ✅ Helper appears immediately without HA restart

**New Method:**
```python
# 1. Add to helpers.yaml:
input_boolean:
  my_switch:
    name: "My Switch"
    icon: "mdi:toggle-switch"

# 2. Reload integration:
await ws_client.call_service('input_boolean', 'reload', {})

# 3. Helper is now available!
```

**API Changes:**
- ✅ `POST /api/helpers/create` - NOW WORKS via YAML method
- ✅ `DELETE /api/helpers/delete/{entity_id}` - NOW WORKS via YAML method
- ✅ Automatic entity_id generation from name
- ✅ Git commits for all helper changes
- ✅ Validation and error handling

**What Changed:**
- Moved from `.storage/` approach (doesn't work) to YAML approach (works!)
- Helpers created via API are now YAML-based (editable in UI and files)
- Full CRUD support for all helper types

**Credit:** Solution discovered via Home Assistant Community forums

## [2.7.7] - 2025-11-11

### 🚨 Critical: Added Explicit Ban on `attribute:` in Conditional Cards

**MAJOR UPDATE: Found and fixed critical mistake pattern in AI instructions**

**The Problem:**
AI was generating invalid conditional cards with `attribute:` key:
```yaml
# ❌ This was being generated (DOES NOT WORK!)
type: conditional
conditions:
  - entity: climate.office_trv
    attribute: hvac_action    # ← Lovelace does NOT support this!
    state: heating
```

**Root Cause:**
- Lovelace conditional cards do NOT support `attribute:` key
- Home Assistant automations DO support `attribute:` (confusion!)
- AI instructions didn't explicitly forbid this pattern

**What Was Added:**

1. **🚨 CRITICAL warning section** at document start
2. **Expanded Mistake #4** with multiple wrong examples
3. **Updated Golden Rules** - moved `attribute:` ban to #1
4. **Explanation of automation vs dashboard syntax difference**

**New Structure:**
```yaml
# ✅ CORRECT - Use template sensor
template:
  - sensor:
      - name: "Office TRV HVAC Action"
        state: "{{ state_attr('climate.xxx', 'hvac_action') }}"

# Then in dashboard:
conditions:
  - condition: state
    entity: sensor.office_trv_hvac_action
    state: heating
```

**Impact:**
- AI will never use `attribute:` in Lovelace conditionals
- Clear explanation why (automation vs dashboard difference)
- Template sensor pattern shown as solution
- Fixed actual broken dashboard in Home Assistant (commit 3bee434b)

**Files Updated:**
- `06_conditional_cards.md` - Added explicit ban and examples
- Home Assistant `heating-now.yaml` - Fixed all 7 TRV conditionals

**Version:** 2.7.7 (PATCH - critical documentation fix)

## [2.7.6] - 2025-11-11

### 🐛 Fix: Conditional Cards Guide - Corrected Structure

**Fixed incorrect conditional card patterns in AI instructions**

**What was wrong in v2.7.5:**
```yaml
# ❌ WRONG - Missing "condition: state"
type: conditional
conditions:
  - entity: climate.office_trv
    state: "heat"
```

**Corrected in v2.7.6:**
```yaml
# ✅ CORRECT - Must include "condition: state"
type: conditional
conditions:
  - condition: state
    entity: sensor.office_trv_hvac_action
    state: heating
```

**Key fixes:**
1. ✅ Added `condition: state` requirement (most common mistake!)
2. ✅ Corrected to use template sensors for hvac_action attributes
3. ✅ Fixed state value: `heating` not "heat"
4. ✅ Added `condition: numeric_state` for numeric comparisons
5. ✅ Updated all examples with correct structure
6. ✅ Based on actual working commit: e8ed8a3b

**Reference:** Commit e8ed8a3b - "Before deleting dashboard: heating-now.yaml" (the working version)

**Impact:**
- AI will now generate correct conditional cards
- Prevents common YAML structure mistakes
- Template sensors properly documented
- Real-world tested patterns

**Version:** 2.7.6 (PATCH - documentation fix)

## [2.7.5] - 2025-11-11

### 📚 Documentation: Conditional Cards Guide

**Comprehensive instructions for creating conditional cards in Lovelace dashboards**

**Added:**
- New AI instruction document: `06_conditional_cards.md`
- Complete guide based on successful "Heating Now Dashboard" implementation
- Real-world patterns for conditional TRV heating cards
- Common mistakes and how to avoid them
- Ready-to-use templates

**Guide Contents:**
- ✅ Correct YAML syntax for conditional cards
- ✅ Multiple condition patterns (AND logic)
- ✅ State checking (exact, not, above, below)
- ✅ Availability checks
- ✅ Debugging tips
- ✅ Copy-paste templates

**Use Cases:**
- Heating monitoring (show only active TRVs)
- Low battery alerts
- Active media players
- Motion detection
- Problem/warning cards

**Integration:**
- Auto-loaded in AI instructions via `/api/instructions`
- Cross-referenced from dashboard generation guide
- Prevents common conditional card mistakes

**Reference:** Based on commit `a16f9403` - Heating Now Dashboard with conditional TRV controls

**Version:** 2.7.5 (PATCH - documentation enhancement)

## [2.7.4] - 2025-11-10

### 🐛 Bug Fix: Git Rollback Endpoint

**Fixed 404 error when rolling back via MCP tools**

**Bug:**
- MCP calls: `POST /api/backup/rollback/{commit_hash}` (path param)
- API expected: `POST /api/backup/rollback` + body
- Result: 404 Not Found

**Fix:**
- Added path parameter endpoint: `/rollback/{commit_hash}`
- Kept body parameter endpoint for compatibility
- Both versions now work

**API Endpoints:**
```
✅ POST /api/backup/rollback/abc123 (path param - for MCP)
✅ POST /api/backup/rollback + body (legacy - for direct API calls)
```

**Impact:**
- ✅ Git rollback works from AI
- ✅ Can restore previous configurations
- ✅ Both calling styles supported

**Version:** 2.7.4 (PATCH - bug fix)

## [2.7.3] - 2025-11-10

### ✨ Feature: Dashboard Validation + Detailed Errors

**Comprehensive dashboard validation and better error reporting!**

**Part 1: Dashboard Filename Validation**
- Validates filename contains hyphen (HA requirement)
- Checks for spaces, uppercase
- Returns helpful suggestions
- Prevents common mistakes

**Validation Rules:**
```
❌ BAD:  "heating", "stat", "climate" (no hyphen)
✅ GOOD: "heating-now", "climate-control"

Auto-suggestions:
"stat" → "stat-dashboard"
"Heating Now" → "heating-now" (kebab-case)
```

**Part 2: Pre-Creation Checks**
- AI checks if dashboard already exists
- Warns before overwriting
- Validates filename before backup (fail fast)

**Part 3: Detailed Configuration Errors**
- check_config returns detailed errors like Developer Tools
- Shows line numbers and specific issues
- Extracts error messages from HA API
- Much better debugging

**AI Instructions Updated:**
- Added STEP 0: Pre-Creation Checks (mandatory)
- Dashboard name validation rules
- Examples and auto-conversion logic

**Before:**
```
Error: "Configuration has errors: 500 Server Error"
```

**After:**
```
Error: "Configuration invalid!

Invalid config for 'lovelace' at configuration.yaml, line 342: 
Url path needs to contain a hyphen (-) for dictionary value..."
```

**Impact:**
- ✅ Prevents invalid dashboard names
- ✅ Better error messages for debugging
- ✅ AI can understand and fix issues
- ✅ Fewer failed dashboard creations

**Version:** 2.7.3 (PATCH - validation improvements)

## [2.7.2] - 2025-11-10

### 🐛 Bug Fix: File List Root Directory

**Fixed 500 error when listing files with directory='/'**

**Bug:**
- `ha_list_files` with directory="/" failed
- Error: "Path outside config directory: /"
- AI couldn't browse config directory

**Root Cause:**
- _get_full_path() treated "/" as absolute path
- Security check failed

**Fix:**
- Handle "/" and "" as root config directory
- Strip leading slashes from paths
- Return config_path directly for root

**Impact:**
- ✅ AI can now browse config directory
- ✅ ha_list_files works correctly
- ✅ Security still enforced

**Version:** 2.7.2 (PATCH - bug fix)

## [2.7.1] - 2025-11-10

### 🎨 UI/UX: Ingress Panel Improvements

**Improved Ingress Panel usability:**

**Changes:**
- Security warning moved to Step 1 (more visible)
- Removed duplicate "Additional Info" section
- Removed redundant Advanced key visibility toggle
- Cleaned up unused CSS and JavaScript
- Simplified UI - only essential elements

**Code Cleanup:**
- Removed unused CSS: .advanced, .key-display, .btn-secondary, .chevron
- Removed unused JS: toggleAdvanced(), toggleKeyVisibility()
- Removed unused variables: masked_key, keyVisible
- Template simplified: 3 variables instead of 4

**CHANGELOG:**
- Fixed duplicate v2.7.0 entry
- Combined refactor notes properly

**Result:**
- Cleaner, simpler UI
- Better security notice placement
- Less code, same functionality

**Version:** 2.7.1 (PATCH - UI improvements)

## [2.7.0] - 2025-11-10

### 🏗️ MAJOR REFACTOR: Architecture Improvements

**Two major internal refactors for better maintainability!**

#### Part 1: AI Instructions → Markdown Files

**Before:**
- ai_instructions.py: 1295 lines (giant Python string)
- Hard to edit, no syntax highlighting

**After:**
- ai_instructions.py: 34 lines (loader only!)
- 7 modular Markdown files by topic
- Dynamic loader combines files

**Structure:**
```
app/ai_instructions/
├── __init__.py (loader)
└── docs/
    ├── 00_overview.md
    ├── 01_explain_before_executing.md
    ├── 02_output_formatting.md
    ├── 03_critical_safety.md
    ├── 04_dashboard_generation.md
    ├── 05_api_summary.md
    └── 99_final_reminder.md
```

**Benefits:**
- ✅ Markdown (easy editing, GitHub preview, syntax highlighting)
- ✅ Modular (update sections independently)
- ✅ Version dynamically injected
- ✅ 97% code reduction

#### Part 2: Ingress Panel → Jinja2 Template

**Before:**
- ingress_panel.py: 715 lines (HTML in Python string)
- Hard to edit HTML, no syntax highlighting

**After:**
- ingress_panel.py: 52 lines (clean loader)
- app/templates/ingress_panel.html: Jinja2 template
- requirements.txt: added jinja2

**Benefits:**
- ✅ HTML syntax highlighting
- ✅ Separation of concerns (logic vs presentation)
- ✅ Easy UI editing
- ✅ 93% code reduction in Python

#### Summary

**Git Stats:**
- ai_instructions.py: 1295 → 34 lines (-97%)
- ingress_panel.py: 715 → 52 lines (-93%)
- Total: ~2200 lines cleaned up
- Better code organization, same functionality

**Version:** 2.7.0 (MINOR - internal refactor, API unchanged)

## [2.6.1] - 2025-11-10

### 📚 Documentation: Complete Reference Update

**Updated all remaining old package references:**
- app/main.py: old ingress panel package name
- app/ingress_panel.py: NPM package link
- CHANGELOG.md: complete history for v2.5.x-2.6.x

**Version:** 2.6.1

## [2.6.0] - 2025-11-10

### 📦 BREAKING: MCP Package Renamed

**MCP package renamed for consistency with GitHub repository!**

**Old:** `@coolver/mcp-home-assistant`  
**New:** `@coolver/home-assistant-mcp`

**Migration Required:**
Users must update `~/.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "home-assistant": {
      "command": "npx",
      "args": ["-y", "@coolver/home-assistant-mcp@latest"],
      ...
    }
  }
}
```

**Changes:**
- app/ingress_panel.py: updated npx command to new package
- app/main.py: updated all package references
- README.md: updated NPM badge and links
- CHANGELOG.md: updated historical links

**Why:**
- Consistency with GitHub repo (home-assistant-mcp)
- Development stage (no existing users affected)
- Clearer naming convention

**MCP Package Changes (v3.0.x):**
- Package name: @coolver/mcp-home-assistant → @coolver/home-assistant-mcp
- SDK upgraded: 0.5.0 → 1.21.1 (API compatibility)
- Repository: github.com/Coolver/home-assistant-mcp
- All documentation updated

## [2.5.4] - 2025-11-10

### 🐛 Bug Fix: API Key Regeneration

**Fixed 404 error when regenerating API key via ingress panel:**
- Fixed: fetch('/api/regenerate-key') → fetch('api/regenerate-key')
- Relative URL works through ingress proxy correctly
- Improved JavaScript error handling

## [2.5.3] - 2025-11-10

### ✨ Feature: API Key Regeneration Button

**Added working "Regenerate Key" button in UI:**
- Button placed next to "Copy Configuration"
- POST /api/regenerate-key endpoint
- One-click key regeneration
- Auto-updates config display with new key
- Alerts user to update Cursor

## [2.5.2] - 2025-11-10

### 📖 Documentation: Communication Guidelines

**Added AI communication guidelines:**
- "Explain Before Executing" section
- AI explains plan before calling tools
- Better transparency and user understanding
- Exception for simple read-only checks

## [2.5.1] - 2025-11-10

### 📖 Documentation: Output Formatting

**Added output formatting guidelines for AI:**
- Format MCP tool output for readability
- Don't show raw JSON to users
- Use emojis and tables for clarity
- Show key information, hide implementation details

## [2.4.7] - 2025-11-09

### 🛠️ Improvements: YAMLEditor Utility + Error Handling

**Lessons learned - proper tooling:**
- ✅ Added YAMLEditor utility for safe YAML operations
- ✅ Added auto-rollback function for error recovery
- ✅ Improved empty section cleanup

**New utilities:**
- YAMLEditor.remove_lines_from_end()
- YAMLEditor.remove_empty_yaml_section()
- YAMLEditor.remove_yaml_entry()
- _rollback_on_error() for automatic Git rollback

## [2.4.6] - 2025-11-09

### 🐛 Bug Fix: Empty Section Cleanup

**Fixed invalid YAML after dashboard deletion:**
- Deleting last dashboard left empty lovelace: section
- HA validation failed: "expected dictionary, got None"
- Now removes empty sections automatically

## [2.4.5] - 2025-11-09

### 🗑️ Feature: Dashboard Deletion + Restart Fix

**Added dashboard deletion endpoint:**
- DELETE /api/lovelace/delete/{filename}
- Removes file + configuration entry
- Full HA restart after deletion

**Fixed restart warning:**
- Changed reload_config() → restart() (full restart needed)

## [2.4.4] - 2025-11-09

### 🐛 Bug Fix: Handle !include Directives

**Fixed configuration.yaml parsing:**
- yaml.safe_load() failed on !include directives
- Now processes as text to preserve HA directives
- Uses regex for insertion

## [2.4.3] - 2025-11-09

### 🐛 Bug Fix: Async File Operations

**Fixed async/await in lovelace.py:**
- Added await for file_manager.read_file()
- Added await for file_manager.write_file()
- Fixed GitManager.commit_changes() calls

## [2.4.2] - 2025-11-09

### 🎯 Feature: Auto-Registration

**Dashboards automatically register in configuration.yaml:**
- No manual UI steps needed
- Auto-restart after registration
- Dashboard appears in sidebar instantly

## [2.4.1] - 2025-11-09

### 🐛 Bug Fix: Async File Operations

**Fixed async/await in dashboard preview and apply.**

## [2.4.0] - 2025-11-09

### 🎨 MAJOR: Lovelace Dashboard Generator (Phase 2.1)

**Automatic dashboard generation from your entities!** (#3 most requested feature, 85/100 priority)

**New Service: LovelaceGenerator**
- Analyzes entities by domain, area, and type
- Generates beautiful views automatically
- Smart grouping and recommendations
- Supports 3 styles: modern, classic, minimal
- Material Design patterns

**New API Endpoints (4):**
- `GET /api/lovelace/analyze` - Analyze entities & recommendations
- `POST /api/lovelace/generate` - Generate complete dashboard config
- `GET /api/lovelace/preview` - Preview current dashboard
- `POST /api/lovelace/apply` - Apply dashboard with Git backup

**Auto-generated Views:**
- 🏠 Home: Weather + People + Quick controls
- 💡 Lights: All lights (if >3 lights detected)
- 🌡️ Climate: Thermostats/TRVs with thermostat cards
- 🎵 Media: Media players with media-control cards
- 📊 Sensors: Grouped by device_class
- 🤖 Automation: Automations + Scripts management

**Features:**
- Smart room detection (from friendly_name)
- Multi-language support (English, Russian)
- Automatic card type selection
- Git backup before applying
- YAML output ready to use

**Example workflow:**
```
User: "Create dashboard for my smart home"
AI: Analyzes 50 entities → generates 6 views → applies with backup
```

**Impact:**
- Beautiful dashboards without YAML knowledge
- One-command dashboard creation
- Killer feature for marketing
- Great screenshots for README

**Changes:**
- app/services/lovelace_generator.py: NEW - entity analysis & generation
- app/api/lovelace.py: NEW - 4 endpoints
- app/main.py: registered lovelace router

**Works with:** MCP v2.4.0+

## [2.3.17] - 2025-11-09

### 🗑️ Feature: HACS Uninstall

**Added HACS uninstall endpoint:**
- ✅ `POST /api/hacs/uninstall`
- ✅ Removes `/custom_components/hacs` directory
- ✅ Removes `.storage/hacs*` configuration files
- ✅ Restarts Home Assistant automatically

**Use cases:**
- Testing HACS install/uninstall cycle
- Clean removal of HACS
- Troubleshooting by reinstalling
- Reset to clean state

**Changes:**
- app/api/hacs.py: added uninstall_hacs() endpoint
- repository.json: updated maintainer email

## [2.3.16] - 2025-11-09

### 📚 Documentation: Version Tracking

**Added version tracking section to AI Instructions:**
- How to check Agent version (startup logs)
- How to check MCP version (connection logs)
- Version compatibility matrix
- Feature availability by version

**Compatibility matrix:**
- Agent v2.4.0 + MCP v2.4.0 = Lovelace dashboard generation
- Agent v2.3.15 + MCP v2.3.5 = Full store catalog support
- Agent v2.3.14 + MCP v2.3.4 = Repository management
- Agent v2.3.10 + MCP v2.3.3 = Basic add-on management

**Changes:**
- app/api/ai_instructions.py: added VERSION TRACKING section

## [2.3.15] - 2025-11-09

### 📦 Feature: Store Catalog Endpoint

**Added /store endpoint for complete add-ons catalog:**
- ✅ `GET /api/addons/store` - Full catalog from all repositories
- ✅ Returns ALL add-ons (not just installed)
- ✅ Use for browsing and AI recommendations

**Why:**
- `/addons` returns limited list (~2 add-ons)
- `/store` returns COMPLETE catalog (83+ add-ons)
- Enables AI to recommend from full catalog

**Use cases:**
- AI can show all available add-ons
- AI can recommend based on user needs
- Complete catalog browsing

**Changes:**
- app/services/supervisor_client.py: added list_store_addons()
- app/api/addons.py: added GET /store endpoint

## [2.3.14] - 2025-11-09

### 🐛 Bug Fix

**Fixed Repository Parsing Logic (Complete Fix):**
- ✅ Fixed parsing error for all Supervisor API response formats
- ✅ Handles 4 different response formats correctly
- ✅ No more `'list' object has no attribute 'get'` errors

**Root cause found:**
- Supervisor API returns: `{'data': [...list...]}`
- Old code: `result.get('data', {}).get('repositories')`
- If `data` is list: `[...].get('repositories')` → ERROR!

**Complete fix - handles all formats:**
1. Direct list: `[...]`
2. Dict with repositories: `{'repositories': [...]}`
3. Dict with data as list: `{'data': [...]}`
4. Dict with nested data: `{'data': {'repositories': [...]}}`

**Impact:**
- Repository management now fully functional
- All Supervisor API response formats handled correctly

## [2.3.13] - 2025-11-09

### 🔍 Feature: MCP Client Version Tracking

**Added MCP version logging:**
- ✅ Middleware logs MCP client version on first request
- ✅ Reads X-MCP-Client-Version header from MCP client
- ✅ Shows: `🔌 MCP Client connected: v2.3.4 from 192.168.68.63`
- ✅ Logs once per client IP (avoids spam)

**Benefits:**
- See which MCP version is connecting
- Identify version mismatches
- Better debugging capabilities

## [2.3.12] - 2025-11-09

### 🔧 Maintenance

**Force Docker rebuild:**
- Version increment to trigger Home Assistant rebuild
- Ensures repository parsing fix is applied

## [2.3.11] - 2025-11-09

### 🐛 Bug Fix

**Fixed Repository List Parsing:**
- ✅ Fixed parsing error: `'list' object has no attribute 'get'`
- ✅ Added flexible parsing for Supervisor API response
- ✅ Handles both list and dict response formats

**What was wrong:**
- Code assumed: `result.get('data', {}).get('repositories', [])`
- Supervisor API may return list directly or in different structure
- Caused error when listing repositories

**Fix:**
- Check if result is list → use directly
- Check if result is dict → handle multiple formats
- Fallback to empty list if unexpected format

**Impact:**
- `/api/addons/repositories` now works correctly
- AI can check connected repositories
- AI can suggest adding community repositories

**Changes:**
- app/api/addons.py: flexible parsing in list_repositories()

## [2.3.10] - 2025-11-09

### 🐛 Bug Fix

**Fixed Installed Add-ons Detection Logic:**
- ✅ Changed detection from `a.get('installed')` to `a.get('version')`
- ✅ Supervisor API returns `version` field for installed add-ons
- ✅ Field `installed` is not always present in response

**What was wrong:**
- Logic checked for `installed` field: `if a.get('installed')`
- Supervisor API doesn't always include this field
- Installed add-ons have `version` field (current installed version)
- Available (not installed) add-ons only have `version_latest`

**Impact:**
- `/api/addons/available` now correctly separates installed vs available
- `/api/addons/installed` now shows actual installed add-ons
- AI can see which add-ons are already installed

**Changes:**
- app/api/addons.py: changed filter logic in both endpoints
  - `list_available_addons()`: uses `version` to detect installed
  - `list_installed_addons()`: uses `version` to detect installed

## [2.3.9] - 2025-11-09

### 📚 Enhanced AI Instructions

**Improved Add-on Management Guidance:**
- ✅ Added comprehensive add-on reference guide with purpose and use cases
- ✅ Explained why popular add-ons may not appear (minimal repository setup)
- ✅ Removed hardcoded slugs - now dynamically searches add-ons by name
- ✅ Added instructions for users to add community repositories
- ✅ Detailed descriptions of popular add-ons:
  - Mosquitto MQTT Broker (IoT communication)
  - Zigbee2MQTT (Zigbee devices)
  - Node-RED (visual automation)
  - ESPHome (DIY devices)
  - Terminal & SSH (system access)
  - MariaDB (database)
  - DuckDNS/Let's Encrypt (remote access)

**New Use Cases:**
- "What add-ons do you recommend?" - AI suggests based on user needs
- "Why do I see so few add-ons?" - AI explains minimal installation
- Dynamic slug discovery instead of hardcoded values

**Impact:**
- AI can now provide intelligent recommendations
- Users understand why certain add-ons aren't visible
- Better guidance for repository management
- Safer installations (no hardcoded slugs that may be wrong)

**Changes:**
- app/api/ai_instructions.py: 2.3.0 → 2.3.9
- Added 📋 Popular Add-ons Reference
- Added 🎯 Use Case templates
- Added ⚠️ Repository requirements explanation

## [2.3.8] - 2025-11-09

### 🐛 Critical Bug Fix

**Fixed Supervisor API URL Path Duplication:**
- ✅ Removed `/supervisor/` prefix from all endpoint paths
- ✅ Fixed URL from `http://supervisor/supervisor/addons` to `http://supervisor/addons`
- ✅ All add-on management endpoints now use correct URL format

**Root cause:**
- v2.3.4 added `/supervisor/` prefix to endpoints
- But `base_url` is already `http://supervisor`
- Result: `http://supervisor` + `/supervisor/addons` = double `/supervisor/` → 404

**Fixed all endpoints:**
- `addons` (not `supervisor/addons`)
- `addons/{slug}/info`, `/logs`, `/install`, `/uninstall`, etc.
- `store/repositories` (not `supervisor/store/repositories`)

**Impact:**
- 🎉 Add-on management should now work with correct URLs!
- Manager role from v2.3.7 + correct URLs = working add-on management

## [2.3.7] - 2025-11-09

### 🔐 Critical Fix: Supervisor API Access + Security

**1. Added Supervisor Manager Role (Critical):**
- ✅ Added `hassio_role: manager` to config.yaml
- ✅ Grants add-on permissions to manage other add-ons via Supervisor API
- ✅ Fixes 403 Forbidden errors for all add-on management operations

**Root cause of 403 errors:**
- Supervisor API requires `hassio_role: manager` for add-on management
- Without this role, all Supervisor API calls return 403 Forbidden
- `hassio_api: true` alone is not sufficient for add-on management

**2. Security Fix: Removed Token Logging:**
- ✅ Removed token preview from all logs
- ✅ Changed from `Token: 7e2dec72...` to no token logging
- ✅ Headers logging moved to DEBUG level

**Why:**
- Logging tokens (even preview) is a security risk
- Tokens should never appear in logs accessible to users
- Debug-level logging available if needed for troubleshooting

**Changes:**
- config.yaml: added `hassio_role: manager`
- app/main.py: removed token from SupervisorClient startup log
- app/services/supervisor_client.py: removed token from all logs

**Impact:**
- 🎉 Add-on management should now work correctly!
- 🔐 No token information in logs (improved security)

## [2.3.6] - 2025-11-09

### 🔍 Debug Enhancement

**Enhanced Supervisor API Logging:**
- ✅ Added detailed logging for Supervisor API requests
- ✅ Log exact URL, headers, and token (preview) for each request
- ✅ Added SupervisorClient initialization log in startup event

**Purpose:**
- Debug 403 Forbidden errors from Supervisor API
- Verify correct URL format and authentication headers
- Identify root cause of add-on management issues

**Changes:**
- app/main.py: added SupervisorClient logging in startup event
- app/services/supervisor_client.py: enhanced request logging (INFO level)
- Logs now show: URL, headers, token preview for debugging

## [2.3.5] - 2025-11-09

### 🐛 Bug Fixes

**1. Supervisor API Authentication Fix (Critical):**
- ✅ Fixed authentication header for Supervisor API
- ✅ Changed from `Authorization: Bearer {token}` to `X-Supervisor-Token: {token}`
- ✅ All add-on management operations now authenticate correctly

**What was wrong:**
- Supervisor API uses custom `X-Supervisor-Token` header, not standard `Authorization: Bearer`
- All requests were rejected with 403 Forbidden due to incorrect auth header
- Home Assistant Supervisor API documentation specifies `X-Supervisor-Token` format

**Impact:**
- All add-on management endpoints now work correctly ✅
- Authentication passes, full add-on lifecycle management functional
- Fixes 403 Forbidden errors from v2.3.4

**2. Logs Endpoint Redirect Fix:**
- ✅ Fixed unnecessary 307 redirect for `/api/logs` endpoint
- ✅ Changed `@router.get("/")` to `@router.get("")` in logs.py
- ✅ Direct response without redirect

**What was wrong:**
- Endpoint was defined as `/api/logs/` (with trailing slash)
- Requests to `/api/logs` caused 307 redirect to `/api/logs/`
- FastAPI automatically redirects when trailing slash mismatch occurs

**Impact:**
- `/api/logs` now responds directly with 200 OK (no redirect)
- Improved API performance and cleaner request logs

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
- Added link to [@coolver/home-assistant-mcp](https://www.npmjs.com/package/@coolver/home-assistant-mcp) NPM package (formerly @coolver/mcp-home-assistant)
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
