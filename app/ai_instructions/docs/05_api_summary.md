# API ENDPOINTS SUMMARY

## Quick Reference

| Category | Endpoints |
|----------|-----------|
| **Files** | GET/POST /api/files/read, /api/files/write, /api/files/list, /api/files/delete |
| **Entities** | GET /api/entities/list, /api/entities/state/{entity_id} |
| **Helpers** | GET/POST/DELETE /api/helpers/list, /api/helpers/create, /api/helpers/delete |
| **Automations** | GET/POST/DELETE /api/automations/list, /api/automations/create, /api/automations/delete |
| **Scripts** | GET/POST/DELETE /api/scripts/list, /api/scripts/create, /api/scripts/delete |
| **HACS** | POST /api/hacs/install, /api/hacs/search, /api/hacs/list |
| **Add-ons** | GET/POST /api/addons/list, /api/addons/install, /api/addons/start, /api/addons/stop |
| **Dashboard** | GET/POST/DELETE /api/lovelace/analyze, /api/lovelace/apply, /api/lovelace/delete |
| **System** | POST /api/system/reload, /api/system/check_config, /api/system/restart |
| **Backup** | POST /api/backup/commit, /api/backup/rollback |
| **Logs** | GET /api/logs/ |
| **Config entries** | GET /api/config_entries/list, POST /api/config_entries/flow/start, POST/DELETE /api/config_entries/flow/{flow_id}, POST /api/config_entries/options_flow/start, POST/DELETE /api/config_entries/options_flow/{flow_id}, POST /api/config_entries/{entry_id}/reload, DELETE /api/config_entries/{entry_id}?confirm=true |
| **Registries** | POST /api/registries/entities/update (name, area_id, new_entity_id, disabled, hidden, ...) |
| **Health** | GET /api/health |

**Full interactive documentation:** http://homeassistant.local:8099/docs

## Config flows (UI dialogs)

Anything the Home Assistant UI does through a dialog (Add integration, Create helper,
Configure) is a config flow or options flow:

1. Start it: `POST /api/config_entries/flow/start` with `{"handler": "<domain>"}`.
2. Read the returned step. `form`: fill the fields in `data_schema`. `menu`: pick one of `menu_options` with `{"next_step_id": "<option>"}`.
3. Submit: `POST /api/config_entries/flow/{flow_id}` with `{"user_input": {...}}`. Repeat until the type is `create_entry` (done) or `abort` (read `reason`).
4. To give up halfway, `DELETE /api/config_entries/flow/{flow_id}`.

Example, turning a smart plug into a light ("Change device type of a switch"):
`{"handler": "switch_as_x"}`, then `{"user_input": {"entity_id": "switch.tv", "target_domain": "light"}}`.
The new entity id may get the area as a prefix (e.g. `light.vardagsrum_tv`); rename it with
`/api/registries/entities/update` if automations expect another id.

Explain to the user before deleting a config entry: it removes the integration and all its entities.



























