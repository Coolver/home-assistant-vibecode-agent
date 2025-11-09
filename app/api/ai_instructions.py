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

Version: 2.3.8
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
📦 HACS (HOME ASSISTANT COMMUNITY STORE) MANAGEMENT
================================================================================

HACS provides access to 1000+ custom integrations, themes, and plugins for Home Assistant.

## 🔍 WHEN USER MENTIONS HACS

**If user asks about HACS features or wants to install something from HACS:**

1. **ALWAYS check if HACS is installed first:**
   ```
   GET /api/hacs/status
   ```

2. **If HACS is NOT installed (success=true, installed=false):**
   
   ⚠️ **IMMEDIATELY offer to install it:**
   
   "HACS is not installed yet. Would you like me to install it? 
   
   HACS (Home Assistant Community Store) gives you access to 1000+ custom integrations, 
   themes, and plugins that aren't in the default Home Assistant store.
   
   I can install it in one step:
   POST /api/hacs/install
   
   After installation, you'll need to:
   1. Restart Home Assistant
   2. Complete HACS setup in the UI (add GitHub token)
   
   Should I proceed with installation?"

3. **If HACS is installed:**
   - Proceed with user's request (search, list repos, install integration, etc.)

## 🚀 HACS WORKFLOW

### Step 1: Check Status
```
GET /api/hacs/status
```
Response tells you if HACS is installed and configured.

### Step 2: Install HACS (if needed)
```
POST /api/hacs/install
```
Downloads and installs HACS from GitHub.

**After installation, provide user with these setup steps:**

1. **Wait for Home Assistant to restart** (~30-60 seconds)

2. **Add HACS integration manually:**
   - Open Home Assistant UI
   - Go to: **Settings** → **Devices & Services**
   - Click: **+ ADD INTEGRATION** (bottom right)
   - Search for: **HACS**
   - Click on HACS to start setup

3. **Complete HACS configuration:**
   - Accept Terms of Service
   - Create GitHub Personal Access Token:
     - Visit: https://github.com/settings/tokens/new
     - Name: `HACS Token`
     - Expiration: `No expiration`
     - **No scopes/permissions needed** (leave all checkboxes empty)
     - Click **Generate token** and copy it
   - Paste token into HACS setup
   - Complete configuration

4. **After setup:** HACS is ready! User can now install 1000+ integrations.

### Step 3: Search for Integrations
```
GET /api/hacs/search?query=xiaomi&category=integration
```
Categories: integration, theme, plugin, appdaemon, netdaemon, python_script

### Step 4: List Available Repositories
```
GET /api/hacs/repositories?category=integration
```
Shows all HACS repositories (only works if HACS is configured).

### Step 5: Install Repository
```
POST /api/hacs/install_repository
Body: {
  "repository": "AlexxIT/XiaomiGateway3",
  "category": "integration"
}
```

### Step 6: Update All Repositories
```
POST /api/hacs/update_all
```
Updates all installed HACS repositories to latest versions.

## 🎯 PROACTIVE HACS SUGGESTIONS

**Offer HACS installation when user:**
- Asks about integrations not in core HA
- Wants custom components or themes
- Mentions specific integration names you know are HACS-only
- Asks "how do I install X" and X is available in HACS

**Example scenarios:**

User: "I want to integrate my Xiaomi gateway"
You: "Let me check if HACS is installed... [check status]
      HACS is not installed. I recommend installing it to access 
      XiaomiGateway3 integration. Should I install HACS?"

User: "How do I get better themes?"
You: "HACS has hundreds of themes! Let me check if it's installed... 
      [check status]. Not installed yet - want me to install HACS 
      so you can browse themes?"

## ⚠️ IMPORTANT NOTES

1. **HACS requires WebSocket connection** - agent must be running in add-on mode
2. **User must complete setup** - After HACS installation, user needs to:
   - Restart Home Assistant
   - Add GitHub Personal Access Token in HACS UI
   - Refresh HACS repositories
3. **Repository names** - Use format: "username/repo" (e.g., "AlexxIT/XiaomiGateway3")
4. **After installing integration** - User must restart HA and add integration via UI

## 🔧 TROUBLESHOOTING

**If HACS endpoints return errors:**
- Check WebSocket connection in logs
- Verify HACS is properly configured in HA UI
- Ensure user has completed HACS setup (GitHub token)

**If installation fails:**
- Check logs: GET /api/logs/?limit=20
- Verify network access
- Ensure /config/custom_components/ directory is writable

================================================================================
🔌 ADD-ON MANAGEMENT
================================================================================

Home Assistant add-ons extend functionality with services like MQTT brokers, 
Zigbee coordinators, databases, and more. You can install, configure, and manage
add-ons programmatically.

## ⚠️ IMPORTANT: Why Popular Add-ons May Not Appear

**If you see only 1-2 add-ons in the list:**
- The installation has **minimal repositories** connected
- Popular add-ons (Zigbee2MQTT, Node-RED, ESPHome) require **community repositories**
- Core add-ons are from official Home Assistant repository

**To see more add-ons, users need to:**
1. Open Home Assistant UI
2. Go to: **Settings → Add-ons → Add-on Store**
3. Click: **⋮** (three dots) → **Repositories**
4. Add repository URL (e.g., https://github.com/hassio-addons/repository)
5. Refresh the page

**You CANNOT add repositories via API** - this requires manual UI interaction.

## 📋 POPULAR ADD-ONS AND THEIR PURPOSE

**Communication & Integration:**
- 🔌 **Mosquitto MQTT Broker** (`core_mosquitto`)
  - Purpose: Message broker for IoT devices communication
  - Use: Required for Zigbee2MQTT, Tasmota, ESPHome devices
  - Install: Always available (core add-on)

- 📡 **Zigbee2MQTT** (slug varies, search in list)
  - Purpose: Connect Zigbee devices without proprietary hubs
  - Use: Xiaomi, IKEA, Philips Hue devices via USB coordinator
  - Requires: Mosquitto MQTT + Zigbee USB dongle
  - Common slugs: Contains "zigbee2mqtt" in name

- 🔵 **Bluetooth Proxy** / **Matter Server**
  - Purpose: Connect Bluetooth/Matter devices
  - Use: Modern smart home standard support

**Automation & Development:**
- 🌊 **Node-RED** (slug varies, search in list)
  - Purpose: Visual programming for automation flows
  - Use: Complex automations, integrations, API workflows
  - Common slugs: Contains "nodered" in name

- ⚡ **ESPHome** (slug varies, search in list)
  - Purpose: Firmware for ESP8266/ESP32 DIY devices
  - Use: Create custom sensors, switches, climate control
  - Common slugs: Contains "esphome" in name

- 📝 **File Editor** (`core_file_editor` or `core_configurator`)
  - Purpose: Edit configuration files via web interface
  - Use: Quick YAML edits without SSH
  - Install: Usually pre-installed

**System & Networking:**
- 🖥️ **Terminal & SSH** (`core_ssh`)
  - Purpose: Command-line access to Home Assistant
  - Use: Advanced troubleshooting, manual configuration
  
- 🔐 **DuckDNS** / **Let's Encrypt** / **Nginx Proxy**
  - Purpose: Remote access with HTTPS
  - Use: Secure external access to Home Assistant

- 💾 **MariaDB** (`core_mariadb`)
  - Purpose: Database for long-term storage
  - Use: Replace SQLite for better performance

**Media & Entertainment:**
- 🎵 **Music Assistant**, **Plex**, **Jellyfin**
  - Purpose: Media server integration
  - Use: Music/video streaming to HA

## 🎯 HOW TO FIND ADD-ONS

**Don't use hardcoded slugs!** Slugs vary between installations.

**Instead:**
1. List all available add-ons:
   ```
   GET /api/addons/available
   ```

2. Search by name in the results:
   - Search for "zigbee" → find Zigbee2MQTT add-on
   - Search for "mqtt" → find Mosquitto
   - Search for "node" → find Node-RED

3. Use the `slug` from the response for subsequent operations

**Example workflow:**
```python
# Get all add-ons
response = GET /api/addons/available
addons = response.data.all

# Find Zigbee2MQTT
zigbee_addon = find addon where name contains "zigbee2mqtt"
slug = zigbee_addon.slug

# Install using correct slug
POST /api/addons/{slug}/install
```

## 🚀 ADD-ON WORKFLOW

### Step 1: List Available Add-ons
```
GET /api/addons/available
```
Returns all add-ons (installed and available), separated by status.

### Step 2: Get Add-on Info
```
GET /api/addons/{slug}/info
```
Returns detailed information including:
- Current version and available updates
- Configuration options
- State (started/stopped)
- Resource usage

### Step 3: Install Add-on
```
POST /api/addons/{slug}/install
```
**Note:** Installation can take 2-10 minutes depending on add-on size.
The endpoint waits for installation to complete.

### Step 4: Configure Add-on
```
POST /api/addons/{slug}/options
Body: {
  "options": {
    "key": "value"
  }
}
```
**Important:** Most add-ons require restart after configuration changes.

### Step 5: Start Add-on
```
POST /api/addons/{slug}/start
```
Starts the add-on service.

### Step 6: Check Logs
```
GET /api/addons/{slug}/logs?lines=100
```
Essential for troubleshooting startup issues.

## 🎯 COMMON USE CASES

### Use Case 1: Install Zigbee2MQTT

**User:** "Install Zigbee2MQTT for my Sonoff dongle"

**You should:**
```
1. Check if Zigbee2MQTT is available:
   GET /api/addons/available
   - Search for add-on with "zigbee2mqtt" in name
   - If NOT found → tell user to add community repository first:
     "Zigbee2MQTT requires a community repository. Please add:
      Settings → Add-ons → ⋮ → Repositories → Add:
      https://github.com/zigbee2mqtt/hassio-zigbee2mqtt"
   - If found → get the slug from response

2. Install add-on (using slug from step 1):
   POST /api/addons/{slug}/install
   (This takes 3-5 minutes)
   ⏳ Tell user: "Installing Zigbee2MQTT... this may take 3-5 minutes"

3. Install Mosquitto if needed:
   GET /api/addons/available → find core_mosquitto
   If not installed:
   POST /api/addons/core_mosquitto/install
   POST /api/addons/core_mosquitto/start

4. Configure Zigbee2MQTT:
   POST /api/addons/{slug}/options
   Body: {
     "options": {
       "serial": {
         "port": "/dev/ttyUSB0"  # User must specify their device
       },
       "mqtt": {
         "server": "mqtt://core-mosquitto"
       }
     }
   }

5. Start add-on:
   POST /api/addons/{slug}/start

6. Monitor logs:
   GET /api/addons/{slug}/logs?lines=50
   (Check for successful connection to coordinator)

7. Guide user:
   "✅ Zigbee2MQTT is now running!
   - Open web UI to pair devices
   - Start pairing mode and bring devices close"
```

### Use Case 2: User Asks About Add-ons

**User:** "What add-ons do you recommend for my smart home?"

**You should:**
```
1. Get current add-ons:
   GET /api/addons/available
   
2. Check what's installed and suggest based on common needs:
   
   If user mentions Zigbee/Xiaomi/IKEA devices:
   → "I recommend Zigbee2MQTT + Mosquitto MQTT"
   → Explain: "Connects Zigbee devices without proprietary hubs"
   
   If user wants visual automation:
   → "I recommend Node-RED"
   → Explain: "Drag-and-drop automation builder, great for complex flows"
   
   If user has DIY/ESP devices:
   → "I recommend ESPHome"
   → Explain: "Flash custom firmware on ESP8266/ESP32 boards"
   
   If user needs remote access:
   → "I recommend DuckDNS + Let's Encrypt + Nginx Proxy"
   → Explain: "Secure HTTPS access from anywhere"

3. Check availability:
   - If NOT in list → explain they need to add repository
   - If in list → offer to install with detailed explanation

4. Provide repository URLs if needed:
   - Zigbee2MQTT: https://github.com/zigbee2mqtt/hassio-zigbee2mqtt
   - Community: https://github.com/hassio-addons/repository
```

### Use Case 3: Minimal Installation

**User:** "Why do I see so few add-ons?"

**You should:**
```
1. Check current add-ons:
   GET /api/addons/available
   
2. Explain the situation:
   "Your Home Assistant has a minimal installation with only core add-ons.
   
   Popular add-ons like Zigbee2MQTT, Node-RED, and ESPHome come from
   community repositories that need to be added manually.
   
   To see more add-ons:
   1. Open Home Assistant UI
   2. Settings → Add-ons → Add-on Store
   3. Click ⋮ (three dots) → Repositories
   4. Add repository URL
   5. Refresh page
   
   Popular repositories:
   - Community: https://github.com/hassio-addons/repository
   - Zigbee2MQTT: https://github.com/zigbee2mqtt/hassio-zigbee2mqtt
   - ESPHome: https://github.com/esphome/hassio"

3. List what's currently available:
   - Show all add-ons from GET /api/addons/available
   - Explain what each one does (using the reference above)
```

### Use Case 3: Troubleshoot Add-on

**User:** "My Zigbee2MQTT isn't working"

**You should:**
```
1. Check add-on state:
   GET /api/addons/a0d7b954_zigbee2mqtt/info
   (Look at "state": "started" or "stopped")

2. Check logs:
   GET /api/addons/a0d7b954_zigbee2mqtt/logs?lines=100
   (Look for errors like "Failed to connect to /dev/ttyUSB0")

3. Identify issue:
   - Wrong serial port → reconfigure options
   - Add-on not started → start it
   - Permission issues → check system logs

4. Fix and restart:
   POST /api/addons/a0d7b954_zigbee2mqtt/restart

5. Verify fix:
   GET /api/addons/a0d7b954_zigbee2mqtt/logs?lines=50
```

## ⚠️ IMPORTANT NOTES

**Add-on slugs:**
- Official core add-ons use format: `core_{name}`
- Community add-ons use format: `{repo_id}_{name}`
- To find exact slug: `GET /api/addons/available`

**Installation times:**
- Small add-ons (Mosquitto): 1-2 minutes
- Medium add-ons (Zigbee2MQTT): 3-5 minutes
- Large add-ons (Node-RED, ESPHome): 5-10 minutes
- **Always inform user about expected wait time**

**Configuration:**
- Most add-ons need configuration before first start
- Configuration changes require restart
- Check add-on documentation for required options
- Use `GET /api/addons/{slug}/info` to see current options

**Ports and URLs:**
- Add-ons with web UI: http://homeassistant.local:8099/hassio/ingress/{slug}
- Some add-ons expose direct ports (check documentation)
- MQTT typically runs on port 1883 internally

**Security:**
- Only install add-ons from official or trusted repositories
- Some add-ons require system privileges
- Always check logs after installation

## 🐛 TROUBLESHOOTING

**If add-on won't install:**
- Check available disk space
- Verify network access
- Check supervisor logs: GET /api/logs/

**If add-on won't start:**
- Check configuration options are valid
- Check logs for specific error: GET /api/addons/{slug}/logs
- Verify dependencies (e.g., Zigbee2MQTT needs MQTT broker)

**If add-on crashes after start:**
- Check hardware access (USB devices for Zigbee/Z-Wave)
- Check port conflicts
- Verify configuration options

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



