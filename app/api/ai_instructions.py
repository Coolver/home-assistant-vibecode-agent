"""
AI Instructions API
Provides detailed instructions for AI assistants (like Cursor AI)
"""
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=["AI Instructions"])

AI_INSTRUCTIONS = """
================================================================================
HA CURSOR AGENT - INSTRUCTIONS FOR AI ASSISTANTS
================================================================================

Version: 2.0.1
Base URL: http://homeassistant.local:8099
Interactive Docs: http://homeassistant.local:8099/docs

================================================================================
CRITICAL: READ THESE INSTRUCTIONS BEFORE MAKING ANY CHANGES
================================================================================

## 1️⃣ ANALYSIS PHASE (MANDATORY - DO THIS FIRST)

Before ANY modifications, you MUST:

1. Read current configuration:
   GET /api/files/read?path=configuration.yaml
   GET /api/files/read?path=automations.yaml
   GET /api/files/read?path=scripts.yaml

2. Identify Home Assistant version:
   - Check configuration.yaml for version info
   - Look for 'homeassistant:' section
   - Note custom integrations

3. Analyze existing format:
   - YAML structure and indentation
   - Entity naming conventions (entity_id format)
   - Existing helper patterns
   - Automation syntax (trigger/condition/action)

4. Query current entities:
   GET /api/entities/list
   - Understand user's devices
   - Identify available domains (climate, light, switch, etc.)
   - Check entity_id patterns

## 2️⃣ COMPATIBILITY VERIFICATION

⚠️ YOUR TRAINING DATA MAY BE OUTDATED

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

## 3️⃣ SAFETY PROTOCOLS (MANDATORY)

Before ANY write operation:

1. Create backup:
   POST /api/backup/commit
   Body: {"message": "Backup before [description]"}

2. Show user your plan:
   "I'm about to:
   - Create 3 input_boolean helpers
   - Add 2 automations to automations.yaml
   - Create 1 script in scripts.yaml
   
   This will enable [feature]. Should I proceed?"

3. Wait for confirmation if changes are significant

4. Make changes incrementally:
   - One component at a time
   - Verify each step before next
   - Don't bulk-create without testing

## 4️⃣ MODIFICATION WORKFLOW (CRITICAL - FOLLOW EXACTLY)

When modifying configuration files (automations.yaml, scripts.yaml, etc.):

### Step-by-Step Process:

1. **CREATE BACKUP (always first):**
   ```
   POST /api/backup/commit
   {"message": "Backup before [your changes description]"}
   ```

2. **MAKE ALL CHANGES:**
   ```
   POST /api/files/write (automations.yaml)
   POST /api/files/write (scripts.yaml)
   POST /api/helpers/create (if needed)
   ... all your modifications ...
   ```
   
   ⚠️ **IMPORTANT:** These do NOT auto-reload! This is intentional.

3. **CHECK CONFIGURATION VALIDITY:**
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

4. **RELOAD COMPONENTS:**
   ```
   POST /api/system/reload?component=automations
   POST /api/system/reload?component=scripts
   ```
   
   Or reload everything:
   ```
   POST /api/system/reload?component=all
   ```

5. **VERIFY CHANGES APPLIED:**
   ```
   GET /api/automations/list
   GET /api/scripts/list
   ```
   Check that your changes are present and active.

6. **FINAL COMMIT:**
   ```
   POST /api/backup/commit
   {"message": "Applied changes: [description]"}
   ```

### Why This Order Matters:

- 🔒 **Backup first** - can rollback if anything fails
- 📝 **Write all changes** - make all modifications together
- ✅ **Check config** - validate BEFORE reloading (safer!)
- 🔄 **Reload once** - faster than reloading after each file
- ✔️ **Verify** - confirm changes are active
- 💾 **Final commit** - mark successful deployment

### Example Workflow:

```
User: "Add automation for lights at sunset"

You:
1. POST /api/backup/commit ("Backup before adding sunset lights automation")
2. Read current automations.yaml
3. Add new automation
4. POST /api/files/write (updated automations.yaml)
5. POST /api/system/check-config
   → If errors: rollback and report
   → If OK: continue
6. POST /api/system/reload?component=automations
7. GET /api/automations/list (verify it's there)
8. POST /api/backup/commit ("Added sunset lights automation")
9. Tell user: "✅ Done! Check: http://homeassistant.local:8123/config/automation"
```

## 5️⃣ POST-MODIFICATION VERIFICATION

After making changes, ALWAYS provide:

1. Summary of modifications:
   ✅ Created: [list entities]
   ✅ Modified: [list files]
   ✅ Deleted: [list removed items]

2. Direct verification links:
   - Automations: http://homeassistant.local:8123/config/automation
   - Scripts: http://homeassistant.local:8123/config/script
   - Helpers: http://homeassistant.local:8123/config/helpers
   - Entities: http://homeassistant.local:8123/config/entities
   - Logs: http://homeassistant.local:8123/config/logs

3. Testing instructions:
   "To test:
   1. Go to Developer Tools → States
   2. Find [entity_id]
   3. [specific test steps]"

4. Rollback command:
   "If something went wrong:
   POST /api/backup/rollback?commit_hash=[hash]
   
   Or say 'rollback' and I'll revert changes."

## 5️⃣ ERROR HANDLING

If any operation fails:

1. Check logs immediately:
   GET /api/logs/?limit=20

2. Check HA configuration:
   POST /api/system/check_config

3. If errors found:
   - Explain what went wrong
   - Offer to rollback: POST /api/backup/rollback
   - Suggest fixes

4. Never leave system in broken state

## 🚫 NEVER DO THESE THINGS

❌ Skip reading current configuration
❌ Use syntax from training data without verification
❌ Modify production systems without backups
❌ **Reload without checking config first** - ALWAYS check-config before reload!
❌ **Auto-reload after every file write** - batch changes, reload once at the end
❌ Ignore configuration check errors
❌ Bulk-create entities without incremental testing
❌ Assume your knowledge is current - USER'S FILES = SOURCE OF TRUTH
❌ Skip the 6-step modification workflow above

## ✅ BEST PRACTICES

✅ Read before write - always
✅ Backup before change - always
✅ Verify after modify - always
✅ Provide links for visual verification
✅ Test incrementally
✅ Explain in plain language
✅ Give user control - ask before major changes
✅ Show file diffs when modifying YAML
✅ Validate YAML syntax before applying

================================================================================
🌡️ CLIMATE CONTROL SYSTEMS - CRITICAL EDGE CASES
================================================================================

**⚠️ MANDATORY: Read CLIMATE_CONTROL_BEST_PRACTICES.md before creating TRV/boiler automations!**

Location: /config/CLIMATE_CONTROL_BEST_PRACTICES.md (in HA Cursor Agent repo)

When user requests climate control automation (TRV + boiler), you MUST:

### 1. Read the Best Practices Document
   ```
   This document contains 10+ real-world edge cases discovered through
   production testing. DO NOT skip these - they prevent system failures!
   ```

### 2. Critical Edge Cases to Handle

   ⚠️ **TRV State Changes During Cooldown**
   - TRV may open while cooldown is active
   - State change won't trigger automation (condition blocks it)
   - MUST check pending TRV states after cooldown ends
   - Solution: Add explicit check in end_cooldown automation

   ⚠️ **Sensor Update Delay**
   - After changing input_boolean, template sensors need time to update
   - 2 seconds is TOO SHORT - use 10 seconds
   - Example: After turning off cooldown flag, wait 10s before checking sensors
   - Solution: Add 10-second delay after state changes

   ⚠️ **Minimum Boiler Runtime**
   - Never turn off boiler before 10 minutes
   - Wastes energy and damages equipment
   - If all TRVs close early, activate buffer radiators
   - Solution: Check runtime >= 10 min in all stop conditions

   ⚠️ **Predictive Shutdown**
   - Don't wait until TRVs reach exact target (overshoot from inertia)
   - Implement early shutdown when TRVs are 0.3°C from target
   - Only after minimum runtime
   - Solution: Create sensor.all_trvs_almost_at_target

   ⚠️ **Multiple Trigger Automations**
   - Single trigger = single point of failure
   - Add time-based backup trigger (every 1-2 minutes)
   - System self-heals from missed triggers
   - Solution: Every critical automation needs dual triggers

### 3. Required Template Sensors

   ```yaml
   sensor.any_trv_heating:
     # Boolean: at least one TRV is heating
   
   sensor.active_trv_count:
     # Number + list of room names currently heating
   
   sensor.boiler_runtime_minutes:
     # Minutes since boiler started (from input_datetime)
   
   sensor.adaptive_cooldown_remaining_minutes:
     # Calculated cooldown time remaining
   ```

### 4. Required Input Helpers

   ```yaml
   input_boolean.climate_system_enabled
   input_boolean.boiler_cooldown_active
   input_text.climate_system_state  # idle/heating/cooldown
   input_number.climate_cooldown_duration  # adaptive
   input_datetime.boiler_last_started
   input_datetime.boiler_last_stopped
   ```

### 5. Core Automations (Non-negotiable)

   **Priority 1 (Critical):**
   - start_heating (when TRV opens, check cooldown)
   - stop_all_idle (when all close, check min runtime)
   - stop_max_runtime (safety cutoff at 30 min)
   - end_cooldown (MUST check if TRVs still heating!)

   **Priority 2 (Safety):**
   - periodic_check (every 2 min, backup mechanism)
   - system_enabled_check (clean startup)
   - system_disabled_reset (clean shutdown)

   **Priority 3 (Optional):**
   - stop_predictive (energy saving)
   - trv_opened_during_cooldown (logging/visibility)

### 6. Timing Guidelines

   ```
   Minimum boiler runtime: 10 minutes (enforced!)
   Maximum boiler runtime: 30 minutes (safety!)
   Cooldown duration: 15-30 min (adaptive based on runtime)
   Delay after state change: 10 seconds (sensor update time)
   Periodic check interval: 2 minutes (backup trigger)
   Predictive threshold: 0.3°C before target
   ```

### 7. Workflow for Climate Control

   ```
   User: "Create TRV automation for my boiler"
   
   You:
   1. "I'll implement climate control with these edge cases: [list critical ones]"
   2. Read CLIMATE_CONTROL_BEST_PRACTICES.md
   3. Identify TRV entities (GET /api/entities/list?domain=climate)
   4. Identify boiler entity (usually switch or climate domain)
   5. Create all required template sensors
   6. Create all required input helpers
   7. Create Priority 1 automations (critical)
   8. Create Priority 2 automations (safety)
   9. Optional: Create Priority 3 (optimization)
   10. Test each automation path with user
   11. Monitor for 24-48 hours, adjust timings
   ```

### 8. Common Mistakes to Avoid

   ❌ No minimum runtime protection → boiler short-cycles
   ❌ No delay after state changes → false sensor readings
   ❌ Single trigger only → system gets stuck
   ❌ No post-cooldown check → TRV heating but boiler off
   ❌ No periodic backup → missed triggers never recover
   ❌ No logging → impossible to debug
   ❌ Fixed cooldown → inefficient (too long/short)

### 9. Testing Checklist

   Before marking complete:
   - [ ] TRV opens during cooldown → logs message, starts after cooldown
   - [ ] All TRVs close before 10 min → buffer radiators activate OR stays on
   - [ ] Maximum runtime reached → boiler turns off
   - [ ] System disabled during heating → clean reset
   - [ ] HA restart during each state → system recovers
   - [ ] Periodic check catches missed trigger → self-heals

### 10. When User Has Climate Control Request

   **DO:**
   ✅ Mention you'll implement proven edge case handling
   ✅ Explain the critical ones (cooldown, minimum runtime, delays)
   ✅ Show which sensors and helpers will be created
   ✅ Implement ALL Priority 1 and 2 automations (not optional!)
   ✅ Add logging for debugging
   ✅ Provide testing instructions

   **DON'T:**
   ❌ Create "simple" version without edge case handling
   ❌ Skip minimum runtime protection ("user can add later")
   ❌ Skip periodic checks ("automations should work")
   ❌ Use 2-second delays ("should be enough")
   ❌ Single triggers only ("time patterns are extra")

### 📚 Full Documentation

   For complete details including:
   - All 10 edge cases with solutions
   - Architecture patterns
   - Safety rules
   - Real-world performance data
   - Templates and examples
   
   Read: CLIMATE_CONTROL_BEST_PRACTICES.md in HA Cursor Agent repo

**🎯 Bottom Line:**
Climate control automation is NOT trivial. These edge cases were discovered
through real production use. Implementing them from the start saves hours of
debugging and prevents system failures.

================================================================================
API ENDPOINTS SUMMARY
================================================================================

Files:        GET/POST /api/files/*
Entities:     GET /api/entities/*
Helpers:      POST /api/helpers/create, DELETE /api/helpers/delete
Automations:  GET/POST/DELETE /api/automations/*
Scripts:      GET/POST/DELETE /api/scripts/*
System:       POST /api/system/reload, /api/system/check_config
Backup:       POST /api/backup/commit, /api/backup/rollback
Logs:         GET /api/logs/
Health:       GET /api/health

Full interactive documentation: http://homeassistant.local:8099/docs

================================================================================
REMEMBER: User trusts you with their home automation. Be careful, thorough,
and always prioritize safety over speed. When in doubt - ASK.
================================================================================
"""


@router.get(
    "/instructions",
    response_class=PlainTextResponse,
    summary="Get AI Assistant Instructions",
    description="Returns detailed instructions for AI assistants on how to safely use this API"
)
async def get_ai_instructions():
    """
    Get complete instructions for AI assistants (like Cursor AI).
    
    This endpoint provides:
    - Safety protocols
    - Step-by-step workflow
    - Best practices
    - Error handling guidelines
    - Links for verification
    
    Returns plain text for easy consumption by AI.
    """
    return AI_INSTRUCTIONS



