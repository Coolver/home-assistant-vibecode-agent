# Release v1.0.1

## 🐛 Bug Fixes

- **Fixed Raspberry Pi support** - Corrected Docker base images to use Python 3.12-alpine3.20
- **Fixed multi-architecture build** - Now builds successfully on all supported platforms (aarch64, armv7, amd64, armhf, i386)
- **Updated token path** - Fixed instructions for new Home Assistant UI (Profile → Security → Long-lived access tokens)

## ✨ New Features

- **Local AI Instructions Endpoint** - Added `/api/ai/instructions` for offline AI integration
- **Cursor Branding** - Added official Cursor icon for better add-on visibility
- **Enhanced Safety Protocols** - Added disclaimer and comprehensive AI safety instructions

## 📝 Documentation

- Simplified documentation structure (removed redundant files)
- Integrated Quick Start into README (5 minutes setup)
- Added Cursor AI integration guide with example prompts
- All documentation now self-hosted via API endpoints

## 🔧 Changes

- Removed GitHub Actions builder workflow (not needed for repository-based installation)
- Removed redundant documentation files (DOCS.md, INSTALLATION.md, SUMMARY.md, etc.)
- Cleaned up Russian language files (project now 100% English)
- Updated version to 1.0.1 across all files

## 📦 Installation

Add repository to Home Assistant:
```
https://github.com/Coolver/home-assistant-cursor-agent
```

Then install from Add-on Store.

## 🔗 Links

- **Repository:** https://github.com/Coolver/home-assistant-cursor-agent
- **Documentation:** See README.md
- **API Docs:** http://homeassistant.local:8099/docs (after installation)
- **AI Instructions:** http://homeassistant.local:8099/api/ai/instructions

## ⚠️ Breaking Changes

None - fully compatible with v1.0.0.

## 🙏 Notes

This release focuses on fixing Raspberry Pi compatibility and improving the Cursor AI integration experience.

If you encounter any issues, please use the rollback feature or report on GitHub.

