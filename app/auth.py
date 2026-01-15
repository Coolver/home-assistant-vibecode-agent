"""
Authentication and authorization utilities
"""
import os
import logging
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.env import load_env
load_env()

logger = logging.getLogger('ha_cursor_agent')

# Security
security = HTTPBearer()

# Get tokens from environment
SUPERVISOR_TOKEN = os.getenv('SUPERVISOR_TOKEN', '')  # Auto-provided by HA when running as add-on
DEV_TOKEN = os.getenv('HA_AGENT_KEY', '')  # For local development only

# Global variable for API key (will be set by main.py)
API_KEY = None


def set_api_key(key: str):
    """Set the API key (called from main.py)"""
    global API_KEY
    API_KEY = key


async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Verify API key.
    
    Add-on mode (SUPERVISOR_TOKEN exists):
    - Validates against configured API_KEY
    - Agent uses SUPERVISOR_TOKEN internally for all HA API operations
    
    Development mode (no SUPERVISOR_TOKEN):
    - Validates against DEV_TOKEN environment variable
    """
    token = credentials.credentials
    token_preview = f"{token[:20]}..." if len(token) > 20 else token
    
    if SUPERVISOR_TOKEN:
        # Add-on mode: Check against API_KEY
        if token != API_KEY:
            logger.warning(f"❌ Invalid API key: {token_preview}")
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        logger.debug(f"✅ API key validated: {token_preview}")
        logger.debug(f"Agent will use SUPERVISOR_TOKEN for HA API operations")
        return token
    else:
        # Development mode: Check against DEV_TOKEN
        logger.debug(f"Development mode: Checking token against DEV_TOKEN")
        if not DEV_TOKEN or token != DEV_TOKEN:
            logger.warning(f"❌ Token mismatch in development mode")
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        logger.info(f"✅ Token validated in development mode")
        return token


