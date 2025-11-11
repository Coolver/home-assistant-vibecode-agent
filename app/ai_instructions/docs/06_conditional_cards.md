# 🎯 CONDITIONAL CARDS IN LOVELACE DASHBOARDS

## Overview

Conditional cards allow you to show/hide cards dynamically based on entity state. This is especially powerful for monitoring dashboards where you only want to see active/relevant information.

---

## ✅ CORRECT PATTERN FOR CONDITIONAL CARDS

### Basic Structure

```yaml
type: conditional
conditions:
  - condition: state
    entity: sensor.example
    state: heating
card:
  type: thermostat
  entity: climate.example_trv
```

**Key Points:**
- `conditions:` is an **array** (always use `-` for each condition)
- Each condition MUST have `condition: state` key
- Each condition has `entity:` and `state:` keys
- The `card:` key contains the card to show when conditions are met
- Multiple conditions use AND logic (all must be true)
- States are typically unquoted (e.g., `heating`, `on`, `off`) unless they contain special characters

---

## 🔥 REAL-WORLD EXAMPLE: HEATING NOW DASHBOARD

**From Commit e8ed8a3b** - Optimal pattern for TRVs in heating state:

### Problem
Show TRV thermostat cards **only** when they are actively heating, not when idle/off.

### Solution
Use dedicated `hvac_action` sensors with state `heating`:

```yaml
title: Heating Now
views:
  - title: Heating Now
    path: heating-now
    icon: mdi:radiator
    cards:
      # Always visible status cards
      - type: vertical-stack
        cards:
          - type: markdown
            content: '# 🔥 Boiler Status & Control'
          - type: entities
            entities:
              - entity: switch.boiler_zbminir2
                name: Boiler Power
              - entity: sensor.boiler_runtime_minutes
                name: Runtime (minutes)
            state_color: true
      
      - type: vertical-stack
        cards:
          - type: markdown
            content: '# ❄️ Cooldown Status'
          - type: entities
            entities:
              - entity: input_boolean.boiler_cooldown_active
                name: Cooldown Active
              - entity: sensor.adaptive_cooldown_remaining_minutes
                name: Remaining Time (minutes)
            state_color: true
      
      - type: vertical-stack
        cards:
          - type: markdown
            content: '# 🏠 Active Heating Summary'
          - type: entities
            entities:
              - entity: sensor.active_trv_count
                name: TRVs Currently Heating
              - entity: sensor.any_trv_heating
                name: Any TRV Heating
            state_color: true
      
      # CONDITIONAL CARDS - Only visible when heating!
      - type: conditional
        conditions:
          - condition: state
            entity: sensor.sonoff_trvzb_hvac_action
            state: heating
        card:
          type: thermostat
          entity: climate.sonoff_trvzb_thermostat
          name: 🔥 Office TRV (Heating)
          show_current_as_primary: true
      
      - type: conditional
        conditions:
          - condition: state
            entity: sensor.sonoff_trvzb_hvac_action_2
            state: heating
        card:
          type: thermostat
          entity: climate.sonoff_trvzb_thermostat_2
          name: 🔥 Living Room TRV (Heating)
          show_current_as_primary: true
      
      - type: conditional
        conditions:
          - condition: state
            entity: sensor.kitchen_trv_hvac_action
            state: heating
        card:
          type: thermostat
          entity: climate.kitchen_trv_thermostat
          name: 🔥 Kitchen TRV (Heating)
          show_current_as_primary: true
      
      # ... repeat for all 7 TRVs
```

### Result
- **No heating** → Shows 3 status sections only
- **1 TRV heating** → Shows 3 status sections + 1 thermostat
- **All 7 heating** → Shows 3 status sections + 7 thermostats
- **Dynamic, clean, focused interface!**

### Important Notes

**Sensor Setup Required:**
- You need `sensor.xxx_hvac_action` sensors that expose the `hvac_action` attribute
- These can be created as template sensors in `configuration.yaml`:

```yaml
template:
  - sensor:
      - name: "Office TRV HVAC Action"
        unique_id: office_trv_hvac_action
        state: "{{ state_attr('climate.office_trv', 'hvac_action') }}"
```

---

## 🎓 ADVANCED PATTERNS

### Pattern 1: Multiple Conditions (AND Logic)

```yaml
type: conditional
conditions:
  - condition: state
    entity: sensor.bedroom_trv_hvac_action
    state_not: unavailable
  - condition: state
    entity: sensor.bedroom_trv_hvac_action
    state: heating
card:
  type: thermostat
  entity: climate.bedroom_trv
```

This shows the card only when:
1. Sensor is available (not offline)
2. AND TRV is actively heating

### Pattern 2: Check Different Entity States

```yaml
type: conditional
conditions:
  - condition: state
    entity: binary_sensor.someone_home
    state: 'on'
  - condition: state
    entity: sensor.office_trv_hvac_action
    state: heating
card:
  type: thermostat
  entity: climate.office_trv
```

This shows office TRV only when someone is home AND it's heating.

### Pattern 3: State Not Equal (Excluding States)

```yaml
type: conditional
conditions:
  - condition: state
    entity: climate.bedroom_trv
    state_not: unavailable
  - condition: state
    entity: climate.bedroom_trv
    state_not: 'off'
card:
  type: thermostat
  entity: climate.bedroom_trv
```

### Pattern 4: Numeric Threshold (Below)

```yaml
type: conditional
conditions:
  - condition: numeric_state
    entity: sensor.battery_level
    below: 20
card:
  type: entity
  entity: sensor.battery_level
  name: ⚠️ Low Battery!
```

### Pattern 5: Numeric Threshold (Above)

```yaml
type: conditional
conditions:
  - condition: numeric_state
    entity: sensor.temperature
    above: 25
card:
  type: sensor
  entity: sensor.temperature
  name: 🔥 High Temperature!
```

### Pattern 6: Creating HVAC Action Sensors

**For TRV heating detection, create template sensors:**

```yaml
template:
  - sensor:
      - name: "Office TRV HVAC Action"
        unique_id: office_trv_hvac_action
        state: "{{ state_attr('climate.office_trv', 'hvac_action') }}"
      
      - name: "Living Room TRV HVAC Action"
        unique_id: living_room_trv_hvac_action
        state: "{{ state_attr('climate.living_room_trv', 'hvac_action') }}"
```

Then use in conditional cards:

```yaml
- type: conditional
  conditions:
    - condition: state
      entity: sensor.office_trv_hvac_action
      state: heating
  card:
    type: thermostat
    entity: climate.office_trv
```

---

## ❌ COMMON MISTAKES TO AVOID

### Mistake 1: Missing `condition:` Key

```yaml
# ❌ WRONG - Missing "condition: state"
type: conditional
conditions:
  - entity: sensor.office_trv_hvac_action
    state: heating
card:
  type: thermostat
  entity: climate.office_trv
```

```yaml
# ✅ CORRECT - Must include "condition: state"
type: conditional
conditions:
  - condition: state
    entity: sensor.office_trv_hvac_action
    state: heating
card:
  type: thermostat
  entity: climate.office_trv
```

### Mistake 2: Forgetting Array Syntax

```yaml
# ❌ WRONG - Missing dash before condition
type: conditional
conditions:
  condition: state
  entity: sensor.office_trv_hvac_action
  state: heating
card:
  type: thermostat
  entity: climate.office_trv
```

```yaml
# ✅ CORRECT - Dash indicates array item
type: conditional
conditions:
  - condition: state
    entity: sensor.office_trv_hvac_action
    state: heating
card:
  type: thermostat
  entity: climate.office_trv
```

### Mistake 3: Wrong Indentation

```yaml
# ❌ WRONG - card nested inside conditions
type: conditional
conditions:
  - condition: state
    entity: sensor.office_trv_hvac_action
    state: heating
    card:
      type: thermostat
      entity: climate.office_trv
```

```yaml
# ✅ CORRECT - card at same level as conditions
type: conditional
conditions:
  - condition: state
    entity: sensor.office_trv_hvac_action
    state: heating
card:
  type: thermostat
  entity: climate.office_trv
```

### Mistake 4: Using Attributes Directly

```yaml
# ❌ WRONG - Cannot check attributes directly in conditions
type: conditional
conditions:
  - condition: state
    entity: climate.office_trv
    attribute: hvac_action
    state: heating
```

```yaml
# ✅ CORRECT - Create template sensor that exposes attribute as state
template:
  - sensor:
      - name: "Office TRV HVAC Action"
        state: "{{ state_attr('climate.office_trv', 'hvac_action') }}"

# Then use in conditional:
type: conditional
conditions:
  - condition: state
    entity: sensor.office_trv_hvac_action
    state: heating
card:
  type: thermostat
  entity: climate.office_trv
```

### Mistake 5: Wrong Condition Type for Numeric Values

```yaml
# ❌ WRONG - Using "state" for numeric comparison
type: conditional
conditions:
  - condition: state
    entity: sensor.battery_level
    state: < 20
```

```yaml
# ✅ CORRECT - Use "numeric_state" for numeric comparisons
type: conditional
conditions:
  - condition: numeric_state
    entity: sensor.battery_level
    below: 20
```

### Mistake 6: Multiple Cards Without Wrapping

```yaml
# ❌ WRONG - Cannot show multiple cards directly
type: conditional
conditions:
  - condition: state
    entity: sensor.office_trv_hvac_action
    state: heating
card:
  - type: thermostat
    entity: climate.office_trv
  - type: sensor
    entity: sensor.temperature
```

```yaml
# ✅ CORRECT - Wrap in vertical-stack or horizontal-stack
type: conditional
conditions:
  - condition: state
    entity: sensor.office_trv_hvac_action
    state: heating
card:
  type: vertical-stack
  cards:
    - type: thermostat
      entity: climate.office_trv
    - type: sensor
      entity: sensor.temperature
```

---

## 📋 CONDITION OPTIONS REFERENCE

### Condition Types

| Condition Type | Purpose | Example |
|----------------|---------|---------|
| `condition: state` | Check exact state or use state modifiers | `state: heating` |
| `condition: numeric_state` | Compare numeric values | `above: 20`, `below: 50` |
| `condition: screen` | Check screen size (mobile/tablet/desktop) | Advanced use |

### State Condition Options

| Option | Purpose | Example |
|--------|---------|---------|
| `state:` | Exact state match | `state: heating` or `state: 'on'` |
| `state_not:` | State not equal | `state_not: unavailable` |

### Numeric State Condition Options

| Option | Purpose | Example |
|--------|---------|---------|
| `above:` | Value above threshold | `above: 20` |
| `below:` | Value below threshold | `below: 50` |

**Important:** 
- Simple states (heating, on, off, idle) can be unquoted
- States with special characters need quotes: `state: 'on'`
- Numeric comparisons use `condition: numeric_state` with `above:`/`below:`

---

## 🎯 WHEN TO USE CONDITIONAL CARDS

### ✅ Good Use Cases

1. **Heating Monitoring** - Show only TRVs that are actively heating
2. **Low Battery Alerts** - Display devices with battery below threshold
3. **Problem Alerts** - Show warnings only when issues exist
4. **Active Media** - Display media players only when playing
5. **Motion Detection** - Show cameras only when motion detected

### ❌ Not Recommended

1. **Static Content** - If card should always show, don't make it conditional
2. **Complex Logic** - If you need OR logic or complex conditions, use templates instead
3. **All Cards Conditional** - Keep some static cards for context

---

## 🔧 DEBUGGING TIPS

### Card Not Showing?

1. **Check entity state** - Use Developer Tools → States to verify actual state
2. **Check entity availability** - Add `state_not: "unavailable"` condition
3. **Check quotes** - States should be quoted: `state: "heat"` not `state: heat`
4. **Check indentation** - YAML is sensitive to indentation
5. **Check array syntax** - Don't forget the dash: `- entity:` not `entity:`

### Test Your Conditions

```yaml
# Add a test card to see when conditions are met
- type: conditional
  conditions:
    - entity: climate.office_trv
      state: "heat"
  card:
    type: markdown
    content: "✅ CONDITION MET - Office is heating!"
```

---

## 📝 TEMPLATE FOR TRV HEATING MONITORING

**Use this template for any TRV heating dashboard:**

### Step 1: Create Template Sensors (in configuration.yaml)

```yaml
template:
  - sensor:
      # Create hvac_action sensor for each TRV
      - name: "Office TRV HVAC Action"
        unique_id: office_trv_hvac_action
        state: "{{ state_attr('climate.office_trv', 'hvac_action') }}"
      
      - name: "Bedroom TRV HVAC Action"
        unique_id: bedroom_trv_hvac_action
        state: "{{ state_attr('climate.bedroom_trv', 'hvac_action') }}"
      
      # Add one sensor per TRV...
```

### Step 2: Create Dashboard with Conditional Cards

```yaml
title: Heating Monitor
views:
  - title: Active Heating
    path: active-heating
    icon: mdi:fire
    cards:
      # Status cards (always visible)
      - type: entities
        title: 🔥 Heating Status
        entities:
          - entity: binary_sensor.boiler_status
            name: Boiler
          - entity: sensor.active_trv_count
            name: Active TRVs
        state_color: true
      
      # CONDITIONAL TRV CARDS
      # Copy this block for each TRV
      - type: conditional
        conditions:
          - condition: state
            entity: sensor.office_trv_hvac_action
            state: heating
        card:
          type: thermostat
          entity: climate.office_trv
          name: 🔥 Office TRV (Heating)
          show_current_as_primary: true
      
      - type: conditional
        conditions:
          - condition: state
            entity: sensor.bedroom_trv_hvac_action
            state: heating
        card:
          type: thermostat
          entity: climate.bedroom_trv
          name: 🔥 Bedroom TRV (Heating)
          show_current_as_primary: true
      
      # Add one conditional block per TRV...
```

**Replace:**
- `office`, `bedroom` with actual room names
- Add one template sensor per TRV in Step 1
- Add one conditional block per TRV in Step 2
- Keep status cards at the top for context

---

## 🎓 SUMMARY: GOLDEN RULES

1. ✅ **ALWAYS include `condition: state`** - This is the most common mistake!
   ```yaml
   conditions:
     - condition: state  # ← Don't forget this!
       entity: sensor.xxx
       state: heating
   ```

2. ✅ **Always use array syntax** - `conditions:` with `-` for each item

3. ✅ **Proper indentation** - `card:` at same level as `conditions:`, not nested

4. ✅ **Use template sensors for attributes** - Can't check `hvac_action` directly, create sensor first

5. ✅ **Choose correct condition type:**
   - `condition: state` for text states (heating, on, off)
   - `condition: numeric_state` for numbers (above, below)

6. ✅ **Test conditions first** - Use Developer Tools → States to verify entity states

7. ✅ **Keep some static cards** - Don't make everything conditional, provide context

8. ✅ **Quote when needed** - Simple states can be unquoted, special chars need quotes

---

**Reference Commit:** `e8ed8a3b` - "Before deleting dashboard: heating-now.yaml"

This pattern was battle-tested and works perfectly for dynamic heating monitoring! 🔥

**Real-world structure from working dashboard:**
```yaml
- type: conditional
  conditions:
    - condition: state
      entity: sensor.office_trv_hvac_action
      state: heating
  card:
    type: thermostat
    entity: climate.office_trv
    name: 🔥 Office TRV (Heating)
```

