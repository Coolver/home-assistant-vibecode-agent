# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.10.x  | :white_check_mark: |
| < 2.10  | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT** open a public GitHub issue for security vulnerabilities
2. Email: [Open a private security advisory](https://github.com/Coolver/home-assistant-vibecode-agent/security/advisories/new)
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will acknowledge receipt within 48 hours and provide a timeline for a fix.

## Security Design

### Authentication
- All API endpoints (except `/api/health`) require Bearer token authentication
- API keys are auto-generated with 256 bits of entropy (`secrets.token_urlsafe(32)`)
- Keys are stored locally at `/config/.ha_cursor_agent_key`

### File System Access
- All file operations are sandboxed to `/config` directory
- Path traversal attempts are blocked (no `..` allowed in paths)
- Symlink resolution stays within the sandbox

### Network
- The agent listens on a single port (default 8099)
- No outbound connections except to Home Assistant APIs
- The setup panel is served only through Home Assistant Ingress. The API does not send a wildcard CORS header

### Git Versioning
- Shadow git repository isolates versioning from user config
- No remote git operations (push/pull) are performed
- Commit history is bounded (max 30 commits by default)

## Known Limitations

- The agent can read and write `/config`, except credential files (`secrets.yaml`, key and certificate files, and Home Assistant auth/config-entry storage). Set the add-on option `allow_sensitive_files` to allow those too
- Service calls can affect physical devices — always review AI actions before confirming
- The MCP package runs with `npx` which downloads from npm — pin the version for production use:
  ```
  npx -y @coolver/home-assistant-mcp@3.2.32
  ```
