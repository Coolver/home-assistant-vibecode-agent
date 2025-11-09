"""System API endpoints"""
from fastapi import APIRouter, HTTPException, Query
import logging

from app.models.schemas import Response
from app.services.ha_client import ha_client

router = APIRouter()
logger = logging.getLogger('ha_cursor_agent')

@router.post("/reload", response_model=Response)
async def reload_component(
    component: str = Query(..., description="Component to reload: automations, scripts, templates, core, all")
):
    """
    Reload Home Assistant component
    
    **Available components:**
    - `automations` - Reload automations
    - `scripts` - Reload scripts
    - `templates` - Reload template entities
    - `core` - Reload core configuration
    - `all` - Reload all reloadable components
    
    **Example:**
    - `/api/system/reload?component=automations`
    """
    try:
        result = await ha_client.reload_component(component)
        logger.info(f"Reloaded component: {component}")
        
        return Response(
            success=True,
            message=f"Component reloaded: {component}",
            data=result
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to reload component: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/check-config", response_model=Response)
@router.post("/check_config", response_model=Response)  # Legacy compatibility
async def check_config():
    """
    Check Home Assistant configuration validity
    
    Returns validation results
    """
    try:
        result = await ha_client.check_config()
        logger.info("Configuration check completed")
        
        return Response(
            success=True,
            message="Configuration is valid",
            data=result
        )
    except Exception as e:
        logger.error(f"Configuration check failed: {e}")
        return Response(
            success=False,
            message=f"Configuration has errors: {e}",
            data=None
        )

@router.post("/restart", response_model=Response)
async def restart_ha():
    """
    Restart Home Assistant
    
    **⚠️ WARNING: This will restart your Home Assistant instance!**
    """
    try:
        await ha_client.restart()
        logger.warning("Home Assistant restart initiated")
        
        return Response(
            success=True,
            message="Home Assistant restart initiated"
        )
    except Exception as e:
        logger.error(f"Failed to restart HA: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config")
async def get_config():
    """Get Home Assistant configuration"""
    try:
        config = await ha_client.get_config()
        return {
            "success": True,
            "config": config
        }
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

