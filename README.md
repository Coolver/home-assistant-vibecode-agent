# HA Cursor Agent - Home Assistant Add-on

**AI Agent API for Home Assistant - enables Cursor AI to autonomously manage your HA configuration**

[![Version](https://img.shields.io/badge/version-1.0.2-blue.svg)](https://github.com/Coolver/home-assistant-cursor-agent)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 🎯 What is this?

**HA Cursor Agent** is a Home Assistant Add-on that provides a **REST API** for AI assistants (like Cursor AI) to:

✅ **Read/Write** configuration files (configuration.yaml, automations.yaml, scripts.yaml)  
✅ **Create/Manage** Input Helpers, Automations, Scripts  
✅ **Query** all devices, entities, and their states  
✅ **Reload** components without restarting HA  
✅ **Version control** with Git (automatic backups, rollback)  
✅ **Validate** configuration before applying  
✅ **Monitor** agent activity through logs API  

**Result:** AI can autonomously install and configure complex systems (like smart climate control) without manual copy-pasting! 🚀

---

## 🌟 Features

### 📁 File Management
- List, read, write, append, delete files
- Automatic backup before modifications
- YAML parsing and validation
- Safe path handling (restricted to `/config`)

### 🏠 Home Assistant Integration
- Full access to HA REST API
- List all entities and their states
- Call any HA service
- Reload components (automations, scripts, templates)
- Check configuration validity

### 🔧 Component Management
- Create/Delete Input Helpers (boolean, text, number, datetime, select)
- Create/Delete Automations
- Create/Delete Scripts
- Automatic reload after changes

### 💾 Git Versioning
- Automatic commit on every change
- Backup history (up to 50 commits)
- Rollback to any previous state
- View diffs between versions
- Commit messages for tracking

### 📊 Monitoring
- Agent logs API
- Operation history
- Real-time status
- Health check endpoint

---

## ⚡ Quick Start (5 minutes)

### 1. Add Repository
1. **Settings** → **Add-ons** → **Add-on Store** → **⋮** → **Repositories**
2. Add: `https://github.com/Coolver/home-assistant-cursor-agent`
3. Click **Add**

### 2. Install
1. Refresh the page
2. Find **HA Cursor Agent** → Click **INSTALL**
3. Wait for installation

### 3. Start
1. **Configuration** tab → Keep defaults → **SAVE**
2. **Info** tab → **Start on boot: ON** → **START**
3. Test: `http://homeassistant.local:8099/api/health`

### 4. Get Token
1. Click your **Profile Name** (bottom left) → **Security**
2. **Refresh Tokens** section → **Long-lived access tokens**
3. **CREATE TOKEN**
4. Name: `HA Cursor Agent`
5. **Copy token** and save it securely

### 5. Test API
Open `http://homeassistant.local:8099/docs` and explore! 🎉

---

## 🤖 Using with Cursor AI

This add-on enables **Cursor AI to autonomously manage your Home Assistant** through natural language prompts - no manual copy-pasting needed!

### ⚠️ Important Disclaimer

**This tool is designed for experienced Home Assistant users who understand what they're doing.** 

- ✅ **Always review changes** before applying them to production systems
- ⚠️ **Cursor AI can accidentally break your configuration** if given incorrect instructions or outdated information
- 💾 **Git versioning is enabled by default** - all changes are backed up and can be rolled back
- 🔄 **Test in a safe environment first** if you're new to AI-driven automation
- 📖 **Verify syntax and compatibility** with your Home Assistant version

**Use at your own risk. The automatic backup system minimizes risk but doesn't eliminate it.**

### How to Connect Cursor AI

Once the add-on is installed and running, use this simple prompt:

```
I have HA Cursor Agent running on my Home Assistant.

Token: YOUR_LONG_LIVED_ACCESS_TOKEN
API Base: http://YOUR_HA_IP:8099

Please read the AI instructions from:
http://YOUR_HA_IP:8099/api/ai/instructions

Confirm you're ready and understand the safety protocols.

My request: [describe what you want]
```

**Finding YOUR_HA_IP:**
- Open Home Assistant: **Settings** → **System** → **Network**
- Look for **IPv4 address** (e.g., `192.168.68.62`)
- Or use `homeassistant.local` if mDNS works on your network

**That's it!** Cursor AI will fetch the instructions from your local add-on (no internet needed) and follow all safety protocols.

### Example Prompts

**Install Climate Control System:**
```
Install Climate Control V3 with buffer radiators for my TRVs.
Analyze my current setup and configure it automatically.
```

**Create Automation:**
```
Create an automation that turns on my living room lights 
when motion is detected after sunset.
```

**Configure System:**
```
Set up a presence detection system using my phone's 
location and notify me when I'm approaching home.
```

### What Cursor AI Can Do

With this add-on, Cursor AI can:

✅ **Read your entire HA configuration** - no need to paste files  
✅ **Create complex systems in seconds** - automations, scripts, helpers  
✅ **Automatic backups** - every change is Git-versioned  
✅ **Intelligent analysis** - understands your devices and entities  
✅ **Error recovery** - can rollback if something goes wrong  
✅ **Complete autonomy** - from analysis to deployment  

**No more manual copy-pasting YAML configs!** 🚀

---

## 🚀 Installation (Detailed)

### Option 1: Via GitHub Repository (Recommended)

1. Open **Settings** → **Add-ons** → **Add-on Store**
2. Click **⋮** (three-dot overflow menu in top right corner)
3. Select **Repositories**
4. Add repository URL: `https://github.com/Coolver/home-assistant-cursor-agent`
5. Click **Add**
6. Refresh the page - find **HA Cursor Agent** in the list
7. Click **INSTALL**
8. Configure and start

### Option 2: Manual Installation (Alternative)

1. **Copy this folder** to `/addons/home-assistant-cursor-agent/` on your HA system via SSH/Samba/File Editor

2. **Reload Add-on repositories:**
   - Supervisor → Add-on Store → ⋮ → Check for updates

3. **Install the Add-on:**
   - Find "HA Cursor Agent" in Local Add-ons
   - Click **INSTALL**

4. **Configure:**
   - Set port (default: 8099)
   - Enable Git versioning (recommended)
   - Set log level

5. **Start the Add-on**

6. **Get your API token:**
   - The add-on uses Home Assistant's Supervisor token
   - For external access, use your Long-Lived Access Token

---

## ⚙️ Configuration

```yaml
port: 8099                    # API port
log_level: info               # Logging: debug, info, warning, error
enable_git_versioning: true   # Enable automatic backups
auto_backup: true             # Auto-commit on changes
max_backups: 50               # Maximum commits to keep
```

---

## 📚 API Documentation

### Interactive Documentation

Once installed, access:

- **Swagger UI:** `http://homeassistant.local:8099/docs`
- **ReDoc:** `http://homeassistant.local:8099/redoc`

### Quick Reference

#### Files API (`/api/files`)

```bash
# List files
GET /api/files/list?directory=&pattern=*.yaml

# Read file
GET /api/files/read?path=configuration.yaml

# Write file
POST /api/files/write
{
  "path": "automations.yaml",
  "content": "...",
  "create_backup": true
}

# Append to file
POST /api/files/append
{
  "path": "scripts.yaml",
  "content": "\nmy_script:\n  ..."
}

# Delete file
DELETE /api/files/delete?path=old_file.yaml

# Parse YAML
GET /api/files/parse_yaml?path=configuration.yaml
```

#### Entities API (`/api/entities`)

```bash
# List all entities
GET /api/entities/list

# Filter by domain
GET /api/entities/list?domain=climate

# Search entities
GET /api/entities/list?search=bedroom

# Get specific entity state
GET /api/entities/state/climate.bedroom_trv_thermostat

# List all services
GET /api/entities/services
```

#### Helpers API (`/api/helpers`)

```bash
# Create helper
POST /api/helpers/create
{
  "domain": "input_boolean",
  "entity_id": "my_switch",
  "name": "My Switch",
  "config": {
    "icon": "mdi:toggle-switch",
    "initial": false
  }
}

# Delete helper
DELETE /api/helpers/delete/input_boolean.my_switch
```

#### Automations API (`/api/automations`)

```bash
# List automations
GET /api/automations/list

# Create automation
POST /api/automations/create
{
  "id": "my_automation",
  "alias": "My Automation",
  "trigger": [...],
  "action": [...]
}

# Delete automation
DELETE /api/automations/delete/my_automation
```

#### Scripts API (`/api/scripts`)

```bash
# List scripts
GET /api/scripts/list

# Create script
POST /api/scripts/create
{
  "entity_id": "my_script",
  "alias": "My Script",
  "sequence": [...]
}

# Delete script
DELETE /api/scripts/delete/my_script
```

#### System API (`/api/system`)

```bash
# Reload component
POST /api/system/reload?component=automations
# Components: automations, scripts, templates, core, all

# Check configuration
POST /api/system/check_config

# Get HA config
GET /api/system/config

# Restart HA (⚠️ use carefully!)
POST /api/system/restart
```

#### Backup API (`/api/backup`)

```bash
# Create backup (commit)
POST /api/backup/commit
{
  "message": "Before climate control installation"
}

# Get backup history
GET /api/backup/history?limit=20

# Rollback to commit
POST /api/backup/rollback
{
  "commit_hash": "a1b2c3d4"
}

# Get diff
GET /api/backup/diff
GET /api/backup/diff?commit1=a1b2c3d4
```

#### Logs API (`/api/logs`)

```bash
# Get agent logs
GET /api/logs/?limit=100
GET /api/logs/?level=ERROR

# Clear logs
DELETE /api/logs/clear
```

---

## 🔐 Authentication

All API endpoints (except `/api/health`) require authentication.

### Using Supervisor Token (within HA)

The add-on automatically uses the Supervisor token. No configuration needed.

### Using Long-Lived Token (external access)

1. Create token in HA: **Profile Name** (bottom left) → **Security** → **Long-lived access tokens** → **CREATE TOKEN**
2. Add header to requests:
   ```
   Authorization: Bearer YOUR_TOKEN_HERE
   ```

### Example with curl:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://homeassistant.local:8099/api/entities/list
```

---

## 💡 Usage Examples

### Example 1: Read configuration

```python
import requests

headers = {"Authorization": "Bearer YOUR_TOKEN"}
url = "http://homeassistant.local:8099"

# Read configuration.yaml
response = requests.get(
    f"{url}/api/files/read",
    params={"path": "configuration.yaml"},
    headers=headers
)
config = response.json()['content']
print(config)
```

### Example 2: Create automation

```python
# Create backup first
requests.post(
    f"{url}/api/backup/commit",
    json={"message": "Before adding automation"},
    headers=headers
)

# Create automation
automation = {
    "id": "test_automation",
    "alias": "Test Automation",
    "trigger": [
        {"platform": "state", "entity_id": "sensor.temperature", "to": "20"}
    ],
    "action": [
        {"service": "light.turn_on", "target": {"entity_id": "light.bedroom"}}
    ]
}

response = requests.post(
    f"{url}/api/automations/create",
    json=automation,
    headers=headers
)
print(response.json())
```

### Example 3: List climate entities

```python
# Get all climate entities
response = requests.get(
    f"{url}/api/entities/list",
    params={"domain": "climate"},
    headers=headers
)

climates = response.json()['entities']
for climate in climates:
    print(f"{climate['entity_id']}: {climate['attributes']['current_temperature']}°C")
```

### Example 4: Rollback if something went wrong

```python
# Get history
response = requests.get(
    f"{url}/api/backup/history",
    headers=headers
)
commits = response.json()['commits']

# Rollback to previous commit
requests.post(
    f"{url}/api/backup/rollback",
    json={"commit_hash": commits[1]['hash']},  # Previous commit
    headers=headers
)

# Restart HA to apply
requests.post(
    f"{url}/api/system/restart",
    headers=headers
)
```

---

## 🔍 Monitoring

### Check Agent Health

```bash
# No auth required for health check
curl http://homeassistant.local:8099/api/health
```

### View Agent Logs

```bash
curl -H "Authorization: Bearer TOKEN" \
     http://homeassistant.local:8099/api/logs/?limit=50
```

### View Backup History

```bash
curl -H "Authorization: Bearer TOKEN" \
     http://homeassistant.local:8099/api/backup/history
```

---

## 🛡️ Security

### Safety Features

- ✅ **Path validation** - Cannot access files outside `/config`
- ✅ **Authentication required** - All endpoints (except health) require token
- ✅ **Automatic backups** - Git commits before modifications
- ✅ **Rollback capability** - Restore any previous state
- ✅ **Configuration validation** - Check before applying
- ✅ **Audit logs** - Track all operations

### Best Practices

1. **Always backup** before major changes
2. **Check config** before reloading
3. **Review logs** after operations
4. **Use rollback** if something breaks
5. **Test in dev environment** first

---

## 🔧 Development

### Project Structure

```
home-assistant-cursor-agent/
├── config.yaml              # Add-on configuration
├── Dockerfile               # Container definition
├── run.sh                   # Startup script
├── requirements.txt         # Python dependencies
├── app/
│   ├── main.py             # FastAPI application
│   ├── api/                # API endpoints
│   │   ├── files.py
│   │   ├── entities.py
│   │   ├── helpers.py
│   │   ├── automations.py
│   │   ├── scripts.py
│   │   ├── system.py
│   │   ├── backup.py
│   │   └── logs.py
│   ├── services/           # Business logic
│   │   ├── ha_client.py    # HA API client
│   │   ├── file_manager.py # File operations
│   │   └── git_manager.py  # Git versioning
│   ├── models/             # Pydantic models
│   │   └── schemas.py
│   └── utils/              # Utilities
│       └── logger.py
└── README.md
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export CONFIG_PATH="/path/to/ha/config"
export HA_TOKEN="your_token"
export HA_URL="http://homeassistant.local:8123"
export PORT=8099
export LOG_LEVEL=DEBUG
export ENABLE_GIT=true

# Run
python -m uvicorn app.main:app --reload --port 8099
```

---

## 🎯 Use Cases

### For Cursor AI

This add-on enables Cursor AI to:

1. **Autonomously install systems** - AI reads current config, creates all components, tests
2. **Debug issues** - AI reads logs, configs, entity states, fixes problems
3. **Evolve configurations** - AI improves automations based on usage patterns
4. **Safe experimentation** - Git versioning allows instant rollback
5. **Complete automation** - No manual steps required!

### Example Workflow

```
User: "Install smart climate control system"
   ↓
AI via Agent:
1. Reads current TRV entities
2. Creates backup
3. Creates 7 input helpers
4. Adds 12 template sensors to configuration.yaml
5. Creates 5 scripts
6. Creates 10 automations
7. Reloads all components
8. Validates installation
9. Shows dashboard YAML for user to add
   ↓
User: "Something's wrong, rollback!"
   ↓
AI via Agent:
1. Gets backup history
2. Rolls back to previous commit
3. Restarts HA
4. Verifies restoration
```

---

## 📊 API Overview

| Endpoint | Methods | Description |
|----------|---------|-------------|
| `/api/files` | GET, POST, DELETE | File operations |
| `/api/entities` | GET | Entity states and services |
| `/api/helpers` | POST, DELETE | Input helper management |
| `/api/automations` | GET, POST, DELETE | Automation management |
| `/api/scripts` | GET, POST, DELETE | Script management |
| `/api/system` | POST, GET | System operations |
| `/api/backup` | GET, POST | Git versioning |
| `/api/logs` | GET, DELETE | Agent logs |
| `/api/health` | GET | Health check (no auth) |
| `/docs` | GET | Interactive API docs |

---

## ⚠️ Important Notes

### Git Versioning

- Creates `.git` folder in `/config` if not exists
- Auto-commits on every change (if enabled)
- Stores up to 50 commits (configurable)
- Commit messages include operation details

### File Operations

- All paths are relative to `/config`
- Cannot access files outside config directory
- Automatic backup before write/delete
- YAML validation on parse

### Service Calls

- Full access to Home Assistant API
- Can call any service (lights, climate, system, etc.)
- Requires proper entity IDs

---

## 🐛 Troubleshooting

### Add-on won't start

**Check logs:** Supervisor → HA Cursor Agent → Logs

Common issues:
- Port 8099 already in use
- Invalid configuration
- Missing permissions

### API returns 401 Unauthorized

- Check token is correct
- Ensure Authorization header is present
- Token format: `Bearer YOUR_TOKEN`

### File operations fail

- Check file paths are relative to `/config`
- Ensure files exist for read/delete operations
- Check YAML syntax for parse errors

### Git versioning not working

- Check `enable_git_versioning` is `true`
- View logs for Git errors
- Ensure `/config` is writable

---

## 📞 Support

- **Issues:** GitHub Issues
- **Documentation:** `/docs` endpoint (Swagger UI)
- **Logs:** `/api/logs/` endpoint

---

## 📜 License

MIT License - See LICENSE file

---

## 🙏 Credits

Created for seamless integration between **Cursor AI** and **Home Assistant**.

Enables AI to autonomously manage smart home configurations! 🏠🤖

---

**Ready to give your AI full control of Home Assistant? Install now!** 🚀

