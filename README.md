# HA Vibecode Agent - Home Assistant Add-on

[![Version](https://img.shields.io/badge/version-2.10.23-blue.svg)](https://github.com/Coolver/home-assistant-vibecode-agent)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![MCP Package](https://img.shields.io/npm/v/@coolver/home-assistant-mcp?label=MCP%20Package)](https://www.npmjs.com/package/@coolver/home-assistant-mcp)

**Let AI build your Home Assistant automations – or act as your DevOps for the ones you write by hand. Just describe what you need in natural language. 🏠🤖**

You describe your goal → AI inspects your Home Assistant → designs a custom solution → and deploys it on-board automatically. 🚀

And if you prefer to handcraft your automations and scripts yourself, the agent can simply act as your DevOps and extra pair of hands: quickly uploading your changes, running tests, and analyzing logs on demand. **You stay in control and decide how much you delegate to AI and how deep it should go.**

Transform the way you manage your smart home. This add-on enables **Cursor**, **Visual Studio Code (VS Code)**, or any **MCP-enabled IDE** to:

- 📝 Analyze your Home Assistant configuration, entities, and devices  
- 🏗️ Create intelligent automations, scripts, and complete systems — including Home Assistant helpers that can be fully managed programmatically  
- 🎨 Design and customize Lovelace dashboards with full control over cards, layouts, and styling  
- 🖌️ Create and tweak themes for a personalized UI  
- 🔄 Safely deploy changes with automatic Git-based versioning  
- 🔍 Monitor and troubleshoot your setup through log analysis  
- 📦 Install and manage HACS integrations and custom repositories  

No more manual YAML editing or searching through documentation - just describe what you want in natural language!

**Real example:** User says *"Install smart climate control"* → AI analyzes 7 TRVs, creates 10 automations + 9 helpers + 10 sensors + 5 scripts, deploys everything, and it just works!

https://github.com/user-attachments/assets/0df48019-06c0-48dd-82ad-c7fe0734ddb3

**Full YouTube Demo:**
- [How to control Home Assistant from Cursor](https://youtu.be/xocbWonWdoc)

---

## 🎯 What is this?

**HA Vibecode Agent** is a Home Assistant add-on that exposes a safe on-board REST API and toolset, allowing AI assistants (Cursor, VS Code, Claude, Continue, and any MCP-enabled IDE) to work *with* your Home Assistant instead of just generating YAML in the dark.

---

### 🔍 Analyze your setup

✅ Read your full configuration — entities, automations, scripts, helpers  
✅ Understand your devices — capabilities, relations, and usage patterns  
✅ Learn existing logic — analyze how your current automations and scripts behave  

---

### 🏗️ Build intelligence

✅ Create complete systems — multiple interconnected automations in seconds  
✅ Generate helpers and sensors — tailored to your actual setup and needs  
✅ Write optimized scripts — based on real entities, areas, and devices  
✅ Refactor existing logic — improve or merge automations instead of starting from scratch  

---

### 📊 Dashboards & UI

✅ Create and update Lovelace dashboards — fully programmatically  
✅ Add, remove, or rearrange cards — stat, graphs, history, custom cards, and more  
✅ Control layouts and views — organize rooms, areas, and scenarios  
✅ Design and tweak themes — colors, typography, and styles for a personalized UI  

---

### 🔒 Safe operations

✅ Git-based versioning — every change is tracked with meaningful commit messages  
✅ Human-readable commits — AI explains *what* changed and *why*  
✅ Configuration validation — test before apply to reduce breaking changes  
✅ One-click rollback — revert to a previous state if something goes wrong  
✅ Activity log — full audit trail of what the agent did and when  

---

### 📦 Extend with the community

✅ Install and configure HACS — unlock 1000+ community integrations  
✅ Search repositories — themes, plugins, custom components, dashboards  
✅ Install integrations — one-command setup for new HACS components  
✅ Keep things fresh — update all HACS repositories from a single place  

---

**Result:**  
You describe your goal → AI inspects your Home Assistant → designs a custom solution → and deploys it on-board automatically. 🚀


### 🚀 How is this different from other MCP modules for Home Assistant?

Most MCP integrations I’ve seen for Cursor, VS Code or Claude work only on your local machine and talk to Home Assistant over SSH and sometimes the REST API.

For serious Home Assistant work, that’s not really enough:

Home Assistant is not just a bunch of YAML files.
It exposes multiple internal APIs, and some of the most important ones are only available from inside HA itself over the WebSocket API.

When you access HA only via SSH, the AI usually has to generate and upload a helper script on every request, then execute it blindly on the host.
Since that script can be different every time, each request is a bit of a black box — more like playing Russian roulette than doing reliable automation.

Because of that, I chose a different architecture.

This project is **split into two modules**:

**Home Assistant Agent** (this module) – runs inside Home Assistant (as an add-on),
has native access to all relevant APIs, files and services,
and exposes a safe, well-defined interface for external tools.

**Home Assistant MCP server** – runs on your computer alongside your AI IDE (Cursor, VS Code, etc.)
and talks to the Agent over a controlled API instead of SSH hacks (installation steps below)

This design makes working with Home Assistant faster, more predictable, safer and repeatable.
Your AI IDE gets exactly the actions and data it needs — through a stable API — instead of constantly inventing ad-hoc scripts and hoping they behave correctly.

---

## 🌟 Features

### 🏠 Home Assistant Integration
- Full access to HA REST API and WebSocket
- List all entities and their states
- Call any HA service
- Reload components (automations, scripts, templates)
- Check configuration validity
- Real-time state monitoring

### 📊 Dashboards & Themes
- Create and update Lovelace dashboards programmatically
- Add, remove, and rearrange cards (stat, graphs, history, custom cards, etc.)
- Manage views, layouts, and groups for rooms and areas
- Create and tweak themes for fully customized UI appearance
- Safely adjust dashboards and themes through AI-driven operations

### 📁 File Management
- List, read, write, append, delete files
- Automatic backup before modifications
- YAML parsing and validation
- Safe path handling (restricted to `/config`)

### 🔧 Component Management
- Create/Delete Input Helpers (boolean, text, number, datetime, select)
- Create/Delete Automations
- Create/Delete Scripts
- Automatic reload after changes

### 💾 Git Versioning
- Automatic commit on every change with meaningful commit messages
- AI-generated descriptive messages explaining what and why changed
- Backup history (up to 30 commits, configurable)
- Automatic cleanup of old commits to prevent repository bloat
- **View change history** – ask AI to show recent commits with meaningful messages
- **Easy rollback** – ask AI to rollback to any previous version by description or commit hash
- View diffs between versions
- Commit messages include operation context (e.g., "Add automation: Control lights when motion detected")

**Example AI interactions:**
- *"Show me the last 10 changes to my configuration"* → AI displays commit history with meaningful messages  
- *"Something broke! Roll back to the version from yesterday"* → AI finds and restores previous version  
- *"What changed in the last commit?"* → AI shows detailed diff  
- *"Roll back to when I added the motion sensor automation"* → AI finds and restores that specific commit

### 📡 Monitoring & Troubleshooting
- Agent logs API with filtering
- Operation history
- Real-time status
- Health check endpoint
- System monitoring and analysis

### 🔌 Add-on Management
**Complete add-on lifecycle management – install, configure, and control services!**
- Install/uninstall add-ons (Zigbee2MQTT, Node-RED, ESPHome, etc.)
- Configure add-on options
- Start/stop/restart add-ons
- Monitor add-on logs
- Update add-ons
- Powered by Supervisor API

### 📦 HACS Management
**Complete HACS integration via WebSocket – browse 1000+ custom integrations!**
- Install HACS automatically from GitHub
- Search repositories by name, author, or category
- Install integrations, themes, and plugins
- Update all installed repositories
- View repository details (stars, versions, authors)
- Powered by persistent WebSocket connection

---

## ⚡ Quick Start (5 minutes)

### 1. Add Repository

Open your **Home Assistant UI** (usually http://homeassistant.local:8123):

1. Go to **Settings** → **Add-ons** → **Add-on Store** → **⋮** → **Repositories** (usually http://homeassistant.local:8123/hassio/dashboard )
2. Add: `https://github.com/coolver/home-assistant-vibecode-agent`
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
If you find this project useful and want to support its development, **please consider giving it a [GitHub Star](https://github.com/Coolver/home-assistant-vibecode-agent) ⭐**

[YouTube Installation guide: how to install the Home Assistant Cursor Agent](https://youtu.be/RZNkNZnhMrc)

---

## 🤖 Using with AI IDE (Cursor, VS Code etc)

This add-on enables **AI IDE to autonomously manage your Home Assistant** through natural language - no manual copy-pasting needed!

### ⚠️ Important Disclaimer

**This tool is designed for experienced Home Assistant users who understand what they're doing.** 

- ✅ **Always review changes** before applying them to production systems
- ⚠️ **AI can accidentally break your configuration** if given incorrect instructions or outdated information
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

AI will autonomously read your configuration, create components, and deploy everything automatically!

**That's it!** AI IDE will use the MCP protocol to communicate with your Home Assistant.

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

### What Vibecode Agent Can Do

With this add-on and [MCP integration](https://github.com/Coolver/home-assistant-mcp), AI IDE can:

✅ **Analyze YOUR configuration** - detects your actual devices and entities  
✅ **Create complex systems autonomously** - 10+ interconnected automations  
✅ **Tailored to your setup** - uses your specific entity IDs and device capabilities  
✅ **Automatic backups** - every change is Git-versioned with meaningful commit messages  
✅ **View change history** - ask AI to show recent commits and what changed  
✅ **Easy rollback** - ask AI to rollback to any previous version by description or date  
✅ **Intelligent debugging** - reads logs, finds issues, fixes them  
✅ **Error recovery** - can rollback if something goes wrong  
✅ **End-to-end deployment** - from analysis to production  

**Stop writing YAML manually! Just describe what you want.** 🚀

---

## 📚 API Documentation

For complete API documentation, authentication details, and usage examples, see **[DEVELOPMENT.md](DEVELOPMENT.md)**.

**Quick access:**
- **Swagger UI:** `http://homeassistant.local:8099/docs` (when installed)
- **ReDoc:** `http://homeassistant.local:8099/redoc` (when installed)

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
- ✅ **Automatic backups** - Git commits before modifications with meaningful commit messages
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

For development setup, project structure, API documentation, and local development instructions, see **[DEVELOPMENT.md](DEVELOPMENT.md)**.

## 🤝 Contributing

Contributions are welcome! If you'd like to contribute:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

For detailed contribution guidelines, see **[CONTRIBUTING.md](CONTRIBUTING.md)**.

---

## 🎯 Use Cases

### For Cursor AI, VS Code + Co-Pilot etc

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
User: "Show me the last 10 changes to my configuration"
   ↓
AI via Agent:
1. Calls `ha_git_history` to get commit history
2. Displays commits with meaningful messages:
   - "Add automation: Control lights when motion detected"
   - "Update theme: Change primary color to blue"
   - "Add helper: Enable/disable climate system"
3. Shows timestamps and commit hashes
4. Helps identify which changes to review

User: "Something broke! Rollback to the version from yesterday"
   ↓
AI via Agent:
1. Gets recent commit history
2. Finds commits from yesterday
3. Shows options with descriptions
4. Rolls back to selected version
5. Verifies rollback was successful

User: "Rollback to when I added the motion sensor automation"
   ↓
AI via Agent:
1. Searches commit history for "motion sensor automation"
2. Finds matching commit
3. Shows commit details
4. Rolls back to that specific version
3. Restarts HA
4. Verifies restoration
```
---

## ⚠️ Important Notes

### Git Versioning

- Creates `.git` folder in `/config` if not exists
- Auto-commits on every change (if enabled)
- **Meaningful commit messages**: AI-generated descriptive messages explaining what and why changed
  - Examples: "Add automation: Control lights when motion detected", "Update theme: Change primary color to blue"
  - Messages are generated based on operation context and user-provided descriptions
- Stores up to 30 commits (configurable via `max_backups`)
- Automatic cleanup: When reaching max commits, keeps last 20 commits (maintains buffer)
- Commit messages include operation details and context

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

### "spawn npx ENOENT" error (Cursor / VS Code / Other IDE Console)

This error means Node.js is not installed or not found in your system PATH.

Solution: Install Node.js (v18.0.0 or higher) on the computer where Cursor is running:

Download and install Node.js from https://nodejs.org
Restart Cursor completely after installation
Verify installation by running node --version in a terminal
Important: Node.js must be installed on your computer (where Cursor runs), not on the Home Assistant server.


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

- Git versioning is always enabled in shadow repository (`/config/ha_vibecode_git`)
- Check `git_versioning_auto` setting for auto/manual commit mode
- View logs for Git errors
- Ensure `/config` is writable

## 💬 Support

- 🐛 **Issues:** [GitHub Issues](https://github.com/Coolver/home-assistant-vibecode-agent/issues)
- 💡 **Discussions:** [GitHub Discussions](https://github.com/Coolver/home-assistant-vibecode-agent/discussions)

---

## 📜 License

MIT License - See LICENSE file

---

**Ready to give your AI full control of Home Assistant? Install now!** 🚀

