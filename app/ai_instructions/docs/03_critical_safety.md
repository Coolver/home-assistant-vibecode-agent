# CRITICAL: READ THESE INSTRUCTIONS BEFORE MAKING ANY CHANGES

## 1️⃣ ANALYSIS PHASE (MANDATORY - DO THIS FIRST)

Before ANY modifications, you MUST:

1. **Read current configuration:**
   ```
   GET /api/files/read?path=configuration.yaml
   GET /api/files/read?path=automations.yaml
   GET /api/files/read?path=scripts.yaml
   ```

2. **Identify Home Assistant version:**
   - Check configuration.yaml for version info
   - Look for 'homeassistant:' section
   - Note custom integrations

3. **Analyze existing format:**
   - YAML structure and indentation
   - Entity naming conventions (entity_id format)
   - Existing helper patterns
   - Automation syntax (trigger/condition/action)

4. **Query current entities:**
   ```
   GET /api/entities/list
   ```
   - Understand user's devices
   - Identify available domains (climate, light, switch, etc.)
   - Check entity_id patterns

---

## 2️⃣ COMPATIBILITY VERIFICATION

⚠️ **YOUR TRAINING DATA MAY BE OUTDATED**

1. Compare your knowledge with user's actual HA version:
   - HA frequently changes YAML syntax
   - Features get deprecated between versions
   - New integrations have different formats

2. Red flags - STOP and ask user:
   - Unsure about syntax for their HA version
   - Configuration format looks different from your knowledge
   - Unfamiliar integrations or entity patterns

3. When in doubt:
   - Ask user for confirmation
   - Show what you plan to do FIRST
   - Provide alternative approaches

---

## 3️⃣ SAFETY PROTOCOLS (MANDATORY)

**⚠️ CRITICAL: At the START of EVERY user request, create a checkpoint:**

1. **Create checkpoint (FIRST THING - before any analysis or changes):**
   ```
   ha_create_checkpoint(user_request="[Brief description of what user asked for]")
   ```
   This will:
   - Save current state with a commit
   - Create a tag with timestamp (e.g., `checkpoint_20251123_194530`)
   - Disable auto-commits during request processing
   - Allow easy rollback if something goes wrong

2. **At the END of request processing:**
   ```
   ha_end_checkpoint()
   ```
   This commits anything still waiting and closes the checkpoint.

**Note:** Each write is committed when it happens, including while a checkpoint is open. `ha_end_checkpoint` saves whatever is still uncommitted. Forgetting either call does not drop the edit.

Do not read or write `secrets.yaml`, key or certificate files, or Home Assistant credential storage (`.storage/core.config_entries`, `.storage/auth*`, `.storage/http*`, `.storage/cloud`, `.storage/application_credentials`). The file API refuses them. Other `.storage` files, including dashboards, stay readable.

Before ANY write operation (if checkpoint was not created):

2. **Show user your plan:**
   ```
   "I'm about to:
   - Create 3 input_boolean helpers
   - Add 2 automations to automations.yaml
   - Create 1 script in scripts.yaml
   
   This will enable [feature]. Should I proceed?"
   ```

3. Wait for confirmation if changes are significant

4. Make changes incrementally:
   - One component at a time
   - Verify each step before next
   - Don't bulk-create without testing

---

## 4️⃣ MODIFICATION WORKFLOW (FOLLOW EXACTLY)

When modifying configuration files:

### Step-by-Step Process:

**1. CREATE BACKUP (always first):**
```
POST /api/backup/commit
{"message": "Backup before [your changes description]"}
```

**2. MAKE ALL CHANGES:**
```
POST /api/files/write (automations.yaml)
POST /api/files/write (scripts.yaml)
POST /api/helpers/create (if needed)
```

⚠️ **IMPORTANT:** These do NOT auto-reload! This is intentional.

**3. CHECK CONFIGURATION VALIDITY:**
```
POST /api/system/check-config
```

**IF check fails:**
- ❌ STOP immediately
- Show errors to user
- Offer rollback: `POST /api/backup/rollback/{commit_hash}`
- **DO NOT reload!**

**IF check passes:**
- ✅ Continue to step 4

**4. RELOAD COMPONENTS:**
```
POST /api/system/reload?component=automations
POST /api/system/reload?component=scripts
```

Or reload everything:
```
POST /api/system/reload?component=all
```

**5. VERIFY CHANGES APPLIED:**
```
GET /api/automations/list
GET /api/scripts/list
```

**6. FINAL COMMIT:**
```
POST /api/backup/commit
{"message": "Applied changes: [description]"}
```

---

## 5️⃣ POST-MODIFICATION VERIFICATION

After making changes, ALWAYS provide:

1. **Summary of modifications:**
   - ✅ Created: [list entities]
   - ✅ Modified: [list files]
   - ✅ Deleted: [list removed items]

2. **Direct verification links:**
   - Automations: http://homeassistant.local:8123/config/automation
   - Scripts: http://homeassistant.local:8123/config/script
   - Helpers: http://homeassistant.local:8123/config/helpers
   - Entities: http://homeassistant.local:8123/config/entities
   - Logs: http://homeassistant.local:8123/config/logs

3. **Testing instructions**

4. **Rollback command** (if needed)

---

## 6️⃣ GIT ROLLBACK WORKFLOW

**When rolling back to previous commit:**

1. **Check available commits:**
   ```
   ha_git_history (limit=20)
   ```

2. **Rollback to commit:**
   ```
   ha_git_rollback (commit_hash="abc123")
   ```

3. **⚠️ CRITICAL: Full restart required after rollback!**
   ```
   ha_restart
   ```
   
   **Why full restart, not reload?**
   - Rollback restores FILES (automations.yaml, dashboards, scripts, etc)
   - Core reload only reloads configuration.yaml
   - Full restart re-reads ALL files from disk
   
   **Do NOT use:**
   - ❌ ha_reload_config (will miss file changes!)
   - ❌ Component reloads (insufficient)
   
   **Always use:**
   - ✅ ha_restart (full HA restart)

4. **Wait for restart (~30-60 seconds)**

5. **Verify changes applied:**
   - Check files are restored
   - Verify entities in UI
   - Test functionality

## 🚫 NEVER DO THESE THINGS

- ❌ Skip reading current configuration
- ❌ Use syntax from training data without verification
- ❌ Modify production systems without backups
- ❌ **Reload without checking config first** - ALWAYS check-config before reload!
- ❌ **Auto-reload after every file write** - batch changes, reload once at the end
- ❌ **Use reload after git rollback** - ALWAYS use full restart after rollback!
- ❌ Ignore configuration check errors
- ❌ Bulk-create entities without incremental testing
- ❌ Assume your knowledge is current - USER'S FILES = SOURCE OF TRUTH
- ❌ Skip the 6-step modification workflow above

---

## ✅ BEST PRACTICES

- ✅ Read before write - always
- ✅ Backup before change - always
- ✅ Verify after modify - always
- ✅ Provide links for visual verification
- ✅ Test incrementally
- ✅ Explain in plain language
- ✅ Give user control - ask before major changes
- ✅ Show file diffs when modifying YAML
- ✅ Validate YAML syntax before applying







