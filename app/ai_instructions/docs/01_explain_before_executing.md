# EXPLAIN BEFORE EXECUTING

**CRITICAL: Always explain what you're about to do BEFORE calling MCP tools!**

**Why:** Users need to understand your plan before you execute it.

---

## Format

```
I'm going to [high-level goal]:
1. [Tool name] - [what it does]
2. [Tool name] - [what it does]
3. [Expected result]

Proceeding...
```

---

## Examples

### ✅ Good Example: Dashboard Creation

```
User: "Create a dashboard"

AI: "I'll create a custom dashboard for your climate system:
1. ha_analyze_entities_for_dashboard - Get your devices and sensors
2. Generate YAML based on your requirements
3. ha_apply_dashboard - Create and register the dashboard
4. ha_restart - Restart HA to make it visible

Proceeding..."

[then executes tools]
```

### ✅ Good Example: Add-on Installation

```
User: "Install Zigbee2MQTT"

AI: "I'll install and configure Zigbee2MQTT:
1. ha_list_store_addons - Check if it's available
2. ha_install_addon - Install Zigbee2MQTT add-on
3. ha_addon_logs - Monitor installation progress
4. ha_set_addon_options - Configure for your USB dongle

This will take ~2-3 minutes. Proceeding..."

[then executes tools]
```

### ❌ Bad Example

```
User: "Create dashboard"
AI: [calls ha_analyze_entities_for_dashboard without explanation]
```

---

## Exceptions

**Simple read-only checks don't need explanation:**
- `ha_check_config` (quick validation)
- `ha_get_logs` (when user asks for logs)
- `ha_get_entity_state` (checking specific entity)


