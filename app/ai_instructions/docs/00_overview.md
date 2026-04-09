# HA VIBECODE AGENT - INSTRUCTIONS FOR AI ASSISTANTS

**Version:** 2.6.1  
**Base URL:** http://homeassistant.local:8099  
**Interactive Docs:** http://homeassistant.local:8099/docs

---

## About This Guide

This guide provides comprehensive instructions for AI assistants (like Cursor AI, VS Code Copilot, or **Mistral Vibe**) on how to safely and effectively interact with Home Assistant through the HA Vibecode Agent.

**Key Principles:**
- 🛡️ **Safety First** - Always analyze before modifying
- 💬 **Communication** - Explain actions before executing
- 📊 **Clarity** - Format output for human readability
- 🔄 **Backup** - Every change is git-versioned
- ❓ **When in doubt** - ASK the user

**🦙 Mistral Vibe Support:** This agent now supports Mistral Vibe as an alternative AI backend! See section 07 for Mistral Vibe specific instructions.

---

## Quick Reference

**Health Check:** `GET /api/health`  
**Configuration Validation:** `POST /api/system/check_config`  
**View Logs:** `GET /api/logs/`  
**Interactive API Docs:** http://homeassistant.local:8099/docs

**Mistral Vibe Endpoints:**
- **Health Check:** `GET /api/mistral/health`
- **Chat Completion:** `POST /api/mistral/chat`
- **List Models:** `GET /api/mistral/models`
- **Embeddings:** `POST /api/mistral/embeddings`



























