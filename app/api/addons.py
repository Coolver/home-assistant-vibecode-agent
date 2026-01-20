"""Add-on Management API Endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

from app.models.schemas import Response
from app.auth import verify_token
from app.services.supervisor_client import get_supervisor_client

logger = logging.getLogger('ha_cursor_agent')
router = APIRouter()

# ==================== Request Models ====================

class AddonOptionsRequest(BaseModel):
    """Request model for setting add-on options"""
    options: Dict[str, Any]

class RepositoryRequest(BaseModel):
    """Request model for adding repository"""
    repository_url: str

# ==================== Endpoints ====================

@router.get("/store", response_model=Response, dependencies=[Depends(verify_token)])
async def list_store_addons():
    """
    List ALL add-ons from add-on store (full catalog)
    
    Returns complete catalog of add-ons from all connected repositories.
    Use this for browsing available add-ons and making recommendations.
    """
    try:
        supervisor = await get_supervisor_client()
        result = await supervisor.list_store_addons()
        
        # Parse response (may be list or dict)
        if isinstance(result, list):
            addons = result
        elif isinstance(result, dict):
            if 'addons' in result:
                addons = result['addons']
            elif 'data' in result and isinstance(result['data'], list):
                addons = result['data']
            elif 'data' in result and isinstance(result['data'], dict):
                addons = result['data'].get('addons', [])
            else:
                addons = []
        else:
            addons = []
        
        return Response(
            success=True,
            message=f"Found {len(addons)} add-ons in store catalog",
            data={
                'count': len(addons),
                'addons': addons
            }
        )
    except Exception as e:
        logger.error(f"Error listing store add-ons: {e}")
        return Response(success=False, message=f"Failed to list store add-ons: {str(e)}")

@router.get("/available", response_model=Response, dependencies=[Depends(verify_token)])
async def list_available_addons():
    """
    List all available add-ons (installed and available to install)
    
    Returns add-ons from all repositories including:
    - Official add-ons (core, community)
    - Custom repository add-ons
    - Installation status for each
    """
    try:
        supervisor = await get_supervisor_client()
        result = await supervisor.list_addons()
        
        addons = result.get('data', {}).get('addons', [])
        
        # Separate installed and available
        # An add-on is installed if it has a 'version' field (current installed version)
        installed = [a for a in addons if a.get('version')]
        available = [a for a in addons if not a.get('version')]
        
        return Response(
            success=True,
            message=f"Found {len(addons)} add-ons ({len(installed)} installed, {len(available)} available)",
            data={
                'total': len(addons),
                'installed_count': len(installed),
                'available_count': len(available),
                'installed': installed,
                'available': available,
                'all': addons
            }
        )
    except Exception as e:
        logger.error(f"Error listing add-ons: {e}")
        return Response(success=False, message=f"Failed to list add-ons: {str(e)}")

@router.get("/installed", response_model=Response, dependencies=[Depends(verify_token)])
async def list_installed_addons():
    """
    List only installed add-ons
    
    Returns add-ons that are currently installed on the system
    """
    try:
        supervisor = await get_supervisor_client()
        result = await supervisor.list_addons()
        
        addons = result.get('data', {}).get('addons', [])
        # An add-on is installed if it has a 'version' field (current installed version)
        installed = [a for a in addons if a.get('version')]
        
        return Response(
            success=True,
            message=f"Found {len(installed)} installed add-ons",
            data={
                'count': len(installed),
                'addons': installed
            }
        )
    except Exception as e:
        logger.error(f"Error listing installed add-ons: {e}")
        return Response(success=False, message=f"Failed to list installed add-ons: {str(e)}")

@router.get("/{slug}/info", response_model=Response, dependencies=[Depends(verify_token)])
async def get_addon_info(slug: str):
    """
    Get detailed information about a specific add-on
    
    Args:
        slug: Add-on slug (e.g., 'core_mosquitto', 'a0d7b954_zigbee2mqtt')
    
    Returns detailed information including:
    - Name, description, version
    - Installation status
    - Configuration options
    - State (started/stopped)
    - Resource usage
    """
    try:
        supervisor = await get_supervisor_client()
        result = await supervisor.get_addon_info(slug)
        
        addon_data = result.get('data', {})
        
        return Response(
            success=True,
            message=f"Add-on info: {addon_data.get('name', slug)}",
            data=addon_data
        )
    except Exception as e:
        logger.error(f"Error getting add-on info for {slug}: {e}")
        return Response(success=False, message=f"Failed to get add-on info: {str(e)}")

@router.get("/{slug}/logs", dependencies=[Depends(verify_token)])
async def get_addon_logs(slug: str, lines: Optional[int] = 100):
    """
    Get add-on logs
    
    Args:
        slug: Add-on slug
        lines: Number of lines to return (default: 100)
    
    Returns:
        Plain text logs
    """
    try:
        supervisor = await get_supervisor_client()
        logs = await supervisor.get_addon_logs(slug)
        
        # Return last N lines
        if lines:
            log_lines = logs.split('\n')
            logs = '\n'.join(log_lines[-lines:])
        
        return {
            "success": True,
            "message": f"Logs for {slug}",
            "logs": logs
        }
    except Exception as e:
        logger.error(f"Error getting logs for {slug}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {str(e)}")

@router.post("/{slug}/install", response_model=Response, dependencies=[Depends(verify_token)])
async def install_addon(slug: str):
    """
    Install an add-on
    
    Args:
        slug: Add-on slug to install
    
    Note: Installation can take several minutes depending on add-on size.
          The endpoint will wait for installation to complete.
    
    Returns:
        Installation result
    """
    try:
        supervisor = await get_supervisor_client()
        
        # Check if already installed
        info = await supervisor.get_addon_info(slug)
        addon_data = info.get('data', {})
        
        if addon_data.get('version'):
            return Response(
                success=True,
                message=f"Add-on '{addon_data.get('name', slug)}' is already installed (version {addon_data.get('version')})",
                data={
                    'slug': slug,
                    'name': addon_data.get('name'),
                    'version': addon_data.get('version'),
                    'already_installed': True
                }
            )
        
        # Install add-on
        logger.info(f"Starting installation of add-on: {slug}")
        result = await supervisor.install_addon(slug)
        
        # Get updated info
        info_after = await supervisor.get_addon_info(slug)
        addon_after = info_after.get('data', {})
        
        return Response(
            success=True,
            message=f"Add-on '{addon_after.get('name', slug)}' installed successfully (version {addon_after.get('version')})",
            data={
                'slug': slug,
                'name': addon_after.get('name'),
                'version': addon_after.get('version'),
                'installed': True,
                'state': addon_after.get('state'),
                'next_steps': "Configure add-on options if needed, then start it"
            }
        )
    except Exception as e:
        logger.error(f"Error installing add-on {slug}: {e}")
        return Response(success=False, message=f"Failed to install add-on: {str(e)}")

@router.post("/{slug}/uninstall", response_model=Response, dependencies=[Depends(verify_token)])
async def uninstall_addon(slug: str):
    """
    Uninstall an add-on
    
    Args:
        slug: Add-on slug to uninstall
    
    Warning: This will remove the add-on and its data!
    """
    try:
        supervisor = await get_supervisor_client()
        
        # Get info before uninstalling
        info = await supervisor.get_addon_info(slug)
        addon_data = info.get('data', {})
        addon_name = addon_data.get('name', slug)
        
        # Uninstall
        await supervisor.uninstall_addon(slug)
        
        return Response(
            success=True,
            message=f"Add-on '{addon_name}' uninstalled successfully",
            data={'slug': slug, 'name': addon_name}
        )
    except Exception as e:
        logger.error(f"Error uninstalling add-on {slug}: {e}")
        return Response(success=False, message=f"Failed to uninstall add-on: {str(e)}")

@router.post("/{slug}/start", response_model=Response, dependencies=[Depends(verify_token)])
async def start_addon(slug: str):
    """
    Start an add-on
    
    Args:
        slug: Add-on slug to start
    """
    try:
        supervisor = await get_supervisor_client()
        
        info = await supervisor.get_addon_info(slug)
        addon_name = info.get('data', {}).get('name', slug)
        
        await supervisor.start_addon(slug)
        
        return Response(
            success=True,
            message=f"Add-on '{addon_name}' started successfully",
            data={'slug': slug, 'name': addon_name, 'state': 'started'}
        )
    except Exception as e:
        logger.error(f"Error starting add-on {slug}: {e}")
        return Response(success=False, message=f"Failed to start add-on: {str(e)}")

@router.post("/{slug}/stop", response_model=Response, dependencies=[Depends(verify_token)])
async def stop_addon(slug: str):
    """
    Stop an add-on
    
    Args:
        slug: Add-on slug to stop
    """
    try:
        supervisor = await get_supervisor_client()
        
        info = await supervisor.get_addon_info(slug)
        addon_name = info.get('data', {}).get('name', slug)
        
        await supervisor.stop_addon(slug)
        
        return Response(
            success=True,
            message=f"Add-on '{addon_name}' stopped successfully",
            data={'slug': slug, 'name': addon_name, 'state': 'stopped'}
        )
    except Exception as e:
        logger.error(f"Error stopping add-on {slug}: {e}")
        return Response(success=False, message=f"Failed to stop add-on: {str(e)}")

@router.post("/{slug}/restart", response_model=Response, dependencies=[Depends(verify_token)])
async def restart_addon(slug: str):
    """
    Restart an add-on
    
    Args:
        slug: Add-on slug to restart
    """
    try:
        supervisor = await get_supervisor_client()
        
        info = await supervisor.get_addon_info(slug)
        addon_name = info.get('data', {}).get('name', slug)
        
        await supervisor.restart_addon(slug)
        
        return Response(
            success=True,
            message=f"Add-on '{addon_name}' restarted successfully",
            data={'slug': slug, 'name': addon_name, 'state': 'restarted'}
        )
    except Exception as e:
        logger.error(f"Error restarting add-on {slug}: {e}")
        return Response(success=False, message=f"Failed to restart add-on: {str(e)}")

@router.post("/{slug}/update", response_model=Response, dependencies=[Depends(verify_token)])
async def update_addon(slug: str):
    """
    Update an add-on to latest version
    
    Args:
        slug: Add-on slug to update
    
    Note: Update can take several minutes.
    """
    try:
        supervisor = await get_supervisor_client()
        
        info_before = await supervisor.get_addon_info(slug)
        addon_data = info_before.get('data', {})
        addon_name = addon_data.get('name', slug)
        version_before = addon_data.get('version')
        
        await supervisor.update_addon(slug)
        
        # Get new version
        info_after = await supervisor.get_addon_info(slug)
        version_after = info_after.get('data', {}).get('version')
        
        return Response(
            success=True,
            message=f"Add-on '{addon_name}' updated from {version_before} to {version_after}",
            data={
                'slug': slug,
                'name': addon_name,
                'version_before': version_before,
                'version_after': version_after
            }
        )
    except Exception as e:
        logger.error(f"Error updating add-on {slug}: {e}")
        return Response(success=False, message=f"Failed to update add-on: {str(e)}")

@router.get("/{slug}/options", response_model=Response, dependencies=[Depends(verify_token)])
async def get_addon_options(slug: str):
    """
    Get add-on configuration options
    
    Args:
        slug: Add-on slug
    """
    try:
        supervisor = await get_supervisor_client()
        options = await supervisor.get_addon_options(slug)
        
        return Response(
            success=True,
            message=f"Current options for {slug}",
            data={'options': options}
        )
    except Exception as e:
        logger.error(f"Error getting options for {slug}: {e}")
        return Response(success=False, message=f"Failed to get add-on options: {str(e)}")

@router.post("/{slug}/options", response_model=Response, dependencies=[Depends(verify_token)])
async def set_addon_options(slug: str, request: AddonOptionsRequest):
    """
    Set add-on configuration options
    
    Args:
        slug: Add-on slug
        request: Configuration options to set
    
    Note: Add-on may need to be restarted for changes to take effect
    """
    try:
        supervisor = await get_supervisor_client()
        
        info = await supervisor.get_addon_info(slug)
        addon_name = info.get('data', {}).get('name', slug)
        
        await supervisor.set_addon_options(slug, request.options)
        
        return Response(
            success=True,
            message=f"Options updated for '{addon_name}'. Restart add-on if needed.",
            data={
                'slug': slug,
                'name': addon_name,
                'options': request.options,
                'restart_needed': True
            }
        )
    except Exception as e:
        logger.error(f"Error setting options for {slug}: {e}")
        return Response(success=False, message=f"Failed to set add-on options: {str(e)}")

@router.get("/repositories", response_model=Response, dependencies=[Depends(verify_token)])
async def list_repositories():
    """
    List all add-on repositories
    """
    try:
        supervisor = await get_supervisor_client()
        result = await supervisor.list_repositories()
        
        # Supervisor API may return different formats
        if isinstance(result, list):
            # Format 1: Direct list
            repos = result
        elif isinstance(result, dict):
            # Format 2: {'repositories': [...]}
            if 'repositories' in result:
                repos = result['repositories']
            # Format 3: {'data': [...]} (data is list)
            elif 'data' in result and isinstance(result['data'], list):
                repos = result['data']
            # Format 4: {'data': {'repositories': [...]}}
            elif 'data' in result and isinstance(result['data'], dict):
                repos = result['data'].get('repositories', [])
            else:
                repos = []
        else:
            repos = []
        
        return Response(
            success=True,
            message=f"Found {len(repos)} repositories",
            data={'count': len(repos), 'repositories': repos}
        )
    except Exception as e:
        logger.error(f"Error listing repositories: {e}")
        return Response(success=False, message=f"Failed to list repositories: {str(e)}")

@router.post("/repositories/add", response_model=Response, dependencies=[Depends(verify_token)])
async def add_repository(request: RepositoryRequest):
    """
    Add a custom add-on repository
    
    Args:
        request: Repository URL to add
    """
    try:
        supervisor = await get_supervisor_client()
        await supervisor.add_repository(request.repository_url)
        
        return Response(
            success=True,
            message=f"Repository added: {request.repository_url}",
            data={'repository_url': request.repository_url}
        )
    except Exception as e:
        error_msg = str(e)
        # Extract more user-friendly error message from Supervisor API response
        if "git clone" in error_msg or "fatal:" in error_msg:
            if "could not read Username" in error_msg or "No such device or address" in error_msg:
                error_msg = f"Repository not found or not accessible: {request.repository_url}. Please check that the repository exists and is publicly accessible."
            elif "repository not found" in error_msg.lower():
                error_msg = f"Repository not found: {request.repository_url}. Please verify the repository URL is correct."
            elif "authentication" in error_msg.lower() or "permission" in error_msg.lower():
                error_msg = f"Authentication failed for repository: {request.repository_url}. Private repositories are not supported."
        
        logger.error(f"Error adding repository {request.repository_url}: {e}")
        return Response(success=False, message=f"Failed to add repository: {error_msg}")

