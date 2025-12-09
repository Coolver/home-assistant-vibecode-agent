# 🧪 Home Assistant Agent - Comprehensive Test Suite

**Version:** 2.10.4  
**Purpose:** Complete testing of all HA Cursor Agent MCP functions  
**Usage:** Say "run Home Assistant Agent test suite" to run full suite

---

## 📋 Test Categories

- [Files](#1-file-operations-4-tests) (4 tests)
- [Entities](#2-entity-operations-2-tests) (2 tests)
- [Registries](#13-registry-operations-11-tests) (11 tests)
- [Helpers](#3-helper-operations-2-tests) (2 tests)
- [Automations](#4-automation-operations-2-tests) (2 tests)
- [Scripts](#5-script-operations-2-tests) (2 tests)
- [Git/Backup](#6-gitbackup-operations-4-tests) (4 tests)
- [System](#7-system-operations-4-tests) (4 tests)
- [HACS](#8-hacs-operations-8-tests) (8 tests)
- [Add-ons](#9-add-on-operations-13-tests) (13 tests)
- [Dashboards](#10-dashboard-operations-4-tests) (4 tests)
- [Repositories](#11-repository-operations-2-tests) (2 tests)
- [Logbook](#12-logbook-operations-1-test) (1 test)

**Total:** 64 tests

---

## Test Execution Instructions

### How to Run

1. **Full Suite:** "run Home Assistant Agent test suite"
2. **Category:** "run tests [Files/Entities/Helpers/...]"
3. **Single Test:** "run test [test_name]"

### Success Criteria

✅ **PASS:** Function returns expected data/success message  
❌ **FAIL:** Error, timeout, or unexpected response  
⚠️ **SKIP:** Test cannot run (missing dependencies, etc.)

### Test Output Format

```
✅ test_read_configuration_yaml - PASS (125ms)
   Response: File content retrieved successfully
   
❌ test_create_invalid_helper - FAIL (50ms)
   Error: Invalid helper configuration
   Expected: Validation error message
   
⚠️ test_hacs_install - SKIP
   Reason: HACS not installed
```

---

## 1. File Operations (4 tests)

### test_list_files_root
**Function:** `ha_list_files`  
**Parameters:** `{ directory: "/" }`  
**Expected:** List of files in root directory  
**Success:** Returns array with files like `configuration.yaml`, `automations.yaml`

### test_read_configuration_yaml
**Function:** `ha_read_file`  
**Parameters:** `{ path: "configuration.yaml" }`  
**Expected:** File content as string  
**Success:** Returns YAML content starting with `default_config:`

### test_write_and_read_test_file
**Function:** `ha_write_file` then `ha_read_file`  
**Steps:**
1. Write: `{ path: "test_agent.txt", content: "Test from HA Agent" }`
2. Read: `{ path: "test_agent.txt" }`  
**Expected:** Read returns written content  
**Cleanup:** Delete test file after

### test_delete_test_file
**Function:** `ha_delete_file`  
**Parameters:** `{ path: "test_agent.txt" }`  
**Expected:** File deleted successfully  
**Success:** Subsequent read fails with "not found"

---

## 2. Entity Operations (2 tests)

### test_list_all_entities
**Function:** `ha_list_entities`  
**Parameters:** `{}`  
**Expected:** Array of all entities  
**Success:** Returns entities with `entity_id`, `state`, `attributes`

### test_list_climate_entities
**Function:** `ha_list_entities`  
**Parameters:** `{ domain: "climate" }`  
**Expected:** Array of climate entities only  
**Success:** All returned entities start with `climate.`

### test_get_entity_state
**Function:** `ha_get_entity_state`  
**Parameters:** `{ entity_id: "sun.sun" }`  
**Expected:** Entity state object  
**Success:** Returns state (`above_horizon` or `below_horizon`)

---

## 3. Helper Operations (3 tests)

### test_list_helpers
**Function:** `ha_list_helpers`  
**Parameters:** `{}`  
**Expected:** List of existing helpers  
**Success:** Returns array (may be empty)

### test_create_input_boolean_helper
**Function:** `ha_create_helper`  
**Parameters:**
```json
{
  "type": "input_boolean",
  "config": {
    "name": "Test Agent Helper",
    "icon": "mdi:test-tube"
  }
}
```
**Expected:** Helper created successfully  
**Success:** Helper appears in list, entity_id exists  
**Cleanup:** Delete helper after test

### test_delete_helper
**Function:** `ha_delete_helper`  
**Steps:**
1. Create test helper: `ha_create_helper` with `{ type: "input_boolean", config: { name: "Test Helper for Deletion" } }`
2. Verify helper exists in list
3. Delete helper: `ha_delete_helper` with `{ entity_id: "input_boolean.test_helper_for_deletion" }`
4. Verify helper no longer appears in list  
**Expected:** Helper deleted successfully  
**Success:** Helper removed from list, subsequent get returns error/not found  
**Note:** ⚠️ DESTRUCTIVE - only test with test helpers created for this purpose

---

## 4. Automation Operations (3 tests)

### test_list_automations
**Function:** `ha_list_automations`  
**Parameters:** `{}`  
**Expected:** List of automations  
**Success:** Returns array with automation objects

### test_create_test_automation
**Function:** `ha_create_automation`  
**Parameters:**
```json
{
  "config": {
    "id": "test_agent_automation",
    "alias": "Test Agent Automation",
    "trigger": [
      {
        "platform": "state",
        "entity_id": "sun.sun"
      }
    ],
    "action": [
      {
        "service": "notify.persistent_notification",
        "data": {
          "message": "Test from Agent"
        }
      }
    ]
  }
}
```
**Expected:** Automation created  
**Success:** Automation appears in list  
**Cleanup:** Delete automation after

### test_delete_automation
**Function:** `ha_delete_automation`  
**Steps:**
1. Create test automation: `ha_create_automation` with test config (id: "test_automation_for_deletion")
2. Verify automation exists in list
3. Delete automation: `ha_delete_automation` with `{ automation_id: "test_automation_for_deletion" }`
4. Verify automation no longer appears in list  
**Expected:** Automation deleted successfully  
**Success:** Automation removed from list, subsequent get returns error/not found  
**Note:** ⚠️ DESTRUCTIVE - only test with test automations created for this purpose

---

## 5. Script Operations (3 tests)

### test_list_scripts
**Function:** `ha_list_scripts`  
**Parameters:** `{}`  
**Expected:** List of scripts  
**Success:** Returns array (may be empty)

### test_create_test_script
**Function:** `ha_create_script`  
**Parameters:**
```json
{
  "config": {
    "test_agent_script": {
      "alias": "Test Agent Script",
      "sequence": [
        {
          "service": "notify.persistent_notification",
          "data": {
            "message": "Test script executed"
          }
        }
      ]
    }
  }
}
```
**Expected:** Script created  
**Success:** Script appears in list  
**Cleanup:** Delete script after

### test_delete_script
**Function:** `ha_delete_script`  
**Steps:**
1. Create test script: `ha_create_script` with test config (id: "test_script_for_deletion")
2. Verify script exists in list
3. Delete script: `ha_delete_script` with `{ script_id: "test_script_for_deletion" }`
4. Verify script no longer appears in list  
**Expected:** Script deleted successfully  
**Success:** Script removed from list, subsequent get returns error/not found  
**Note:** ⚠️ DESTRUCTIVE - only test with test scripts created for this purpose

---

## 6. Git/Backup Operations (4 tests)

### test_git_history
**Function:** `ha_git_history`  
**Parameters:** `{ limit: 5 }`  
**Expected:** Last 5 commits  
**Success:** Returns array with commit objects (hash, message, date)

### test_git_commit
**Function:** `ha_git_commit`  
**Parameters:** `{ message: "Test commit from HA Agent" }`  
**Expected:** Commit created  
**Success:** Returns commit hash

### test_git_diff_last_two_commits
**Function:** `ha_git_diff`  
**Steps:**
1. Get history to find last 2 commit hashes
2. Call `ha_git_diff` with those hashes  
**Expected:** Diff between commits  
**Success:** Returns diff text

### test_git_rollback_and_restore
**Function:** `ha_git_rollback`  
**Steps:**
1. Note current commit hash
2. Rollback to previous commit
3. Verify rollback
4. Rollback back to original  
**Expected:** Successful rollback and restore  
**Success:** System returns to original state

---

## 7. System Operations (5 tests)

### test_check_config
**Function:** `ha_check_config`  
**Parameters:** `{}`  
**Expected:** Configuration validation result  
**Success:** Returns `valid: true` or list of errors

### test_get_logs
**Function:** `ha_get_logs`  
**Parameters:** `{ limit: 10 }`  
**Expected:** Last 10 log entries  
**Success:** Returns array of log entries

### test_check_agent_logs_for_errors
**Function:** `ha_get_logs`  
**Parameters:** `{ limit: 100, level: "ERROR" }`  
**Expected:** Check for errors in agent logs  
**Success:** Returns empty array or only expected/known errors  
**Validation:**
- Check that no unexpected ERROR level logs exist
- Verify fallback operations logged as INFO (not ERROR) - e.g., "falling back to list method" should be INFO
- Ensure no WebSocket connection errors
- Confirm no authentication failures
- Check that registry operations (Entity/Area/Device) don't produce errors
- Verify that fallback mechanisms work correctly (no errors, only INFO logs)
**Note:** ⚠️ **Should be run AFTER all other tests** to catch any errors they may have caused. This is a critical validation step.
**Expected Behavior:**
- Registry fallback operations should log: `"WebSocket result empty for {id}, falling back to list method"` as INFO
- No ERROR logs should appear for normal fallback operations
- Only genuine errors (connection failures, auth issues) should appear as ERROR

### test_reload_config_core
**Function:** `ha_reload_config`  
**Parameters:** `{ component: "core" }`  
**Expected:** Core config reloaded  
**Success:** Returns success message  
**Note:** Does NOT restart HA

### test_health_check
**Function:** Direct API call to `/api/health`  
**Expected:** Health status  
**Success:** Returns `{ status: "ok", version, git_enabled }`

---

## 8. HACS Operations (8 tests)

### test_hacs_status
**Function:** `ha_hacs_status`  
**Parameters:** `{}`  
**Expected:** HACS installation status  
**Success:** Returns installed/not installed status

### test_install_hacs
**Function:** `ha_install_hacs`  
**Parameters:** `{}`  
**Expected:** HACS installed  
**Success:** HACS appears in integrations  
**Note:** Only run if not installed

### test_hacs_list_repositories
**Function:** `ha_hacs_list_repositories`  
**Parameters:** `{}`  
**Expected:** List of available HACS repos  
**Success:** Returns array of repositories  
**Prerequisite:** HACS installed

### test_hacs_search_integration
**Function:** `ha_hacs_search`  
**Parameters:**
```json
{
  "query": "xiaomi",
  "category": "integration"
}
```
**Expected:** Search results  
**Success:** Returns repos matching query  
**Prerequisite:** HACS installed

### test_hacs_repository_details
**Function:** `ha_hacs_repository_details`  
**Parameters:** `{ repository_id: "hacs/integration" }`  
**Expected:** Detailed repo info  
**Success:** Returns stars, authors, version  
**Prerequisite:** HACS installed

### test_hacs_install_repository
**Function:** `ha_hacs_install_repository`  
**Parameters:**
```json
{
  "repository": "test/repo",
  "category": "integration"
}
```
**Expected:** Repository installed  
**Success:** Repo appears in installed list  
**Note:** Use test repo or skip  
**Cleanup:** Uninstall after

### test_hacs_update_all
**Function:** `ha_hacs_update_all`  
**Parameters:** `{}`  
**Expected:** All HACS repos updated  
**Success:** Returns update results  
**Note:** May take several minutes

### test_uninstall_hacs
**Function:** `ha_uninstall_hacs`  
**Parameters:** `{}`  
**Expected:** HACS uninstalled  
**Success:** HACS removed from integrations  
**Note:** Only run in test environment

---

## 9. Add-on Operations (13 tests)

### test_list_store_addons
**Function:** `ha_list_store_addons`  
**Parameters:** `{}`  
**Expected:** All available add-ons from store  
**Success:** Returns large array with all store add-ons

### test_list_available_addons
**Function:** `ha_list_addons`  
**Parameters:** `{}`  
**Expected:** Available add-ons (limited list)  
**Success:** Returns array of add-ons

### test_list_installed_addons
**Function:** `ha_list_installed_addons`  
**Parameters:** `{}`  
**Expected:** Currently installed add-ons  
**Success:** Returns array (includes HA Cursor Agent)

### test_get_addon_info
**Function:** `ha_addon_info`  
**Parameters:** `{ slug: "core_mosquitto" }`  
**Expected:** Detailed add-on information  
**Success:** Returns name, version, state, options

### test_get_addon_options
**Function:** `ha_get_addon_options`  
**Parameters:** `{ slug: "core_mosquitto" }`  
**Expected:** Add-on configuration options  
**Success:** Returns options object

### test_get_addon_logs
**Function:** `ha_addon_logs`  
**Parameters:** `{ slug: "core_mosquitto", lines: 20 }`  
**Expected:** Last 20 log lines  
**Success:** Returns log text

### test_install_addon
**Function:** `ha_install_addon`  
**Parameters:** `{ slug: "core_mosquitto" }`  
**Expected:** Add-on installed  
**Success:** Add-on appears in installed list  
**Note:** Use lightweight add-on  
**Cleanup:** Uninstall after

### test_start_addon
**Function:** `ha_start_addon`  
**Parameters:** `{ slug: "core_mosquitto" }`  
**Expected:** Add-on started  
**Success:** Add-on state changes to "started"  
**Prerequisite:** Add-on installed

### test_stop_addon
**Function:** `ha_stop_addon`  
**Parameters:** `{ slug: "core_mosquitto" }`  
**Expected:** Add-on stopped  
**Success:** Add-on state changes to "stopped"

### test_restart_addon
**Function:** `ha_restart_addon`  
**Parameters:** `{ slug: "core_mosquitto" }`  
**Expected:** Add-on restarted  
**Success:** Add-on restarts successfully

### test_set_addon_options
**Function:** `ha_set_addon_options`  
**Parameters:**
```json
{
  "slug": "core_mosquitto",
  "options": {
    "logins": [],
    "anonymous": true
  }
}
```
**Expected:** Options updated  
**Success:** Get options returns new values

### test_update_addon
**Function:** `ha_update_addon`  
**Parameters:** `{ slug: "core_mosquitto" }`  
**Expected:** Add-on updated to latest version  
**Success:** Version updated (or already latest)  
**Note:** May take several minutes

### test_uninstall_addon
**Function:** `ha_uninstall_addon`  
**Parameters:** `{ slug: "core_mosquitto" }`  
**Expected:** Add-on uninstalled  
**Success:** Add-on removed from installed list  
**Note:** Only run after install test

---

## 10. Dashboard Operations (4 tests)

### test_analyze_entities_for_dashboard
**Function:** `ha_analyze_entities_for_dashboard`  
**Parameters:** `{}`  
**Expected:** Entity analysis for dashboard creation  
**Success:** Returns entities grouped by domain

### test_preview_existing_dashboard
**Function:** `ha_preview_dashboard`  
**Parameters:** `{}`  
**Expected:** Current dashboard configuration  
**Success:** Returns lovelace config or empty

### test_apply_dashboard
**Function:** `ha_apply_dashboard`  
**Parameters:**
```json
{
  "dashboard_config": {
    "title": "Test Dashboard",
    "views": [
      {
        "title": "Test View",
        "path": "test-view",
        "cards": [
          {
            "type": "markdown",
            "content": "Test from Agent"
          }
        ]
      }
    ]
  },
  "filename": "test-agent-dashboard.yaml",
  "register_dashboard": true,
  "create_backup": true
}
```
**Expected:** Dashboard created and registered  
**Success:** Dashboard file exists, appears in sidebar  
**Cleanup:** Delete dashboard after

### test_delete_dashboard
**Function:** `ha_delete_dashboard`  
**Parameters:**
```json
{
  "filename": "test-agent-dashboard.yaml",
  "remove_from_config": true,
  "create_backup": true
}
```
**Expected:** Dashboard deleted  
**Success:** Dashboard file removed, unregistered

---

## 11. Repository Operations (2 tests)

### test_list_addon_repositories
**Function:** `ha_list_repositories`  
**Parameters:** `{}`  
**Expected:** List of add-on repositories  
**Success:** Returns array with repository URLs

### test_add_and_remove_repository
**Function:** `ha_add_repository`  
**Parameters:**
```json
{
  "repository_url": "https://github.com/hassio-addons/repository"
}
```
**Expected:** Repository added  
**Success:** Repository appears in list  
**Cleanup:** May need manual removal

---

## 12. Logbook Operations (1 test)

### test_logbook_recent_scripts
**Function:** `ha_logbook_entries`  
**Parameters:**
```json
{
  "domains": ["script"],
  "lookback_minutes": 120,
  "limit": 25
}
```
**Expected:** Recent logbook entries for scripts plus summary info  
**Success:** Response includes `entries` array with script events and `summary.scripts` data

---

## 🎯 Test Execution Strategy

**⚠️ Important:** `test_check_agent_logs_for_errors` should be executed **LAST** after all other tests to validate that no errors were introduced during test execution.

### Phase 1: Read-Only Tests (Safe)
- All list/get/analyze operations
- Config checking
- Log reading
- Entity queries
- Registry list operations (Entity/Area/Device)
- Registry entry retrieval (single entries)
- Log error checking (after all tests)

### Phase 2: Non-Destructive Writes (Safe)
- Create test files
- Git commits
- Create helpers/automations/scripts for testing
- Registry updates (with cleanup/restore)

### Phase 3: Reversible Operations (Caution)
- Install/uninstall test add-ons
- Dashboard creation/deletion
- Git rollback (with restore)

### Phase 4: System Operations (Warning)
- Config reload
- Add-on start/stop
- HACS operations

### Phase 5: Destructive Operations (Skip in Production)
- HA restart
- HACS uninstall
- Repository modifications
- Registry deletions (remove_entity_registry, delete_area_registry)

---

## 📊 Test Metrics

Track these metrics during test execution:

- **Total Tests:** 64
- **Passed:** Count
- **Failed:** Count
- **Skipped:** Count
- **Execution Time:** Total duration
- **Coverage:** % of functions tested

---

## 🔧 Test Configuration

### Prerequisites
- Home Assistant running
- HA Cursor Agent installed and running
- MCP server connected
- Git initialized in /config
- Test mode recommended (not production)

### Environment Variables
```bash
HA_AGENT_URL=http://homeassistant.local:8099
HA_AGENT_KEY=<your-token>
```

### Cleanup After Tests
- Delete test files (`test_agent.txt`, etc.)
- Remove test helpers
- Remove test automations
- Remove test scripts
- Remove test dashboards
- Restore registry changes (entity names, area names, device names)
- Delete test areas created during tests
- Rollback to pre-test git commit (optional)

---

## 📝 Test Report Template

```markdown
# Test Execution Report

**Date:** YYYY-MM-DD HH:MM
**Version:** 2.7.7
**Environment:** Development/Production

## Summary
- Total: 64
- Passed: XX
- Failed: XX
- Skipped: XX
- Duration: XX seconds

## Failed Tests
1. test_name - Error message
2. ...

## Skipped Tests
1. test_name - Reason
2. ...

## Performance Notes
- Slowest test: test_name (XX seconds)
- Average duration: XX ms

## Recommendations
- [Any issues found]
- [Suggested fixes]
```

---

---

## 13. Registry Operations (12 tests)

### test_get_entity_registry_list
**Function:** `ha_get_entity_registry`  
**Parameters:** `{}`  
**Expected:** Full Entity Registry with metadata  
**Success:** Returns array of entities with `entity_id`, `area_id`, `device_id`, `name`, `disabled_by`, etc.  
**Note:** This provides complete metadata, unlike `ha_list_entities` which only returns states

### test_get_entity_registry_entry
**Function:** `ha_get_entity_registry_entry`  
**Parameters:** `{ entity_id: "climate.office_trv_thermostat" }`  
**Expected:** Single entity registry entry with full metadata  
**Success:** Returns entity with `area_id`, `device_id`, `name`, `disabled_by`, `capabilities`, etc.  
**Note:** Uses WebSocket `config/entity_registry/get` (works directly)

### test_update_entity_registry
**Function:** `ha_update_entity_registry`  
**Parameters:**
```json
{
  "entity_id": "climate.office_trv_thermostat",
  "name": "Office TRV Test Name"
}
```
**Expected:** Entity registry updated  
**Success:** Returns updated entity entry with new name  
**Cleanup:** Restore original name after test  
**Note:** ⚠️ MODIFIES entity registry - requires approval

### test_get_area_registry_list
**Function:** `ha_get_area_registry`  
**Parameters:** `{}`  
**Expected:** Full Area Registry  
**Success:** Returns array of areas with `area_id`, `name`, `aliases`, `floor_id`, etc.

### test_get_area_registry_entry
**Function:** `ha_get_area_registry_entry`  
**Parameters:** `{ area_id: "office" }`  
**Expected:** Single area registry entry  
**Success:** Returns area with `area_id`, `name`, `aliases`, `temperature_entity_id`, etc.  
**Note:** Uses fallback mechanism (WebSocket `config/area_registry/get` returns empty, falls back to list)

### test_create_area_registry
**Function:** `ha_create_area_registry`  
**Parameters:**
```json
{
  "name": "Test Area from Agent"
}
```
**Expected:** New area created  
**Success:** Returns created area with generated `area_id`  
**Cleanup:** Delete area after test  
**Note:** ⚠️ MODIFIES area registry - requires approval

### test_update_area_registry
**Function:** `ha_update_area_registry`  
**Parameters:**
```json
{
  "area_id": "office",
  "name": "Office Updated Name"
}
```
**Expected:** Area name updated  
**Success:** Returns updated area with new name  
**Cleanup:** Restore original name after test  
**Note:** ⚠️ MODIFIES area registry - requires approval

### test_get_device_registry_list
**Function:** `ha_get_device_registry`  
**Parameters:** `{}`  
**Expected:** Full Device Registry  
**Success:** Returns array of devices with `id`, `name`, `area_id`, `manufacturer`, `model`, etc.

### test_get_device_registry_entry
**Function:** `ha_get_device_registry_entry`  
**Parameters:** `{ device_id: "00ba72baf914c16f3a25499680c5279e" }`  
**Expected:** Single device registry entry  
**Success:** Returns device with `id`, `name`, `area_id`, `manufacturer`, `model`, `connections`, etc.  
**Note:** Uses fallback mechanism (WebSocket `config/device_registry/get` returns empty, falls back to list)

### test_update_device_registry
**Function:** `ha_update_device_registry`  
**Parameters:**
```json
{
  "device_id": "00ba72baf914c16f3a25499680c5279e",
  "name_by_user": "Office TRV Updated Name"
}
```
**Expected:** Device registry updated  
**Success:** Returns updated device entry  
**Cleanup:** Restore original name after test  
**Note:** ⚠️ MODIFIES device registry - requires approval

### test_remove_entity_registry
**Function:** `ha_remove_entity_registry`  
**Parameters:** `{ entity_id: "test_entity_to_remove" }`  
**Expected:** Entity removed from registry  
**Success:** Entity no longer appears in registry list  
**Note:** ⚠️ DESTRUCTIVE - only test with test entities  
**Warning:** This permanently removes entity from registry (doesn't delete entity itself)

### test_delete_area_registry
**Function:** `ha_delete_area_registry`  
**Steps:**
1. Create test area: `ha_create_area_registry` with `{ name: "Test Area for Deletion" }`
2. Verify area exists in registry
3. Delete area: `ha_delete_area_registry` with `{ area_id: "<generated_area_id>" }`
4. Verify area no longer appears in registry list  
**Expected:** Area deleted successfully  
**Success:** Area removed from registry, subsequent get returns error/not found  
**Note:** ⚠️ DESTRUCTIVE - only test with test areas created for this purpose

---

**Last Updated:** 2025-12-09  
**Test Suite Version:** 1.1.0  
**Compatible with:** HA Cursor Agent v2.10.4+

