# 🧪 Home Assistant Agent - Comprehensive Test Suite

**Version:** 2.10.39  
**Purpose:** Complete testing of all HA Cursor Agent MCP functions  
**Usage:** Say "run Home Assistant Agent test suite" to run full suite

---

## 📋 Test Categories

- [Files](#1-file-operations-4-tests) (4 tests)
- [Entities](#2-entity-operations-2-tests) (2 tests)
- [Registries](#13-registry-operations-13-tests) (13 tests)
- [Helpers](#3-helper-operations-2-tests) (2 tests)
- [Automations](#4-automation-operations-6-tests) (6 tests)
- [Scripts](#5-script-operations-2-tests) (2 tests)
- [Git/Backup](#6-gitbackup-operations-4-tests) (4 tests)
- [System](#7-system-operations-4-tests) (4 tests)
- [HACS](#8-hacs-operations-8-tests) (8 tests)
- [Add-ons](#9-add-on-operations-13-tests) (13 tests)
- [Dashboards](#10-dashboard-operations-4-tests) (4 tests)
- [Repositories](#11-repository-operations-2-tests) (2 tests)
- [Logbook](#12-logbook-operations-1-test) (1 test)

**Total:** 69 tests

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

## 4. Automation Operations (6 tests)

### test_list_automations
**Function:** `ha_list_automations`  
**Parameters:** `{}`  
**Expected:** List of automations  
**Success:** Returns array with automation objects

### test_list_automations_ids_only
**Function:** `ha_list_automations`  
**Parameters:** `{ ids_only: true }`  
**Expected:** List of automation IDs only (no full configs)  
**Success:** Returns array of strings (automation IDs)  
**Note:** Useful for quick checks without loading full configurations

### test_get_automation_by_id
**Function:** `ha_get_automation`  
**Parameters:** `{ automation_id: "<existing_automation_id>" }`  
**Expected:** Full automation configuration  
**Success:** Returns automation object with `id`, `alias`, `trigger`, `action`, etc.  
**Note:** Works with automations from `automations.yaml`, `packages/*.yaml`, and `.storage`

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

### test_delete_ghost_automation_from_entity_registry
**Function:** `ha_delete_automation`  
**Steps:**
1. Create test automation: `ha_create_automation` with test config (id: "test_ghost_automation", alias: "Test Ghost Automation")
2. Verify automation exists in list
3. Manually remove automation from storage (simulate ghost entry scenario) OR wait for Entity Registry to have entry but storage to be cleared
4. Delete automation: `ha_delete_automation` with `{ automation_id: "test_ghost_automation" }` OR `{ automation_id: "test_ghost_automation" }` (by alias)
5. Verify automation no longer appears in list  
**Expected:** Ghost automation deleted from Entity Registry successfully  
**Success:** Automation removed from Entity Registry even if not found in storage  
**Note:** ⚠️ Tests the new functionality to remove "ghost" entries from Entity Registry by matching id and alias  
**Details:** This test verifies that `delete_automation` can:
- Find automations in Entity Registry by `id` when not found in storage
- Find automations in Entity Registry by `alias` when not found in storage
- Remove all matching entries from Entity Registry
- Reload automations to sync Entity Registry

### test_delete_automation_with_alias_matching
**Function:** `ha_delete_automation`  
**Steps:**
1. Create test automation: `ha_create_automation` with test config (id: "test_alias_match_123", alias: "Test Alias Match Automation")
2. Verify automation exists in list with both id and alias visible
3. Delete automation by alias-like id: `ha_delete_automation` with `{ automation_id: "test_alias_match" }` (partial match)
4. Verify automation no longer appears in list  
**Expected:** Automation deleted successfully by alias matching  
**Success:** Automation removed even when Entity Registry uses different entity_id than storage id  
**Note:** ⚠️ Tests alias-based matching when Entity Registry entity_id differs from automation id in storage

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

### Step-by-Step Testing Plan

To avoid context loss during large test runs, tests are broken down into small, manageable steps. Execute 3-5 steps at a time, then pause and continue.

**Total Steps:** 40  
**Read-Only Steps:** 27  
**Write Steps:** 13

#### Phase 1: Read-Only File Operations (4 steps)

**Step 1.1:** `test_list_files_root`  
- **MCP Tool:** `ha_list_files`  
- **Parameters:** `{ directory: "/" }`  
- **Expected:** List of files in root directory

**Step 1.2:** `test_read_configuration_yaml`  
- **MCP Tool:** `ha_read_file`  
- **Parameters:** `{ path: "configuration.yaml" }`  
- **Expected:** File content as string

**Step 1.3:** `test_read_automations_yaml`  
- **MCP Tool:** `ha_read_file`  
- **Parameters:** `{ path: "automations.yaml" }`  
- **Expected:** File content or "not found" error

**Step 1.4:** `test_read_scripts_yaml`  
- **MCP Tool:** `ha_read_file`  
- **Parameters:** `{ path: "scripts.yaml" }`  
- **Expected:** File content or "not found" error

#### Phase 2: Read-Only Entity Operations (3 steps)

**Step 2.1:** `test_list_all_entities`  
- **MCP Tool:** `ha_list_entities`  
- **Parameters:** `{}`  
- **Expected:** Array of all entities

**Step 2.2:** `test_list_climate_entities`  
- **MCP Tool:** `ha_list_entities`  
- **Parameters:** `{ domain: "climate" }`  
- **Expected:** Only climate entities

**Step 2.3:** `test_get_entity_state`  
- **MCP Tool:** `ha_get_entity_state`  
- **Parameters:** `{ entity_id: "sun.sun" }`  
- **Expected:** Entity state object

#### Phase 3: Read-Only Registry Operations (6 steps)

**Step 3.1:** `test_get_entity_registry_list`  
- **MCP Tool:** `ha_get_entity_registry`  
- **Parameters:** `{}`  
- **Expected:** Full Entity Registry with metadata

**Step 3.2:** `test_get_entity_registry_entry`  
- **MCP Tool:** `ha_get_entity_registry_entry`  
- **Parameters:** `{ entity_id: "<any existing entity_id>" }`  
- **Expected:** Single entity registry entry

**Step 3.3:** `test_get_area_registry_list`  
- **MCP Tool:** `ha_get_area_registry`  
- **Parameters:** `{}`  
- **Expected:** Full Area Registry

**Step 3.4:** `test_get_area_registry_entry`  
- **MCP Tool:** `ha_get_area_registry_entry`  
- **Parameters:** `{ area_id: "<any existing area_id>" }`  
- **Expected:** Single area registry entry

**Step 3.5:** `test_get_device_registry_list`  
- **MCP Tool:** `ha_get_device_registry`  
- **Parameters:** `{}`  
- **Expected:** Full Device Registry

**Step 3.6:** `test_find_dead_entities`  
- **MCP Tool:** `ha_find_dead_entities`  
- **Parameters:** `{}`  
- **Expected:** Object with `dead_automations`, `dead_scripts`, `summary`

#### Phase 4: Read-Only Helper Operations (1 step)

**Step 4.1:** `test_list_helpers`  
- **MCP Tool:** `ha_list_helpers`  
- **Parameters:** `{}`  
- **Expected:** List of existing helpers

#### Phase 5: Read-Only Automation Operations (3 steps)

**Step 5.1:** `test_list_automations`  
- **MCP Tool:** `ha_list_automations`  
- **Parameters:** `{}`  
- **Expected:** List of automations

**Step 5.2:** `test_list_automations_ids_only`  
- **MCP Tool:** `ha_list_automations`  
- **Parameters:** `{ ids_only: true }`  
- **Expected:** List of automation IDs only

**Step 5.3:** `test_get_automation_by_id`  
- **MCP Tool:** `ha_get_automation`  
- **Parameters:** `{ automation_id: "<existing_automation_id>" }`  
- **Expected:** Full automation configuration

#### Phase 6: Read-Only Script Operations (1 step)

**Step 6.1:** `test_list_scripts`  
- **MCP Tool:** `ha_list_scripts`  
- **Parameters:** `{}`  
- **Expected:** List of scripts

#### Phase 7: Read-Only System Operations (2 steps)

**Step 7.1:** `test_check_config`  
- **MCP Tool:** `ha_check_config`  
- **Parameters:** `{}`  
- **Expected:** Configuration validation result

**Step 7.2:** `test_get_logs`  
- **MCP Tool:** `ha_get_logs`  
- **Parameters:** `{ limit: 10 }`  
- **Expected:** Last 10 log entries

#### Phase 8: Read-Only Git Operations (2 steps)

**Step 8.1:** `test_git_history`  
- **MCP Tool:** `ha_git_history`  
- **Parameters:** `{ limit: 5 }`  
- **Expected:** Last 5 commits

**Step 8.2:** `test_git_diff`  
- **MCP Tool:** `ha_git_diff`  
- **Parameters:** `{}` (or with commit hashes if needed)  
- **Expected:** Diff between commits

#### Phase 9: Read-Only HACS Operations (1 step, if installed)

**Step 9.1:** `test_hacs_status`  
- **MCP Tool:** `ha_hacs_status`  
- **Parameters:** `{}`  
- **Expected:** HACS installation status

#### Phase 10: Read-Only Add-on Operations (3 steps)

**Step 10.1:** `test_list_installed_addons`  
- **MCP Tool:** `ha_list_installed_addons`  
- **Parameters:** `{}`  
- **Expected:** Currently installed add-ons

**Step 10.2:** `test_list_addons`  
- **MCP Tool:** `ha_list_addons`  
- **Parameters:** `{}`  
- **Expected:** Available add-ons (limited list)

**Step 10.3:** `test_get_addon_info`  
- **MCP Tool:** `ha_addon_info`  
- **Parameters:** `{ slug: "core_mosquitto" }` (or any other installed)  
- **Expected:** Detailed add-on information

#### Phase 11: Read-Only Dashboard Operations (2 steps)

**Step 11.1:** `test_analyze_entities_for_dashboard`  
- **MCP Tool:** `ha_analyze_entities_for_dashboard`  
- **Parameters:** `{}`  
- **Expected:** Entity analysis for dashboard creation

**Step 11.2:** `test_preview_existing_dashboard`  
- **MCP Tool:** `ha_preview_dashboard`  
- **Parameters:** `{}`  
- **Expected:** Current dashboard configuration

#### Phase 12: Read-Only Repository Operations (1 step)

**Step 12.1:** `test_list_addon_repositories`  
- **MCP Tool:** `ha_list_repositories`  
- **Parameters:** `{}`  
- **Expected:** List of add-on repositories

#### Phase 13: Read-Only Logbook Operations (1 step)

**Step 13.1:** `test_logbook_recent_scripts`  
- **MCP Tool:** `ha_logbook_entries`  
- **Parameters:** `{ domains: ["script"], lookback_minutes: 120, limit: 25 }`  
- **Expected:** Recent logbook entries for scripts

#### Phase 14: Write Operations - Helper (2 steps)

**Step 14.1:** `test_create_input_boolean_helper`  
- **MCP Tool:** `ha_create_helper`  
- **Parameters:** `{ type: "input_boolean", config: { name: "Test Agent Helper", icon: "mdi:test-tube" } }`  
- **Expected:** Helper created successfully  
- **Cleanup:** Delete helper after test

**Step 14.2:** `test_delete_helper`  
- **MCP Tool:** `ha_delete_helper`  
- **Parameters:** `{ entity_id: "input_boolean.test_agent_helper" }`  
- **Expected:** Helper deleted successfully

#### Phase 15: Write Operations - Automation (4 steps)

**Step 15.1:** `test_create_test_automation`  
- **MCP Tool:** `ha_create_automation`  
- **Parameters:** See test definition in section 4  
- **Expected:** Automation created  
- **Cleanup:** Delete automation after test

**Step 15.2:** `test_delete_automation`  
- **MCP Tool:** `ha_delete_automation`  
- **Parameters:** `{ automation_id: "test_agent_automation" }`  
- **Expected:** Automation deleted successfully

**Step 15.3:** `test_delete_ghost_automation_from_entity_registry`  
- **MCP Tool:** `ha_delete_automation`  
- **Steps:**
  1. Create test automation with id: "test_ghost_automation"
  2. Verify it exists in list
  3. Delete automation: `ha_delete_automation` with `{ automation_id: "test_ghost_automation" }`
  4. Verify it's removed from Entity Registry even if not in storage  
- **Expected:** Ghost automation deleted from Entity Registry successfully  
- **Note:** Tests removal of "ghost" entries by matching id and alias

**Step 15.4:** `test_delete_automation_with_alias_matching`  
- **MCP Tool:** `ha_delete_automation`  
- **Steps:**
  1. Create test automation with id: "test_alias_match_123", alias: "Test Alias Match"
  2. Verify it exists in list
  3. Delete automation by partial alias match: `ha_delete_automation` with `{ automation_id: "test_alias_match" }`
  4. Verify it's removed successfully  
- **Expected:** Automation deleted successfully by alias matching  
- **Note:** Tests alias-based matching when Entity Registry entity_id differs from storage id

#### Phase 16: Write Operations - Script (2 steps)

**Step 16.1:** `test_create_test_script`  
- **MCP Tool:** `ha_create_script`  
- **Parameters:** See test definition in section 5  
- **Expected:** Script created  
- **Cleanup:** Delete script after test

**Step 16.2:** `test_delete_script`  
- **MCP Tool:** `ha_delete_script`  
- **Parameters:** `{ script_id: "test_agent_script" }`  
- **Expected:** Script deleted successfully

#### Phase 17: Write Operations - Registry (3 steps, with cleanup)

**Step 17.1:** `test_update_entity_registry`  
- **MCP Tool:** `ha_update_entity_registry`  
- **Parameters:** `{ entity_id: "<existing entity_id>", name: "Test Name" }`  
- **Expected:** Entity registry updated  
- **Cleanup:** Restore original name after test

**Step 17.2:** `test_create_area_registry`  
- **MCP Tool:** `ha_create_area`  
- **Parameters:** `{ name: "Test Area from Agent" }`  
- **Expected:** New area created  
- **Cleanup:** Delete area after test

**Step 17.3:** `test_update_area_registry`  
- **MCP Tool:** `ha_update_area`  
- **Parameters:** `{ area_id: "<existing area_id>", name: "Updated Name" }`  
- **Expected:** Area name updated  
- **Cleanup:** Restore original name after test

#### Phase 18: Write Operations - Git (1 step)

**Step 18.1:** `test_git_commit`  
- **MCP Tool:** `ha_git_commit`  
- **Parameters:** `{ message: "Test commit from HA Agent" }`  
- **Expected:** Commit created

#### Phase 19: Final Validation (1 step)

**Step 19.1:** `test_check_agent_logs_for_errors`  
- **MCP Tool:** `ha_get_logs`  
- **Parameters:** `{ limit: 100, level: "ERROR" }`  
- **Expected:** Check for errors in agent logs  
- **Note:** ⚠️ **Must be executed LAST** after all other tests

### Execution Recommendations

1. **Execute 3-5 steps at a time** - optimal size for maintaining context
2. **Pause between phases** - can stop after each Phase
3. **Verify results** - check that results match expectations after each step
4. **Cleanup is important** - don't forget to remove test data after write operations
5. **Final validation** - Step 19.1 must be last

### Test Output Format

After each step, record:
- ✅ **PASS** - test passed successfully
- ❌ **FAIL** - test failed (with error description)
- ⚠️ **SKIP** - test skipped (with reason)

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

## 13. Registry Operations (13 tests)

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

### test_find_dead_entities
**Function:** `ha_find_dead_entities`  
**Parameters:** `{}`  
**Expected:** List of "dead" entities (automations/scripts in registry but not in YAML)  
**Success:** Returns object with:
- `dead_automations`: Array of automation entities not found in `automations.yaml`
- `dead_scripts`: Array of script entities not found in `scripts.yaml`
- `summary`: Object with counts:
  - `total_registry_automations`: Total automations in registry
  - `total_registry_scripts`: Total scripts in registry
  - `total_yaml_automations`: Total automations in YAML
  - `total_yaml_scripts`: Total scripts in YAML
  - `dead_automations_count`: Number of dead automations
  - `dead_scripts_count`: Number of dead scripts
  - `total_dead`: Total dead entities
**Note:** ⚠️ READ-ONLY - safe to run, only analyzes data

---

**Last Updated:** 2026-01-27  
**Test Suite Version:** 1.2.0  
**Compatible with:** HA Cursor Agent v2.10.39+

