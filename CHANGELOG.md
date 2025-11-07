# Changelog

All notable changes to this project will be documented in this file.

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
