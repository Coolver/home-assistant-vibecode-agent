# Changelog

All notable changes to this project will be documented in this file.

## [1.0.4] - 2025-11-08

### Fixed
- **Token validation in add-on mode:** Fixed "Invalid token" errors when using Long-Lived Access Tokens
- Agent no longer tries to validate user tokens through supervisor URL (which doesn't accept them)
- In add-on mode, agent simply checks that a token is provided and uses SUPERVISOR_TOKEN for HA API operations

### Changed
- Simplified token validation logic for better reliability
- Improved token validation logging

## [1.0.3] - 2025-11-08

### Added
- **Enhanced debugging:** Detailed logging for token configuration at startup
- **Token validation logging:** Logs token validation attempts with response details
- **HA API request logging:** Logs all HA API requests with token preview
- **HAClient initialization logging:** Shows which token source is being used
- **Success/failure indicators:** Visual ✅/❌ indicators in logs

### Changed
- Version bumped to 1.0.3
- Improved error messages with token context for easier debugging

### Fixed
- Made "Invalid token" errors much easier to diagnose with detailed logging
- Added visibility into SUPERVISOR_TOKEN vs DEV_TOKEN usage

## [1.0.1] - 2024-11-07

### Fixed
- Fixed Docker base images to use correct Python 3.12-alpine3.20 versions
- Now builds successfully on Raspberry Pi (aarch64, armv7) and all other architectures
- Resolved "base image not found" error during add-on installation

### Added
- Cursor AI integration guide in README with ready-to-use prompt templates
- Example use cases for autonomous Home Assistant management
- Proper Cursor branding icons (icon.png, logo.png)

### Changed
- Removed unnecessary GitHub Actions builder workflow  
- Cleaned up documentation (removed redundant files)
- Integrated Quick Start guide directly into README
- Updated to multi-architecture support with build.json

## [1.0.0] - 2024-11-07

### Added
- Initial release of HA Cursor Agent
- FastAPI REST API with 29 endpoints
- File management (read/write/list/append/delete)
- Home Assistant integration (entities, services, reloads)
- Component management (helpers, automations, scripts)
- Git versioning with automatic backups
- Rollback functionality
- Agent logs API
- Health check endpoint
- Swagger UI documentation (`/docs`)
- Multi-architecture Docker support
- Home Assistant Add-on configuration

### Features
- **Files API**: Manage configuration files
- **Entities API**: Query devices and entities
- **Helpers API**: Create/delete input helpers
- **Automations API**: Manage automations
- **Scripts API**: Manage scripts
- **System API**: Reload components, check config
- **Backup API**: Git commit, history, rollback
- **Logs API**: Agent operation logs

### Documentation
- README with installation guide
- DOCS with full API reference
- INSTALLATION guide
- Quick Start guide
- Changelog
