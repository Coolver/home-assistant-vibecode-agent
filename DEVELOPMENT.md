# Development Guide

This document provides detailed information for developers who want to understand, modify, or extend the HA Vibecode Agent.

## 🛠️ Development and Testing on Home Assistant

The **Home Assistant Vibecode Agent** is designed to run *on* your Home Assistant instance.  
If you’re working on new features or bugfixes, you’ll often want to test your changes from a specific Git branch directly on the device, before they are merged into `main`.

Below is one way to do that using a local add-on. If you know a better flow for your environment, PRs are very welcome 🙂

---

### Prerequisites

- Home Assistant **OS** or **Supervised** (i.e. with the Add-on system and Supervisor).
- The **Advanced SSH & Web Terminal** add-on installed and configured.
  - In your user profile, enable **Advanced mode**.
  - In the SSH & Web Terminal add-on settings, disable **Protection mode** so the terminal can access the full filesystem.
- (Optional but recommended) Uninstall or stop the “release” version of the Vibecode Agent add-on if you already installed it from the default repository, to avoid confusion between the store and local versions.

---

### 1. Clone the repository as a local add-on

1. Open **Advanced SSH & Web Terminal** from the Home Assistant sidebar.
2. Create the local add-ons directory if it doesn’t exist yet:

   ```bash
   mkdir -p /addons/local
   ```

3. Change into that directory and clone your fork / the main repository:

   ```bash
   cd /addons/local
   git clone https://github.com/Coolver/home-assistant-vibecode-agent.git
   ```

4. Switch to the branch you want to test (for example):

   ```bash
   cd home-assistant-vibecode-agent
   git checkout your-feature-branch
   ```

At this point, your add-on files live under:

```text
/addons/local/home-assistant-vibecode-agent
```

Home Assistant will treat this as a **local add-on**.

---

### 2. Install the local version of the Vibecode Agent

1. In the Home Assistant UI, go to  
   **Settings → Add-ons → Add-on Store**.
2. Click the **⋮** menu in the top-right and choose **Reload**.
3. After reload, you should see a **“Local add-ons”** section (or similar), where a local copy of **Home Assistant Vibecode Agent** will appear.
4. Open it, click **Install**, then **Start** (and enable “Start on boot” if needed).

You are now running the add-on directly from your checked-out branch in `/addons/local/vibecode-agent`.

---

### 3. Updating the code from your branch

When you make further changes to your branch and push them to GitHub, you’ll want to pull those updates onto your Home Assistant instance and rebuild the add-on.

1. Open **Advanced SSH & Web Terminal** again and run:

   ```bash
   cd /addons/local/home-assistant-vibecode-agent
   git pull
   ```

   This will pull the latest commits from your branch.

2. Then, in the Home Assistant UI, go to:  
   **Settings → Add-ons → Home Assistant Vibecode Agent**  
   (make sure you’re opening the **local** version).

3. Click **Rebuild** (if available) and **Start** the add-on to apply the new code.

After rebuild/restart, the add-on will run with the latest changes from your branch.

---

This workflow lets you iterate on the Vibecode Agent locally on the actual Home Assistant device, while keeping your development flow branch-based and fully under version control.



## 📁 Project Structure

```
home-assistant-vibecode-agent/
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
│   │   ├── themes.py       # Theme management
│   │   ├── logbook.py      # Logbook entries
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

---

## 📚 API Documentation

### Interactive Documentation

Once the agent is running, access interactive API documentation:

- **Swagger UI:** `http://host:8099/docs`
- **ReDoc:** `http://host:8099/redoc`

### API Endpoints

#### Files API (`/api/files`)

#### Mistral Vibe API (`/api/mistral`)  
**New!** Direct integration with Mistral Vibe language models

```bash
# Health check
GET /api/mistral/health

# Chat completion
POST /api/mistral/chat
{
  "messages": [
    {"role": "user", "content": "Create a Home Assistant automation for motion detection"}
  ],
  "model": "mistral-small",
  "temperature": 0.7
}

# List available models
GET /api/mistral/models

# Create embeddings
POST /api/mistral/embeddings
{
  "input": "Smart home automation",
  "model": "mistral-embed"
}
```

**Authentication:** All Mistral Vibe endpoints require the same API key authentication as other endpoints.

**Configuration:** Set `MISTRAL_VIBE_API_URL` and `MISTRAL_VIBE_API_KEY` environment variables to enable.

#### Files API (`/api/files`)

Manage configuration files in the Home Assistant `/config` directory.

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

Query Home Assistant entities and their states.

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

# Call a Home Assistant service
POST /api/entities/call_service
{
  "domain": "light",
  "service": "turn_on",
  "target": {"entity_id": "light.living_room"},
  "service_data": {"brightness": 255}
}

# Rename an entity
POST /api/entities/rename
{
  "old_entity_id": "climate.old_name",
  "new_entity_id": "climate.new_name"
}
```

#### Helpers API (`/api/helpers`)

Create and manage input helpers (input_boolean, input_text, input_number, etc.).

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
DELETE /api/helpers/delete/input_boolean.my_switch?commit_message=Remove helper
```

#### Automations API (`/api/automations`)

Manage Home Assistant automations.

```bash
# List automations
GET /api/automations/list

# Create automation
POST /api/automations/create
{
  "id": "my_automation",
  "alias": "My Automation",
  "trigger": [...],
  "action": [...],
  "commit_message": "Add automation: My Automation"
}

# Delete automation
DELETE /api/automations/delete/my_automation?commit_message=Remove automation
```

#### Scripts API (`/api/scripts`)

Manage Home Assistant scripts.

```bash
# List scripts
GET /api/scripts/list

# Create script
POST /api/scripts/create
{
  "entity_id": "my_script",
  "alias": "My Script",
  "sequence": [...],
  "commit_message": "Add script: My Script"
}

# Delete script
DELETE /api/scripts/delete/my_script?commit_message=Remove script
```

#### System API (`/api/system`)

System-level operations for Home Assistant.

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

Git versioning and rollback operations.

```bash
# Create backup (commit)
POST /api/backup/commit
{
  "message": "Before climate control installation"
}

# Get backup history
GET /api/backup/history?limit=20

# Rollback to commit (by hash)
POST /api/backup/rollback/{commit_hash}

# Rollback to commit (by body)
POST /api/backup/rollback
{
  "commit_hash": "a1b2c3d4"
}

# Get diff
GET /api/backup/diff
GET /api/backup/diff?commit1=a1b2c3d4

# Create checkpoint (start of user request)
POST /api/backup/checkpoint?user_request=Create theme with dark blue header

# End checkpoint (re-enable auto-commits)
POST /api/backup/checkpoint/end

# Manual cleanup of old commits
POST /api/backup/cleanup?delete_backup_branches=true

# Restore files from commit
POST /api/backup/restore
{
  "commit_hash": "a1b2c3d4",
  "file_patterns": ["*.yaml", "configuration.yaml"]
}
```

#### Logs API (`/api/logs`)

Access agent logs.

```bash
# Get agent logs
GET /api/logs/?limit=100
GET /api/logs/?level=ERROR

# Clear logs
DELETE /api/logs/clear
```

#### Add-ons API (`/api/addons`)

Manage Home Assistant add-ons via Supervisor API.

```bash
# List ALL add-ons from store (full catalog)
GET /api/addons/store

# List available add-ons (installed and available)
GET /api/addons/available

# List installed add-ons only
GET /api/addons/installed

# Get add-on info
GET /api/addons/{slug}/info

# Get add-on logs
GET /api/addons/{slug}/logs?lines=100

# Install add-on
POST /api/addons/{slug}/install

# Uninstall add-on
POST /api/addons/{slug}/uninstall

# Start/stop/restart add-on
POST /api/addons/{slug}/start
POST /api/addons/{slug}/stop
POST /api/addons/{slug}/restart

# Update add-on
POST /api/addons/{slug}/update

# Get add-on configuration options
GET /api/addons/{slug}/options

# Set add-on configuration options
POST /api/addons/{slug}/options
{
  "option1": "value1",
  "option2": "value2"
}

# List add-on repositories
GET /api/addons/repositories

# Add custom repository
POST /api/addons/repositories/add
{
  "repository_url": "https://github.com/hassio-addons/repository"
}
```

#### HACS API (`/api/hacs`)

Manage HACS (Home Assistant Community Store) integrations.

```bash
# Check HACS status
GET /api/hacs/status

# Install HACS
POST /api/hacs/install

# Uninstall HACS
POST /api/hacs/uninstall

# List all repositories
GET /api/hacs/repositories

# Search repositories
GET /api/hacs/search?query=xiaomi&category=integration

# Install repository
POST /api/hacs/install_repository?repository=AlexxIT/XiaomiGateway3&category=integration

# Get repository details
GET /api/hacs/repository/{repository_id}

# Update all repositories
POST /api/hacs/update_all
```

#### Themes API (`/api/themes`)

Manage Home Assistant themes.

```bash
# List all themes
GET /api/themes/list

# Get theme content
GET /api/themes/get?theme_name=nice_dark

# Create new theme
POST /api/themes/create
{
  "theme_name": "my_theme",
  "theme_config": {
    "primary-color": "#ffb74d",
    "accent-color": "#ffb74d"
  }
}

# Update existing theme
PUT /api/themes/update
{
  "theme_name": "my_theme",
  "theme_config": {
    "primary-color": "#0000ff"
  }
}

# Delete theme
DELETE /api/themes/delete?theme_name=my_theme

# Reload themes
POST /api/themes/reload

# Check if themes are configured
GET /api/themes/check_config
```

#### Lovelace API (`/api/lovelace`)

Manage Lovelace dashboards.

```bash
# Analyze entities for dashboard generation
GET /api/lovelace/analyze

# Preview current dashboard configuration
GET /api/lovelace/preview

# Apply dashboard configuration
POST /api/lovelace/apply
{
  "dashboard_config": {...},
  "filename": "ai-dashboard.yaml",
  "create_backup": true,
  "register_dashboard": true
}

# Delete dashboard
DELETE /api/lovelace/delete/{filename}
```

#### Logbook API (`/api/logbook`)

Query Home Assistant logbook entries.

```bash
# Get logbook entries
GET /api/logbook/?limit=100
GET /api/logbook/?start_time=2025-12-01T00:00:00Z&end_time=2025-12-07T23:59:59Z
GET /api/logbook/?lookback_minutes=120
GET /api/logbook/?entity_id=automation.my_automation
GET /api/logbook/?domains=automation,script
GET /api/logbook/?event_types=automation_triggered,script_started
GET /api/logbook/?search=motion
```

---

## 🔐 Authentication

All API endpoints (except `/api/health`) require authentication.

### Agent Key Authentication

The add-on uses **Agent Key** authentication for external clients:

1. Agent Key is auto-generated on first start
2. Get your Agent Key from **Web UI** (Settings → Add-ons → HA Vibecode Agent → Open Web UI)
3. Include in requests as Bearer token

### Request Format

Add the `Authorization` header to all requests:

```
Authorization: Bearer YOUR_AGENT_KEY
```

**Example with curl:**

```bash
curl -H "Authorization: Bearer YOUR_AGENT_KEY" \
     http://localhost:8099/api/entities/list
```

### Internal Operations

The add-on automatically uses the **Supervisor Token** for Home Assistant API operations when running as an add-on. No manual configuration needed.

---

## 🏗️ Architecture Overview

### Core Components

1. **FastAPI Application** (`app/main.py`)
   - Main application entry point
   - Routes configuration
   - Middleware setup

2. **API Endpoints** (`app/api/`)
   - RESTful API endpoints
   - Request/response validation using Pydantic
   - Error handling

3. **Services** (`app/services/`)
   - Business logic layer
   - Home Assistant API clients
   - File and Git management

4. **Models** (`app/models/`)
   - Pydantic schemas for request/response validation
   - Data models

### Key Design Decisions

- **Separation of Concerns**: API endpoints are thin, business logic in services
- **Type Safety**: Pydantic models for all API interactions
- **Error Handling**: Consistent error responses across all endpoints
- **Git Versioning**: Automatic commits with meaningful messages
- **Security**: Path validation, authentication, and audit logging

---

For more information, see [README.md](README.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

