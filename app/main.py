"""
HA Vibecode Agent - FastAPI Application
Enables AI assistants (Cursor AI, VS Code + Copilot) to manage Home Assistant configuration
"""
import os
import logging
import aiohttp
import secrets
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse

from app.api import files, entities, helpers, automations, scripts, system, backup, logs, logbook, ai_instructions, hacs, addons, lovelace, themes, registries
from app.utils.logger import setup_logger
from app.ingress_panel import generate_ingress_html
from app.services import ha_websocket
from app.env import load_env
load_env()

from app.auth import verify_token, set_api_key, security

# Setup logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'info').upper()
logger = setup_logger('ha_cursor_agent', LOG_LEVEL)

# Agent version
AGENT_VERSION = "2.10.23"

# FastAPI app
app = FastAPI(
    title="HA Vibecode Agent API",
    description="AI Agent API for Home Assistant - enables AI assistants (Cursor AI, VS Code + Copilot) to manage HA configuration",
    version=AGENT_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
# Note:
# - MCP clients (Cursor, VS Code, Codex, Claude Code, etc.) talk to the agent as
#   regular HTTP clients and are NOT affected by CORS (CORS is a browser concern).
# - We still keep a permissive configuration here for backwards compatibility,
#   but the critical security issue is addressed by requiring authentication for
#   API key regeneration (see /api/regenerate-key below).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Track MCP client versions (to avoid logging on every request)
mcp_clients_logged = set()

# Middleware to log MCP client version
@app.middleware("http")
async def log_mcp_client_version(request: Request, call_next):
    """Log MCP client version on first request"""
    mcp_version = request.headers.get('x-mcp-client-version')
    client_id = request.client.host if request.client else 'unknown'
    
    # Log only once per client
    if mcp_version and client_id not in mcp_clients_logged:
        mcp_clients_logged.add(client_id)
        logger.info(f"🔌 MCP Client connected: v{mcp_version} from {client_id}")
    
    response = await call_next(request)
    return response

# Get tokens and configuration from environment
SUPERVISOR_TOKEN = os.getenv('SUPERVISOR_TOKEN', '')  # Auto-provided by HA when running as add-on
DEV_TOKEN = os.getenv('HA_AGENT_KEY', '')  # For local development only
HA_URL = os.getenv('HA_URL', 'http://supervisor/core')

# API Key configuration
API_KEY_FROM_CONFIG = os.getenv('API_KEY', '').strip()
API_KEY_FILE = Path('/config/.ha_cursor_agent_key')

# Global variable for API key
API_KEY = None


def mask_api_key(key: str) -> str:
    """Mask API key for safe logging"""
    if len(key) > 16:
        return f"{key[:8]}...{key[-8:]}"
    return "***"


def get_or_generate_api_key():
    """
    Get or generate API key.
    
    Priority:
    1. API key from add-on configuration (API_KEY env var)
    2. Existing API key from file
    3. Generate new API key and save to file
    """
    # 1. Check config
    if API_KEY_FROM_CONFIG:
        logger.info("✅ Using API key from add-on configuration")
        return API_KEY_FROM_CONFIG
    
    # 2. Check file
    if API_KEY_FILE.exists():
        api_key = API_KEY_FILE.read_text().strip()
        logger.info("✅ Using existing API key from file")
        return api_key
    
    # 3. Generate new
    api_key = secrets.token_urlsafe(32)  # 256 bits of entropy
    
    try:
        API_KEY_FILE.write_text(api_key)
        logger.info(f"💾 API key saved to {API_KEY_FILE}")
    except Exception as e:
        logger.warning(f"Failed to save API key to file: {e}")
    
    # Log masked key for security
    masked = mask_api_key(api_key)
    logger.info("=" * 70)
    logger.info("NEW API KEY GENERATED")
    logger.info("=" * 70)
    logger.info(f"API Key (masked): {masked}")
    logger.info("")
    logger.info("To view the full API key:")
    logger.info("  - Open the Web UI at http://<host>:8099/")
    logger.info("  - Or read from: /config/.ha_cursor_agent_key")
    logger.info("=" * 70)
    
    return api_key


# Initialize API key
API_KEY = get_or_generate_api_key()
set_api_key(API_KEY)  # Set API key in auth module

# Log startup configuration
supervisor_token_status = "PRESENT" if SUPERVISOR_TOKEN else "MISSING"
dev_token_status = "PRESENT" if DEV_TOKEN else "MISSING"

logger.info(f"=================================")
logger.info(f"HA Vibecode Agent v{AGENT_VERSION}")
logger.info(f"=================================")
logger.info(f"SUPERVISOR_TOKEN: {supervisor_token_status}")
if SUPERVISOR_TOKEN:
    logger.info(f"Mode: Add-on (using SUPERVISOR_TOKEN for HA API)")
else:
    logger.info(f"DEV_TOKEN (for local dev): {dev_token_status}")
    logger.info(f"Mode: Development (using DEV_TOKEN)")
logger.info(f"HA_URL: {HA_URL}")
logger.info(f"API Key (for MCP client): {'Custom (from config)' if API_KEY_FROM_CONFIG else 'Auto-generated'}")
logger.info(f"=================================")


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize WebSocket client and Supervisor client on startup"""
    # Initialize Supervisor client (for add-on management)
    if SUPERVISOR_TOKEN:
        from app.services.supervisor_client import supervisor_client
        logger.info(f"✅ SupervisorClient ready - URL: {supervisor_client.base_url}")
    
    # Only start WebSocket if we have SUPERVISOR_TOKEN (running as add-on)
    if SUPERVISOR_TOKEN:
        logger.info("Initializing WebSocket client...")
        ha_websocket.ha_ws_client = ha_websocket.HAWebSocketClient(
            url=HA_URL,
            token=SUPERVISOR_TOKEN
        )
        await ha_websocket.ha_ws_client.start()
        logger.info("✅ WebSocket client started in background")
    else:
        logger.warning("⚠️ WebSocket client disabled (no SUPERVISOR_TOKEN - dev mode)")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop WebSocket client on shutdown"""
    if ha_websocket.ha_ws_client:
        logger.info("Stopping WebSocket client...")
        await ha_websocket.ha_ws_client.stop()
        logger.info("✅ WebSocket client stopped")




# Include routers
app.include_router(files.router, prefix="/api/files", tags=["Files"], dependencies=[Depends(verify_token)])
app.include_router(entities.router, prefix="/api/entities", tags=["Entities"], dependencies=[Depends(verify_token)])
app.include_router(helpers.router, prefix="/api/helpers", tags=["Helpers"], dependencies=[Depends(verify_token)])
app.include_router(automations.router, prefix="/api/automations", tags=["Automations"], dependencies=[Depends(verify_token)])
app.include_router(scripts.router, prefix="/api/scripts", tags=["Scripts"], dependencies=[Depends(verify_token)])
app.include_router(system.router, prefix="/api/system", tags=["System"], dependencies=[Depends(verify_token)])
app.include_router(backup.router, prefix="/api/backup", tags=["Backup"], dependencies=[Depends(verify_token)])
app.include_router(logs.router, prefix="/api/logs", tags=["Logs"], dependencies=[Depends(verify_token)])
app.include_router(logbook.router, prefix="/api/logbook", tags=["Logbook"], dependencies=[Depends(verify_token)])
app.include_router(hacs.router, prefix="/api/hacs", tags=["HACS"])
app.include_router(addons.router, prefix="/api/addons", tags=["Add-ons"])
app.include_router(lovelace.router, prefix="/api/lovelace", tags=["Lovelace"], dependencies=[Depends(verify_token)])
app.include_router(themes.router, prefix="/api/themes", tags=["Themes"], dependencies=[Depends(verify_token)])
app.include_router(registries.router, prefix="/api/registries", tags=["Registries"], dependencies=[Depends(verify_token)])
app.include_router(ai_instructions.router, prefix="/api/ai")


@app.get("/", response_class=HTMLResponse)
async def ingress_panel():
    """Ingress panel - shows ready-to-use JSON config"""
    return generate_ingress_html(API_KEY, AGENT_VERSION)


@app.post("/api/regenerate-key", dependencies=[Depends(verify_token)])
async def regenerate_api_key():
    """
    Regenerate API key.
    
    Security:
    - Requires a valid API key via Authorization: Bearer <API_KEY>
    - This prevents unauthenticated regeneration from arbitrary web pages,
      while still allowing the Ingress UI to call this endpoint as long as
      it passes the current key in the Authorization header.
    """
    global API_KEY
    
    try:
        import secrets
        from pathlib import Path
        
        logger.info("API key regeneration requested via ingress panel")
        
        # Generate new key
        new_key = secrets.token_urlsafe(32)
        
        # Save to file
        key_file = Path('/config/.ha_cursor_agent_key')
        key_file.write_text(new_key)
        
        # Update global variable
        API_KEY = new_key
        
        # Also update in set_api_key function
        set_api_key(new_key)
        
        logger.warning(f"🔄 API Key regenerated: {new_key[:8]}...{new_key[-8:]}")
        
        return {
            "success": True,
            "message": "API Key regenerated successfully",
            "new_key": new_key
        }
        
    except Exception as e:
        logger.error(f"Failed to regenerate key: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to regenerate key: {str(e)}")


@app.get("/old", response_class=HTMLResponse)
async def old_ingress_panel():
    """Old ingress panel (deprecated)"""
    
    # Mask API key for display (show first 8 and last 8 chars)
    masked_key = f"{API_KEY[:8]}...{API_KEY[-8:]}" if len(API_KEY) > 16 else API_KEY
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>HA Vibecode Agent - API Key</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                padding: 20px;
                background: #0d1117;
                color: #c9d1d9;
                line-height: 1.6;
            }}
            
            .container {{
                max-width: 800px;
                margin: 0 auto;
            }}
            
            h1 {{
                color: #58a6ff;
                margin-bottom: 10px;
                display: flex;
                align-items: center;
                gap: 12px;
            }}
            
            .version {{
                font-size: 14px;
                color: #8b949e;
                font-weight: normal;
                background: #161b22;
                padding: 4px 12px;
                border-radius: 12px;
            }}
            
            .card {{
                background: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 24px;
                margin: 20px 0;
            }}
            
            .card h2 {{
                color: #58a6ff;
                font-size: 18px;
                margin-bottom: 16px;
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            
            .key-display {{
                background: #0d1117;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 16px;
                font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, monospace;
                font-size: 14px;
                word-break: break-all;
                color: #79c0ff;
                margin-bottom: 12px;
                position: relative;
            }}
            
            .key-display.masked {{
                cursor: pointer;
                user-select: none;
            }}
            
            .key-display.masked:hover {{
                background: #161b22;
            }}
            
            .key-actions {{
                display: flex;
                gap: 8px;
                flex-wrap: wrap;
            }}
            
            button {{
                background: #238636;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 500;
                display: inline-flex;
                align-items: center;
                gap: 6px;
                transition: background 0.2s;
            }}
            
            button:hover {{
                background: #2ea043;
            }}
            
            button.secondary {{
                background: #21262d;
                border: 1px solid #30363d;
            }}
            
            button.secondary:hover {{
                background: #30363d;
            }}
            
            .code-block {{
                background: #0d1117;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 16px;
                font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, monospace;
                font-size: 13px;
                overflow-x: auto;
                margin: 12px 0;
            }}
            
            .code-block code {{
                color: #79c0ff;
            }}
            
            .info-box {{
                background: #1c2128;
                border-left: 3px solid #58a6ff;
                padding: 12px 16px;
                margin: 12px 0;
                border-radius: 4px;
            }}
            
            .info-box.warning {{
                border-left-color: #d29922;
            }}
            
            .info-box strong {{
                color: #58a6ff;
            }}
            
            .step {{
                display: flex;
                gap: 12px;
                margin: 16px 0;
            }}
            
            .step-number {{
                background: #238636;
                color: white;
                width: 28px;
                height: 28px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
                flex-shrink: 0;
            }}
            
            .step-content {{
                flex: 1;
            }}
            
            .success-message {{
                position: fixed;
                top: 20px;
                right: 20px;
                background: #238636;
                color: white;
                padding: 12px 20px;
                border-radius: 6px;
                box-shadow: 0 8px 24px rgba(0,0,0,0.4);
                display: none;
                animation: slideIn 0.3s ease;
            }}
            
            @keyframes slideIn {{
                from {{
                    transform: translateX(400px);
                    opacity: 0;
                }}
                to {{
                    transform: translateX(0);
                    opacity: 1;
                }}
            }}
            
            a {{
                color: #58a6ff;
                text-decoration: none;
            }}
            
            a:hover {{
                text-decoration: underline;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>
                🔑 HA Vibecode Agent
                <span class="version">v{AGENT_VERSION}</span>
            </h1>
            
            <div class="card">
                <h2>📋 Your API Key</h2>
                <div class="key-display masked" id="keyDisplay" onclick="toggleKey()">
                    {masked_key} <span style="color: #8b949e; font-size: 12px;">← Click to reveal</span>
                </div>
                <div class="key-actions">
                    <button onclick="copyKey()">
                        📋 Copy to Clipboard
                    </button>
                    <button class="secondary" onclick="toggleKey()">
                        👁️ Show/Hide
                    </button>
                </div>
            </div>
            
            <div class="card">
                <h2>🚀 Setup Instructions</h2>
                
                <div class="step">
                    <div class="step-number">1</div>
                    <div class="step-content">
                        <strong>Copy your API key</strong> using the button above
                    </div>
                </div>
                
                <div class="step">
                    <div class="step-number">2</div>
                    <div class="step-content">
                        <strong>Add to Cursor configuration</strong><br>
                        Open <code>~/.cursor/mcp.json</code> and add:
                        <div class="code-block"><code>{{
  "mcpServers": {{
    "home-assistant": {{
      "command": "npx",
      "args": ["-y", "@coolver/home-assistant-mcp@latest"],
      "env": {{
        "HA_AGENT_URL": "http://homeassistant.local:8099",
        "HA_AGENT_KEY": "YOUR_API_KEY_HERE"
      }}
    }}
  }}
}}</code></div>
                    </div>
                </div>
                
                <div class="step">
                    <div class="step-number">3</div>
                    <div class="step-content">
                        <strong>Restart Cursor</strong> to load the new configuration
                    </div>
                </div>
                
                <div class="step">
                    <div class="step-number">4</div>
                    <div class="step-content">
                        <strong>Test connection</strong> - Ask Cursor AI: "List my Home Assistant entities"
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h2>💡 Additional Information</h2>
                
                <div class="info-box">
                    <strong>🔒 Security:</strong> This API key is used ONLY to authenticate with this agent. The agent uses its internal supervisor token for Home Assistant API operations.
                </div>
                
                <div class="info-box warning">
                    <strong>⚠️ Keep your key safe:</strong> Don't share it publicly or commit it to git repositories.
                </div>
                
                <div class="info-box">
                    <strong>📁 Key location:</strong> Stored in <code>/config/.ha_cursor_agent_key</code>
                </div>
                
                <div class="info-box">
                    <strong>🔄 Regenerate key:</strong> Delete the file above and restart the add-on to generate a new key.
                </div>
            </div>
            
            <div class="card">
                <h2>📚 Resources</h2>
                <ul style="margin-left: 20px;">
                    <li><a href="/docs" target="_blank">API Documentation</a></li>
                    <li><a href="https://github.com/Coolver/home-assistant-cursor-agent" target="_blank">GitHub Repository</a></li>
                    <li><a href="https://www.npmjs.com/package/@coolver/home-assistant-mcp" target="_blank">MCP Package</a></li>
                </ul>
            </div>
        </div>
        
        <div class="success-message" id="successMessage">
            ✅ API Key copied to clipboard!
        </div>
        
        <script>
            const actualKey = "{API_KEY}";
            const maskedKey = "{masked_key}";
            let isKeyVisible = false;
            
            function toggleKey() {{
                const display = document.getElementById('keyDisplay');
                isKeyVisible = !isKeyVisible;
                
                if (isKeyVisible) {{
                    display.textContent = actualKey;
                    display.classList.remove('masked');
                }} else {{
                    display.innerHTML = maskedKey + ' <span style="color: #8b949e; font-size: 12px;">← Click to reveal</span>';
                    display.classList.add('masked');
                }}
            }}
            
            function copyKey() {{
                navigator.clipboard.writeText(actualKey).then(() => {{
                    const message = document.getElementById('successMessage');
                    message.style.display = 'block';
                    setTimeout(() => {{
                        message.style.display = 'none';
                    }}, 3000);
                }}).catch(err => {{
                    alert('Failed to copy: ' + err);
                }});
            }}
        </script>
    </body>
    </html>
    """
    
    return html_content


@app.get("/api/health")
async def health():
    """Health check endpoint (no auth required)"""
    return {
        "status": "healthy",
        "version": AGENT_VERSION,
        "config_path": os.getenv('CONFIG_PATH', '/config'),
        "git_versioning_auto": os.getenv('GIT_VERSIONING_AUTO', 'true') == 'true',
        "ai_instructions": "/api/ai/instructions"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8099))
    uvicorn.run(app, host="0.0.0.0", port=port)

