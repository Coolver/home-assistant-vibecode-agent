# HA Vibecode Agent - Home Assistant Add-on

[![Version](https://img.shields.io/badge/version-2.10.0-blue.svg)](https://github.com/Coolver/home-assistant-cursor-agent)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![MCP Package](https://img.shields.io/npm/v/@coolver/home-assistant-mcp?label=MCP%20Package)](https://www.npmjs.com/package/@coolver/home-assistant-mcp)

**Let AI build your Home Assistant automations - just describe what you want in natural language** 🏠🤖

Transform your smart home management! This add-on enables **Cursor AI**, **Visual Studio Code (VS Code)** or **your favourite IDE with MCP** support to:
- 📝 Analyze your Home Assistant configuration and devices
- 🏗️ Create intelligent automations, scripts, and complete systems
- 🔍 Monitor and troubleshoot your setup through log analysis
- 📦 Install and manage HACS integrations
- 🔄 Safely deploy changes with automatic Git versioning

No more manual YAML editing or searching through documentation - just describe what you want in natural language!

**Real example:** User says *"Install smart climate control"* → AI analyzes 7 TRVs, creates 10 automations + 9 helpers + 10 sensors + 5 scripts, deploys everything, and it just works!

https://github.com/user-attachments/assets/0df48019-06c0-48dd-82ad-c7fe0734ddb3

**Full YouTube Demo:**
- [How to control Home Assistant from Cursor](https://youtu.be/xocbWonWdoc)

---

## 🎯 What is this?

**HA Vibecode Agent** is a Home Assistant Add-on that provides a **REST API** enabling AI assistants (like Cursor AI, VS Code or other IDEs via [MCP protocol](https://github.com/Coolver/home-assistant-mcp)) to:

### 🔍 Analyze Your Setup
✅ **Read entire configuration** - entities, automations, scripts, helpers  
✅ **Understand your devices** - detects capabilities and relationships  
✅ **Learn existing patterns** - analyzes what you already have  

### 🏗️ Build Intelligence
✅ **Create complete systems** - 10+ interconnected automations in seconds  
✅ **Generate helpers and sensors** - tailored to your needs  
✅ **Write optimized scripts** - based on your actual devices  
✅ **Deploy dashboards** - with all your entities  

### 📦 Extend with Community
✅ **Install HACS** - get access to 1000+ custom integrations  
✅ **Search repositories** - find themes, plugins, and integrations  
✅ **Install integrations** - one-command setup for community components  
✅ **Auto-updates** - keep all HACS repositories up to date  

### 🔒 Safe Operations
✅ **Git versioning** - automatic backups of every change  
✅ **Configuration validation** - tests before applying  
✅ **Rollback capability** - undo any change instantly  
✅ **Activity monitoring** - full audit log of all operations  

**Result:** Describe your goal → AI analyzes your setup → Creates custom solution → Deploys automatically! 🚀

---

## 🌟 Features

### 🏠 Home Assistant Integration
- Full access to HA REST API and WebSocket
- List all entities and their states
- Call any HA service
- Reload components (automations, scripts, templates)
- Check configuration validity
- Real-time state monitoring

### 🔌 Add-on Management
**Complete add-on lifecycle management - install, configure, and control services!**
- Install/uninstall add-ons (Zigbee2MQTT, Node-RED, ESPHome, etc)
- Configure add-on options
- Start/stop/restart add-ons
- Monitor add-on logs
- Update add-ons
- Powered by Supervisor API

### 📦 HACS Management
**Complete HACS integration via WebSocket - browse 1000+ custom integrations!**
- Install HACS automatically from GitHub
- Search repositories by name, author, or category
- Install integrations, themes, and plugins
- Update all installed repositories
- View repository details (stars, versions, authors)
- Powered by persistent WebSocket connection

### 🔧 Component Management
- Create/Delete Input Helpers (boolean, text, number, datetime, select)
- Create/Delete Automations
- Create/Delete Scripts
- Automatic reload after changes

### 📁 File Management
- List, read, write, append, delete files
- Automatic backup before modifications
- YAML parsing and validation
- Safe path handling (restricted to `/config`)

### 💾 Git Versioning
- Automatic commit on every change
- Backup history (up to 50 commits)
- Rollback to any previous state
- View diffs between versions
- Commit messages for tracking

### 📊 Monitoring & Troubleshooting
- Agent logs API with filtering
- Operation history
- Real-time status
- Health check endpoint
- System monitoring and analysis

---

## ⚡ Quick Start (5 minutes)

### 1. Add Repository

Open your **Home Assistant UI** (usually http://homeassistant.local:8123):

1. Go to **Settings** → **Add-ons** → **Add-on Store** → **⋮** → **Repositories** (usually http://homeassistant.local:8123/hassio/dashboard )
2. Add: `https://github.com/coolver/home-assistant-cursor-agent`
3. Click **Add**

### 2. Install and Start Add-on

Still in **Home Assistant UI**:

1. Refresh the page
2. Find **HA Vibecode Agent** → Click **INSTALL**
3. Wait for installation to complete
4. Enable → **Start on boot: ON** → and push **START** button
5. **Wait for startup** (~10 seconds)
6. Click **"Open Web UI"** button

You'll see this interface:

<p align="center">
  <img src=".github/images/ingress-panel.jpg" alt="HA Vibecode Agent Ingress Panel" width="700">
</p>

7. Click the **Cursor** or **VS Code** tab (depending on which IDE you want to use with Home Assistant) and **follow the setup instructions**. You’ll need to install and configure Cursor or VS Code so they can connect to the HA Agent via the MCP protocol.

8. That’s it — **you’re ready to start** working with your Home Assistant scripts, automations and dashboards using AI.
If you find this project useful and want to support its development, **please consider giving it a [GitHub Star](https://github.com/Coolver/home-assistant-cursor-agent) ⭐**

[YouTube Installation guide: how to install the Home Assistant Cursor Agent](https://youtu.be/RZNkNZnhMrc)

---

## 🤖 Using with Cursor AI

This add-on enables **Cursor AI to autonomously manage your Home Assistant** through natural language - no manual copy-pasting needed!

### ⚠️ Important Disclaimer

**This tool is designed for experienced Home Assistant users who understand what they're doing.** 

- ✅ **Always review changes** before applying them to production systems
- ⚠️ **Cursor AI can accidentally break your configuration** if given incorrect instructions or outdated information
- 💾 **Git versioning is enabled by default** - all changes are backed up and can be rolled back
- 🔄 **Test in a safe environment first** if you're new to AI-driven automation
- 📖 **Verify syntax and compatibility** with your Home Assistant version

**Use at your own risk. The automatic backup system minimizes risk but doesn't eliminate it.**

### Start Using

Once connected, just describe what you want in natural language:

```
Show me all my climate entities and their current states
```

```
Analyze my automations and suggest optimizations
```

```
Create a smart lighting automation for movie mode
```

Cursor AI will autonomously read your configuration, create components, and deploy everything automatically!

**That's it!** Cursor AI will use the MCP protocol to communicate with your Home Assistant.

**Learn more:** [MCP Home Assistant on GitHub](https://github.com/Coolver/home-assistant-mcp) | [NPM Package](https://www.npmjs.com/package/@coolver/home-assistant-mcp)

### Real-World Examples

**Build Smart Climate Control:**
```
Install a smart climate control system for my TRV radiators. 
Analyze my current devices, create automations for efficient heating 
with predictive shutdown, buffer radiators, and adaptive cooldowns.
Set up monitoring sensors and dashboard.
```

**AI will autonomously:**
- Detect all your TRV entities by analyzing Home Assistant
- Create 10+ automations for intelligent heating control
- Add 9 input helpers for system state management
- Generate 10 template sensors for monitoring
- Create 5 scripts for boiler and buffer control
- Build Lovelace dashboard with all metrics
- Test and deploy everything
- **All tailored to YOUR specific TRVs and configuration!**

**Optimize Existing System:**
```
My heating wastes energy. Analyze my current climate automations 
and optimize for efficiency while maintaining comfort.
```

**Debug Issues:**
```
My bedroom lights automation isn't working. Check the logs, 
find the problem, and fix it.
```

### What Cursor AI Can Do

With this add-on and [MCP integration](https://github.com/Coolver/home-assistant-mcp), Cursor AI can:

✅ **Analyze YOUR configuration** - detects your actual devices and entities  
✅ **Create complex systems autonomously** - 10+ interconnected automations  
✅ **Tailored to your setup** - uses your specific entity IDs and device capabilities  
✅ **Automatic backups** - every change is Git-versioned  
✅ **Intelligent debugging** - reads logs, finds issues, fixes them  
✅ **Error recovery** - can rollback if something goes wrong  
✅ **End-to-end deployment** - from analysis to production  

**Stop writing YAML manually! Just describe what you want.** 🚀

---

## 🚀 Installation (Detailed)

### Option 1: Via GitHub Repository (Recommended)

1. Open **Settings** → **Add-ons** → **Add-on Store**
2. Click **⋮** (three-dot overflow menu in top right corner)
3. Select **Repositories**
4. Add repository URL: `https://github.com/Coolver/home-assistant-cursor-agent`
5. Click **Add**
6. Refresh the page - find **HA Vibecode Agent** in the list
7. Click **INSTALL**
8. Configure and start

### Option 2: Manual Installation (Alternative)

1. **Copy this folder** to `/addons/home-assistant-cursor-agent/` on your HA system via SSH/Samba/File Editor

2. **Reload Add-on repositories:**
   - Supervisor → Add-on Store → ⋮ → Check for updates

3. **Install the Add-on:**
   - Find "HA Vibecode Agent" in Local Add-ons
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

### For MCP Clients (Cursor AI)

The add-on uses **Agent Key** authentication:

1. Get your Agent Key from **Web UI** (Settings → Add-ons → HA Vibecode Agent → Open Web UI)
2. Configure in Cursor MCP settings with `HA_AGENT_KEY`
3. Agent Key is auto-generated on first start

### For Direct API Access

Add header to requests:
```
Authorization: Bearer YOUR_AGENT_KEY
```

**Example with curl:**

```bash
curl -H "Authorization: Bearer YOUR_AGENT_KEY" \
     http://homeassistant.local:8099/api/entities/list
```

### Internal Operations

The add-on automatically uses the **Supervisor Token** for Home Assistant API operations. No configuration needed.

---

## 💡 Usage Examples

### Example 1: Read configuration

```python
import requests

headers = {"Authorization": "Bearer YOUR_AGENT_KEY"}
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

**Example response:**
```json
{
  "status": "healthy",
  "version": "2.0.1"
}
```

### View Agent Logs

```bash
curl -H "Authorization: Bearer YOUR_AGENT_KEY" \
     http://homeassistant.local:8099/api/logs/?limit=50
```

### View Backup History

```bash
curl -H "Authorization: Bearer YOUR_AGENT_KEY" \
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
│   ├── auth.py             # API authentication
│   ├── ingress_panel.py    # Web UI panel
│   ├── api/                # API endpoints
│   │   ├── files.py        # File operations
│   │   ├── entities.py     # Entity states
│   │   ├── helpers.py      # Helper management
│   │   ├── automations.py  # Automation CRUD
│   │   ├── scripts.py      # Script CRUD
│   │   ├── system.py       # System operations
│   │   ├── backup.py       # Git versioning
│   │   ├── logs.py         # Log access
│   │   ├── addons.py       # Add-on management
│   │   ├── hacs.py         # HACS integration
│   │   ├── lovelace.py     # Dashboard management
│   │   └── ai_instructions.py # AI guidance docs
│   ├── services/           # Business logic
│   │   ├── ha_client.py    # HA REST API client
│   │   ├── ha_websocket.py # HA WebSocket client
│   │   ├── supervisor_client.py # Supervisor API
│   │   ├── file_manager.py # File operations
│   │   └── git_manager.py  # Git versioning
│   ├── models/             # Pydantic models
│   │   └── schemas.py
│   ├── utils/              # Utilities
│   │   ├── logger.py       # Logging setup
│   │   └── yaml_editor.py  # YAML manipulation
│   ├── templates/          # HTML templates
│   │   └── ingress_panel.html
│   └── ai_instructions/    # AI agent guidance
├── tests/                  # Test suites
├── CHANGELOG.md
└── README.md
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export CONFIG_PATH="/path/to/ha/config"
export HA_AGENT_KEY="your_dev_key"
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

**Check logs:** Supervisor → HA Vibecode Agent → Logs

Common issues:
- Port 8099 already in use
- Invalid configuration
- Missing permissions

### API returns 401 Unauthorized

- Check Agent Key is correct
- Regenerate key if needed: Settings → Add-ons → HA Vibecode Agent → Open Web UI
- Ensure Authorization header is present
- Format: `Authorization: Bearer YOUR_AGENT_KEY`

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

