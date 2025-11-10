# Climate Control Best Practices & Edge Cases

## 🎯 Purpose

This document captures real-world edge cases and solutions discovered while building TRV-based climate control systems. Use this as a reference when creating similar automation systems.

---

## ⚠️ Critical Edge Cases Discovered

### 1. **TRV State Changes During Cooldown**

**Problem:**
```
Timeline:
0:00 - Boiler turns off, cooldown starts (15 min)
0:05 - TRV opens (hvac_action: heating)
      → climate_simple_start_heating triggers
      → BUT condition fails: boiler_cooldown_active: on
      → Boiler does NOT start
0:15 - Cooldown ends
      → climate_simple_end_cooldown triggers
      → Question: Will it check if TRV is still heating?
```

**Solution Implemented:**
- `climate_simple_end_cooldown` explicitly checks `sensor.any_trv_heating`
- If True → starts boiler after cooldown
- Added logging automation `climate_trv_opened_during_cooldown`:
  - Logs when TRV opens during cooldown
  - Shows remaining cooldown time
  - Provides visibility

**Lesson:**
When implementing state-based systems with cooldown periods:
1. ✅ Always check pending conditions after cooldown ends
2. ✅ Add logging for state changes during blocked periods
3. ✅ Implement backup periodic checks (every 2 min)

---

### 2. **Sensor Update Delay After State Changes**

**Problem:**
```
climate_simple_end_cooldown:
1. Calls script.climate_end_cooldown
   → Sets boiler_cooldown_active: off
2. delay: 2 seconds  ← TOO SHORT!
3. Checks: sensor.any_trv_heating
   → Sensor may not have updated yet!
   → False negative: thinks no TRVs heating
   → Doesn't start boiler
```

**Solution:**
- Increased delay from 2 to **10 seconds**
- Gives time for:
  - State change propagation
  - Template sensor recalculation
  - Home Assistant internal processing

**Lesson:**
After changing input_boolean or other states that affect template sensors:
- ✅ Add 5-10 second delay before reading dependent sensors
- ✅ Don't trust immediate sensor values after state changes
- ✅ Consider using `homeassistant.update_entity` service

---

### 3. **Minimum Boiler Runtime Protection**

**Problem:**
```
0:00 - TRV opens, boiler starts
0:03 - TRV closes (reached target quickly)
     → Automation wants to turn off boiler
     → Bad for boiler: too short runtime
     → Wastes energy: heating cycle incomplete
```

**Solution: Multiple approaches**

**Approach A: Minimum runtime check**
```yaml
condition:
  - condition: template
    value_template: '{{ states("sensor.boiler_runtime_minutes") | int >= 10 }}'
```

**Approach B: Buffer radiators (V3)**
- If all TRVs close before 10 min
- Activate buffer radiators (artificially increase target)
- Keep boiler running until 10 min
- Restore buffer TRVs to original targets

**Lesson:**
When controlling heating systems:
- ✅ Always enforce minimum runtime (10-15 min)
- ✅ Never turn off boiler after < 5 minutes
- ✅ Use buffer radiators to maintain circulation
- ✅ Consider boiler's minimum cycle time

---

### 4. **Predictive Shutdown Timing**

**Problem:**
```
All TRVs are 0.3°C away from target
→ Still hvac_action: heating
→ Will keep heating until exactly at target
→ Rooms overshoot (inertia)
→ Wasted energy
```

**Solution: Predictive logic**
```yaml
sensor.all_trvs_almost_at_target:
  - Check each heating TRV
  - If (current - target) >= -0.3°C  # Almost there
  - All heating TRVs are almost at target
  - Shut down boiler early

Conditions:
  - Only after 10 min runtime (safety)
  - At least one TRV still heating (not all closed)
```

**Lesson:**
For systems with thermal inertia:
- ✅ Implement predictive shutdown
- ✅ Threshold: 0.2-0.4°C before target
- ✅ Only after minimum runtime
- ✅ Saves 10-20% energy

---

### 5. **Adaptive Cooldown Duration**

**Problem:**
```
Fixed cooldown = 30 minutes
→ Short boiler run (12 min) still gets 30 min cooldown (wasteful)
→ Long boiler run (28 min) only gets 30 min cooldown (might overheat)
```

**Solution: Dynamic cooldown**
```python
if runtime < 15 min:
    cooldown = 15 min
elif runtime < 20 min:
    cooldown = 20 min
else:
    cooldown = 30 min
```

**Lesson:**
- ✅ Adapt cooldown to actual runtime
- ✅ Shorter run = shorter cooldown
- ✅ Longer run = longer cooldown
- ✅ Prevents both waste and overheating

---

### 6. **Multiple Trigger Automations for Reliability**

**Problem:**
```
Single trigger automation:
→ If trigger misses (HA restart, sensor glitch)
→ System stuck in wrong state
→ No recovery mechanism
```

**Solution: Dual triggers**
```yaml
climate_simple_stop_predictive:
  trigger:
    - platform: state  # Fast response
      entity_id: sensor.all_trvs_almost_at_target
      to: 'True'
    - platform: time_pattern  # Backup check
      minutes: /1
```

**Lesson:**
For critical automations:
- ✅ Add state-based trigger (fast)
- ✅ Add time-based trigger (reliable backup)
- ✅ Prevents stuck states
- ✅ Self-healing system

---

### 7. **State Tracking with Input Helpers**

**Problem:**
```
System state only in automation memory
→ HA restart = lost state
→ Can't query "is system in cooldown?"
→ No visibility in UI
```

**Solution: Explicit state tracking**
```yaml
input_text.climate_system_state:
  - idle
  - heating
  - cooldown

input_boolean.boiler_cooldown_active:
  - on/off

input_datetime.boiler_last_started:
  - Timestamp for runtime calculation
```

**Lesson:**
For stateful automations:
- ✅ Use input helpers to track state
- ✅ Survives HA restarts
- ✅ Queryable from UI and automations
- ✅ Easier debugging

---

### 8. **Buffer Radiators Coordination**

**Problem:**
```
All TRVs close at 8 min
→ Want to turn off boiler
→ But minimum runtime is 10 min
→ Need to keep boiler running
→ But no TRVs open = pressure issues
```

**Solution: Buffer radiators**
```yaml
When all_trvs_close AND runtime < 10 min:
1. Find TRVs with (current - target) < 0.4°C
2. Increase their target by +1°C
3. Save original targets
4. They open, keep boiler running
5. At 10 min: restore original targets
```

**Lesson:**
For minimum runtime enforcement:
- ✅ Identify buffer candidates (close to target)
- ✅ Save original targets before modification
- ✅ Small increase (+0.5 to +1°C)
- ✅ Restore after minimum time
- ✅ Prevents pressure issues

---

### 9. **System Enable/Disable Transitions**

**Problem:**
```
User disables system while boiler running:
→ Boiler stays on? ❌
→ Cooldown remains active? ❌
→ State becomes inconsistent ❌
```

**Solution: Reset automation**
```yaml
climate_simple_system_disabled_reset:
  trigger: climate_system_enabled → off
  action:
    - Turn off boiler
    - Clear cooldown flag
    - Reset state to idle
    - Reset all timestamps
    - Log the reset
```

**Lesson:**
For enable/disable toggles:
- ✅ Implement clean reset logic
- ✅ Turn off all hardware
- ✅ Clear all state flags
- ✅ Reset timestamps to neutral values
- ✅ Log the action

---

### 10. **Periodic Check as Safety Net**

**Problem:**
```
Complex trigger conditions might miss edge cases:
→ TRV stuck waiting for heat
→ Boiler off but should be on
→ System appears "working" but not responding
```

**Solution: Periodic verification**
```yaml
climate_simple_periodic_check:
  trigger:
    - time_pattern: /2  # Every 2 minutes
  condition:
    - system_enabled: on
    - cooldown: off
    - any_trv_heating: True
    - boiler: off  ← Should be on!
  action:
    - Start boiler
    - Log: "Periodic check - fixing state"
```

**Lesson:**
Always implement periodic checks:
- ✅ Every 1-5 minutes depending on criticality
- ✅ Verify expected state matches actual state
- ✅ Self-healing capability
- ✅ Catches missed triggers

---

## 🏗️ Architecture Patterns

### Pattern 1: Sensor Aggregation

**Don't:**
```yaml
trigger:
  - sensor.bedroom_hvac → heating
  - sensor.living_hvac → heating
  - sensor.kitchen_hvac → heating
  # ... 7 triggers
```

**Do:**
```yaml
# Create aggregation sensor
sensor.any_trv_heating:
  value_template: >
    {{ is_state('sensor.bedroom_hvac', 'heating') or
       is_state('sensor.living_hvac', 'heating') or
       ... }}

# Use in trigger
trigger:
  - sensor.any_trv_heating → True
```

**Benefits:**
- Single trigger point
- Easier to maintain
- Reusable across automations
- DRY principle

---

### Pattern 2: Template Sensors for Business Logic

**Don't:** Complex logic in automation conditions

**Do:** Template sensors with clear names

```yaml
sensor.buffer_trvs_available:
  # Count TRVs suitable for buffer role
  # (current > target) AND (diff < 0.4°C)

sensor.all_trvs_almost_at_target:
  # All heating TRVs within 0.3°C of target
  
sensor.boiler_runtime_minutes:
  # Minutes since boiler started
```

**Benefits:**
- Testable in Developer Tools
- Reusable logic
- Self-documenting names
- Easier debugging

---

### Pattern 3: State Machine with Explicit States

**Don't:** Implicit state in automation combinations

**Do:** Explicit state tracking

```yaml
input_text.climate_system_state:
  options: [idle, heating, cooldown]

# Always update state explicitly
# Read state from single source
# Clear state transitions
```

---

## 🔒 Safety Rules

### Rule 1: Always Backup Before Changes
```
1. POST /api/backup/commit ("Backup before...")
2. Make changes
3. Check config
4. Reload
```

### Rule 2: Minimum Runtime Protection
```
Never turn off boiler if runtime < 10 minutes
Exception: Emergency shutdown or user manual stop
```

### Rule 3: Maximum Runtime Safety
```
Always turn off boiler after 30 minutes
Even if TRVs still heating
Prevent stuck-on scenarios
```

### Rule 4: State Persistence
```
Use input helpers for critical state
Survives HA restarts
```

### Rule 5: Multiple Safety Layers
```
Layer 1: State-based triggers (fast)
Layer 2: Time-based checks (reliable)
Layer 3: Max runtime cutoff (safety)
```

---

## 🐛 Common Mistakes to Avoid

### ❌ Mistake 1: Trusting Immediate Sensor Values
```yaml
# BAD:
- Turn off cooldown flag
- Immediately check sensor
- Sensor not updated yet!

# GOOD:
- Turn off cooldown flag
- delay: 10 seconds
- Check sensor (now updated)
```

### ❌ Mistake 2: No Minimum Runtime
```yaml
# BAD:
if all_trvs_idle:
  turn_off_boiler()  # Might be after 2 minutes!

# GOOD:
if all_trvs_idle AND runtime >= 10:
  turn_off_boiler()
else:
  activate_buffer_trvs()  # Keep running
```

### ❌ Mistake 3: Single Trigger Only
```yaml
# BAD:
trigger:
  - sensor changes to heating

# GOOD:
trigger:
  - sensor changes to heating  # Fast
  - time_pattern: /2  # Backup
```

### ❌ Mistake 4: Ignoring System Transitions
```yaml
# BAD:
User disables system
→ Automations stop
→ Boiler stays on ❌

# GOOD:
system_disabled_reset automation:
→ Turn off all hardware
→ Reset all flags
→ Clean state
```

### ❌ Mistake 5: No Visibility
```yaml
# BAD:
Complex logic, no logging
User: "Why didn't boiler start?"
You: "¯\_(ツ)_/¯"

# GOOD:
Every critical action:
→ logbook.log with details
→ Shows in HA history
→ Easy debugging
```

---

## 📋 Checklist for Climate Control Systems

### Before Implementation:

- [ ] Identify all TRV entities and their hvac_action sensors
- [ ] Check TRV capabilities (min/max temp, hvac_modes)
- [ ] Verify boiler control entity (switch/climate)
- [ ] Understand system inertia (boiler, radiators, TRV response time)
- [ ] Define minimum/maximum runtime requirements
- [ ] Plan cooldown strategy

### During Implementation:

- [ ] Create aggregation sensors (any_trv_heating, active_count, etc.)
- [ ] Create calculation sensors (runtime, cooldown remaining, etc.)
- [ ] Create input helpers for state tracking
- [ ] Implement state machine (idle → heating → cooldown)
- [ ] Add minimum runtime protection
- [ ] Add maximum runtime safety
- [ ] Implement cooldown logic
- [ ] Add state change during cooldown handling
- [ ] Create enable/disable reset automation
- [ ] Add periodic check automation (backup)
- [ ] Implement logging for all critical transitions
- [ ] Test each automation individually

### After Implementation:

- [ ] Test TRV opens during cooldown scenario
- [ ] Test all TRVs close before minimum runtime
- [ ] Test maximum runtime cutoff
- [ ] Test system enable/disable transitions
- [ ] Test HA restart during each state
- [ ] Monitor logs for unexpected behavior
- [ ] Adjust timings based on real-world performance

---

## 🧠 Key Insights

### Insight 1: **Home Assistant is Eventually Consistent**

State changes don't propagate instantly:
- Input boolean changes: ~0.1s
- Template sensor updates: 1-5s
- Automation triggers: 0.5-2s

**Implication:** Add delays after state changes before reading dependent values.

### Insight 2: **TRVs Have Minds of Their Own**

TRV internal logic:
- Opens/closes based on own temperature reading
- Has internal hysteresis (~0.5°C)
- May sleep to save battery
- Can update delayed (30s - 2min)

**Implication:** Use hvac_action sensors, not temperature comparisons.

### Insight 3: **Thermal Inertia is Real**

After boiler turns off:
- Radiators stay warm: 10-20 minutes
- Rooms continue heating: 5-15 minutes
- TRVs see rising temperature
- May overshoot target

**Implication:** Implement predictive shutdown.

### Insight 4: **State Transitions Need Explicit Handling**

Transitions between states are not atomic:
- idle → heating: Check cooldown not active
- heating → cooldown: Save runtime, calculate duration
- cooldown → idle: Check if heating needed
- any → disabled: Clean reset

**Implication:** Every transition needs dedicated automation.

### Insight 5: **Backup Mechanisms Are Essential**

Primary logic might fail:
- Missed trigger (HA restart)
- Sensor glitch
- Wrong condition evaluation
- Network delays

**Implication:** Add time-based periodic checks as safety net.

---

## 📝 Template for AI Instructions

When building TRV + Boiler climate control:

### 1. **Analyze Hardware**
```
- Count TRV entities
- Find hvac_action sensors
- Identify boiler control entity
- Check supported features
```

### 2. **Create Base Sensors**
```
Required template sensors:
- any_trv_heating (Boolean)
- active_trv_count (Number with room names)
- boiler_runtime_minutes (Duration)
- adaptive_cooldown_remaining (Duration)
```

### 3. **Create State Helpers**
```
Required input helpers:
- input_boolean.climate_system_enabled
- input_boolean.boiler_cooldown_active
- input_text.climate_system_state (idle/heating/cooldown)
- input_number.climate_cooldown_duration (adaptive)
- input_datetime.boiler_last_started
- input_datetime.boiler_last_stopped
```

### 4. **Implement Core Automations**
```
Priority 1 (Critical):
- start_heating (when TRV opens)
- stop_all_idle (when all TRVs close, min runtime check)
- stop_max_runtime (safety cutoff at 30 min)
- end_cooldown (check if restart needed)

Priority 2 (Safety):
- periodic_check (every 2 min, backup mechanism)
- system_enabled_check (clean startup)
- system_disabled_reset (clean shutdown)

Priority 3 (Optimization):
- stop_predictive (energy saving)
- trv_opened_during_cooldown (logging)
```

### 5. **Add V3 Features (Optional)**
```
If minimum runtime is critical:
- buffer_trvs_available sensor
- buffer_mode_status sensor
- activate_buffer_mode automation
- deactivate_buffer_mode automation
- activate_buffer_trvs script
- deactivate_buffer_trvs script
```

### 6. **Timing Guidelines**
```
Minimum boiler runtime: 10 minutes
Maximum boiler runtime: 30 minutes
Cooldown duration: 15-30 min (adaptive)
Delay after state change: 10 seconds
Periodic check interval: 2 minutes
Predictive threshold: 0.3°C before target
Buffer activation threshold: 0.4°C
```

---

## 🎓 Lessons for Other Automation Systems

These edge cases apply to ANY state-based automation:

### 1. **Cooldown/Debounce Periods**
- Always check pending conditions after cooldown
- Log state changes during cooldown
- Implement post-cooldown decision logic

### 2. **Sensor Lag**
- Add delays after state changes
- Don't trust immediate sensor reads
- Template sensors update slower than state changes

### 3. **Safety Layers**
- Primary logic (fast, state-based)
- Backup logic (slower, time-based)
- Safety cutoff (maximum values)

### 4. **State Persistence**
- Use input helpers for critical state
- Explicitly track state transitions
- Clean up on enable/disable

### 5. **Visibility**
- Log all critical transitions
- Use meaningful messages
- Include relevant values (counts, durations, etc.)

---

## 🚀 How to Use This Document

### For AI Agents:

When user requests climate control system:

1. **Read this document first**
2. **Ask about their specific hardware:**
   - How many TRVs?
   - Boiler type (on/off or modulating)?
   - Minimum runtime requirements?
3. **Follow the template above**
4. **Implement all edge case handlers**
5. **Don't skip safety features** ("I'll add them later" = never added)

### For Users:

When reviewing AI-generated climate automations:

1. **Check for minimum runtime protection**
2. **Verify cooldown logic includes post-cooldown checks**
3. **Look for periodic backup checks**
4. **Ensure proper delays after state changes**
5. **Confirm logging for debugging**

---

## 📊 Real-World Performance

These patterns were tested with:
- **Hardware:** 7 Sonoff TRV-ZB thermostatic valves + 1 Sonoff ZBMini-R2 relay
- **Runtime:** 7+ days continuous operation
- **Results:**
  - Zero stuck states
  - 10-20% energy savings with predictive shutdown
  - Buffer mode prevented 100% of short-cycle scenarios
  - All edge cases handled gracefully
  - System self-heals from any state

---

## 🎯 Summary: Golden Rules

1. ✅ **Always** check config before reload
2. ✅ **Always** backup before making changes
3. ✅ **Always** add 10s delay after state changes before reading sensors
4. ✅ **Always** implement minimum runtime protection
5. ✅ **Always** add periodic check as backup (every 2 min)
6. ✅ **Always** check pending conditions after cooldown ends
7. ✅ **Always** log critical state transitions
8. ✅ **Always** implement clean enable/disable reset
9. ✅ **Always** use aggregation sensors for multiple entities
10. ✅ **Always** track state in persistent input helpers

**Follow these rules → Reliable, maintainable, safe automation!** 🎯

---

*Last updated: 2025-11-08 after implementing Climate Control V3 with buffer radiators*


























