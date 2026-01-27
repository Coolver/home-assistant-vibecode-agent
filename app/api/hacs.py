"""HACS API endpoints"""
from fastapi import APIRouter, HTTPException, Depends
import logging
import aiohttp
import zipfile
import io
import os
from pathlib import Path
from typing import Optional


def safe_extract_zip(zip_content: bytes, target_dir: str) -> None:
    """Safely extract ZIP, preventing path traversal attacks."""
    target_path = Path(target_dir).resolve()

    with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_file:
        for member in zip_file.namelist():
            member_path = (target_path / member).resolve()
            # Verify path stays within target directory
            if not str(member_path).startswith(str(target_path)):
                raise ValueError(f"Path traversal detected in ZIP: {member}")
        # All paths validated, safe to extract
        zip_file.extractall(target_dir)

from app.models.schemas import Response
from app.services.ha_client import ha_client
from app.services.ha_websocket import get_ws_client
from app.auth import verify_token

router = APIRouter()
logger = logging.getLogger('ha_cursor_agent')

HACS_GITHUB_REPO = "hacs/integration"
HACS_INSTALL_PATH = "/config/custom_components/hacs"


@router.post("/install", response_model=Response, dependencies=[Depends(verify_token)])
async def install_hacs():
    """
    Install HACS (Home Assistant Community Store)
    
    This will:
    1. Download latest HACS release from GitHub
    2. Extract to custom_components/hacs
    3. Restart Home Assistant
    
    **⚠️ Note:** Home Assistant will restart automatically after installation
    """
    try:
        logger.info("Starting HACS installation...")
        
        # Check if HACS already installed
        hacs_path = Path(HACS_INSTALL_PATH)
        if hacs_path.exists():
            logger.info("HACS is already installed")
            return Response(
                success=True,
                message="HACS is already installed",
                data={"version": "unknown", "path": HACS_INSTALL_PATH}
            )
        
        # Get latest HACS release from GitHub
        logger.info(f"Fetching latest HACS release from GitHub: {HACS_GITHUB_REPO}")
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.github.com/repos/{HACS_GITHUB_REPO}/releases/latest") as resp:
                if resp.status != 200:
                    raise HTTPException(status_code=500, detail="Failed to fetch HACS release info")
                release_data = await resp.json()
        
        version = release_data.get("tag_name", "unknown")
        download_url = None
        
        # Find the ZIP asset
        for asset in release_data.get("assets", []):
            if asset["name"] == "hacs.zip":
                download_url = asset["browser_download_url"]
                break
        
        if not download_url:
            raise HTTPException(status_code=500, detail="HACS download URL not found")
        
        logger.info(f"Downloading HACS {version} from {download_url}")
        
        # Download HACS ZIP
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url) as resp:
                if resp.status != 200:
                    raise HTTPException(status_code=500, detail="Failed to download HACS")
                zip_content = await resp.read()
        
        logger.info(f"Downloaded {len(zip_content)} bytes")
        
        # Extract ZIP to custom_components/hacs
        logger.info(f"Extracting HACS to {HACS_INSTALL_PATH}")
        os.makedirs(HACS_INSTALL_PATH, exist_ok=True)
        
        safe_extract_zip(zip_content, HACS_INSTALL_PATH)
        
        logger.info("HACS extracted successfully")
        
        # Restart Home Assistant
        logger.warning("Restarting Home Assistant to load HACS...")
        try:
            await ha_client.restart()
        except Exception as restart_error:
            logger.warning(f"Restart command sent, but got error (this is normal): {restart_error}")
        
        return Response(
            success=True,
            message=f"HACS {version} installed successfully. Home Assistant is restarting...",
            data={
                "version": version,
                "path": HACS_INSTALL_PATH,
                "restart_initiated": True
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to install HACS: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/uninstall", response_model=Response, dependencies=[Depends(verify_token)])
async def uninstall_hacs():
    """
    Uninstall HACS (Home Assistant Community Store)
    
    This will:
    1. Remove custom_components/hacs directory
    2. Remove HACS storage files
    3. Restart Home Assistant
    
    **⚠️ Warning:** This will remove HACS and all its data
    **⚠️ Note:** Home Assistant will restart automatically after uninstallation
    """
    try:
        logger.info("Starting HACS uninstallation...")
        
        # Check if HACS installed
        hacs_path = Path(HACS_INSTALL_PATH)
        if not hacs_path.exists():
            return Response(
                success=True,
                message="HACS is not installed",
                data={"was_installed": False}
            )
        
        # Remove HACS directory
        logger.info(f"Removing HACS directory: {HACS_INSTALL_PATH}")
        import shutil
        shutil.rmtree(HACS_INSTALL_PATH)
        logger.info("HACS directory removed")
        
        # Remove HACS storage files
        storage_path = Path("/config/.storage")
        if storage_path.exists():
            hacs_storage_files = list(storage_path.glob("hacs*"))
            for file in hacs_storage_files:
                logger.info(f"Removing HACS storage file: {file}")
                file.unlink()
        
        logger.info("HACS uninstalled successfully")
        
        # Restart Home Assistant
        logger.warning("Restarting Home Assistant to apply changes...")
        try:
            await ha_client.restart()
        except Exception as restart_error:
            logger.warning(f"Restart command sent, but got error (this is normal): {restart_error}")
        
        return Response(
            success=True,
            message="HACS uninstalled successfully. Home Assistant is restarting...",
            data={
                "removed_path": HACS_INSTALL_PATH,
                "restart_initiated": True
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to uninstall HACS: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=Response, dependencies=[Depends(verify_token)])
async def get_hacs_status():
    """
    Check if HACS is installed and get version info
    """
    try:
        hacs_path = Path(HACS_INSTALL_PATH)
        
        if not hacs_path.exists():
            return Response(
                success=True,
                message="HACS is not installed",
                data={
                    "installed": False,
                    "path": HACS_INSTALL_PATH
                }
            )
        
        # Try to read version from manifest
        manifest_path = hacs_path / "manifest.json"
        version = "unknown"
        
        if manifest_path.exists():
            import json
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
                version = manifest.get("version", "unknown")
        
        return Response(
            success=True,
            message="HACS is installed",
            data={
                "installed": True,
                "version": version,
                "path": HACS_INSTALL_PATH
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to check HACS status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repositories", response_model=Response, dependencies=[Depends(verify_token)])
async def list_hacs_repositories(category: Optional[str] = None):
    """
    List HACS repositories by reading storage file
    
    **Parameters:**
    - category: Filter by category (integration, plugin, theme, appdaemon, netdaemon, python_script)
    
    **Note:** Requires HACS to be installed and configured via UI first.
    HACS stores repository data in /config/.storage/hacs.repositories
    """
    try:
        logger.info(f"Listing HACS repositories (category: {category or 'all'})...")
        
        # Check if HACS is installed
        hacs_path = Path(HACS_INSTALL_PATH)
        if not hacs_path.exists():
            raise HTTPException(
                status_code=400,
                detail="HACS is not installed. Please install HACS first using /api/hacs/install"
            )
        
        # Try to read HACS storage file
        hacs_storage_path = Path("/config/.storage/hacs.repositories")
        hacs_repos = []
        
        if hacs_storage_path.exists():
            try:
                import json
                with open(hacs_storage_path, 'r', encoding='utf-8') as f:
                    storage_data = json.load(f)
                
                # Log file structure for debugging
                logger.debug(f"HACS storage file keys: {list(storage_data.keys())}")
                
                # HACS stores data in 'data' object directly (not 'data' -> 'repositories')
                # The 'data' key contains a dictionary where keys are repository IDs
                repositories_data = storage_data.get('data', {})
                
                # If 'data' is empty, try alternative structures
                if not repositories_data:
                    # Try 'data' -> 'repositories' structure (older format)
                    repositories_data = storage_data.get('data', {}).get('repositories', {})
                    logger.debug(f"Trying 'data.repositories' structure, found {len(repositories_data)} entries")
                
                # If still empty, try direct 'repositories' key
                if not repositories_data:
                    repositories_data = storage_data.get('repositories', {})
                    logger.debug(f"Trying direct 'repositories' key, found {len(repositories_data)} entries")
                
                logger.info(f"HACS storage file contains {len(repositories_data)} repository entries")
                
                for repo_id, repo_info in repositories_data.items():
                    repo_category = repo_info.get('category', '')
                    
                    # Filter by category if specified
                    if category is None or repo_category == category:
                        # Determine if repository is installed
                        # HACS uses 'installed' boolean and 'version_installed' (not 'installed_version')
                        installed = repo_info.get('installed', False) or repo_info.get('version_installed') is not None
                        
                        # Extract name from full_name if name is not available
                        repo_name = repo_info.get('name', '')
                        if not repo_name:
                            full_name = repo_info.get('full_name', '')
                            repo_name = full_name.split('/')[-1] if '/' in full_name else full_name
                        
                        hacs_repos.append({
                            'repository_id': repo_id,
                            'full_name': repo_info.get('full_name', ''),
                            'name': repo_name,
                            'category': repo_category,
                            'installed': installed,
                            'available_version': repo_info.get('available_version') or repo_info.get('version_available'),
                            'installed_version': repo_info.get('installed_version') or repo_info.get('version_installed'),
                            'description': repo_info.get('description', ''),
                            'stars': repo_info.get('stars', 0) or repo_info.get('stargazers_count', 0),
                            'downloads': repo_info.get('downloads', 0),
                        })
                
                logger.info(f"Found {len(hacs_repos)} HACS repositories from storage file")
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse HACS storage file: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to parse HACS storage file: {str(e)}")
            except Exception as e:
                logger.error(f"Error reading HACS storage file: {e}")
                raise HTTPException(status_code=500, detail=f"Error reading HACS storage file: {str(e)}")
        else:
            logger.warning(f"HACS storage file not found at {hacs_storage_path}")
            # Fallback: try to get installed integrations via API
            try:
                ws_client = await get_ws_client()
                # Try to get integrations list via WebSocket
                # Note: This will only show installed integrations, not all available repositories
                logger.info("HACS storage file not found, trying alternative method...")
            except Exception as e:
                logger.error(f"Failed to get HACS repositories: {e}")
        
        return Response(
            success=True,
            message=f"Found {len(hacs_repos)} HACS repositories",
            data={
                'repositories': hacs_repos,
                'count': len(hacs_repos),
                'category': category or 'all'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list HACS repositories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/install_repository", response_model=Response, dependencies=[Depends(verify_token)])
async def install_hacs_repository(repository: str, category: str = "integration"):
    """
    Install a repository from HACS via WebSocket
    
    **Parameters:**
    - repository: Repository name (e.g., "AlexxIT/XiaomiGateway3")
    - category: Type of repository (integration, theme, plugin, appdaemon, netdaemon, python_script)
    
    **Note:** Requires HACS to be installed and configured via UI first.
    
    **⚠️ Important:** 
    - Home Assistant may need to be restarted after installation
    - For integrations, configuration may be needed via UI
    """
    try:
        logger.info(f"Installing HACS repository: {repository} (category: {category})")
        
        # Check if HACS is installed
        hacs_path = Path(HACS_INSTALL_PATH)
        if not hacs_path.exists():
            raise HTTPException(
                status_code=400,
                detail="HACS is not installed. Please install HACS first using /api/hacs/install"
            )
        
        # Get WebSocket client
        ws_client = await get_ws_client()
        
        # Call HACS download service via WebSocket
        logger.info(f"Calling hacs/download service for {repository}...")
        
        result = await ws_client.call_service(
            domain='hacs',
            service='download',
            service_data={
                'repository': repository
            }
        )
        
        logger.info(f"WebSocket service call result: {result}")
        
        # Verify installation by checking repository status
        # Wait a moment for HACS to update its storage
        import asyncio
        await asyncio.sleep(1)
        
        # Check if repository is now installed by reading storage file
        verification_status = None
        hacs_storage_path = Path("/config/.storage/hacs.repositories")
        if hacs_storage_path.exists():
            try:
                import json
                with open(hacs_storage_path, 'r', encoding='utf-8') as f:
                    storage_data = json.load(f)
                
                repositories_data = storage_data.get('data', {})
                
                # Find repository by full_name
                logger.debug(f"Verifying installation: searching for repository '{repository}' in {len(repositories_data)} repositories")
                for repo_id, repo_info in repositories_data.items():
                    if repo_info.get('full_name') == repository:
                        is_installed = repo_info.get('installed', False) or repo_info.get('version_installed') is not None
                        verification_status = {
                            'found': True,
                            'installed': is_installed,
                            'version_installed': repo_info.get('version_installed'),
                        }
                        logger.info(f"Verification: repository '{repository}' found, installed={is_installed}, version={repo_info.get('version_installed')}")
                        break
                
                if not verification_status:
                    logger.warning(f"Verification: repository '{repository}' not found in storage yet (may need refresh)")
                    verification_status = {'found': False, 'note': 'Repository not found in storage yet (may need refresh)'}
            except Exception as verify_error:
                logger.warning(f"Could not verify installation: {verify_error}")
                verification_status = {'error': str(verify_error)}
        
        logger.info(f"✅ HACS repository installation initiated: {repository}")
        
        # Determine if restart needed
        restart_needed = category in ['integration', 'python_script']
        
        return Response(
            success=True,
            message=f"Repository installation initiated: {repository}",
            data={
                'repository': repository,
                'category': category,
                'websocket_result': result,
                'verification': verification_status,
                'installed': verification_status.get('installed', False) if verification_status else None,
                'restart_needed': restart_needed,
                'next_steps': [
                    'Wait a few seconds and check repository status',
                    'Restart Home Assistant if installing integration' if restart_needed else 'Repository ready to use',
                    'Configure integration in HA UI if needed'
                ]
            }
        )
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to install HACS repository: {error_msg}")
        
        # Provide helpful error messages
        if 'not connected' in error_msg.lower():
            raise HTTPException(
                status_code=503,
                detail="WebSocket not connected. Agent may still be starting up. Wait a few seconds and try again."
            )
        elif 'not found' in error_msg.lower() or 'unknown service' in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail="HACS service not found. Please configure HACS in Home Assistant UI first: Settings → Devices & Services → HACS"
            )
        else:
            raise HTTPException(status_code=500, detail=error_msg)


@router.get("/search", response_model=Response, dependencies=[Depends(verify_token)])
async def search_hacs_repositories(query: str, category: Optional[str] = None):
    """
    Search HACS repositories via WebSocket
    
    **Parameters:**
    - query: Search query (repository name, author, description)
    - category: Filter by category (optional)
    
    **Returns:**
    Matching repositories with details
    """
    try:
        logger.info(f"Searching HACS repositories: '{query}' (category: {category or 'all'})")
        
        # Get WebSocket client
        ws_client = await get_ws_client()
        
        # Get all states
        states = await ws_client.get_states()
        
        # Search in HACS sensors
        matching_repos = []
        query_lower = query.lower()
        
        for state in states:
            entity_id = state.get('entity_id', '')
            
            if entity_id.startswith('sensor.hacs_'):
                attributes = state.get('attributes', {})
                repo_category = attributes.get('category', '')
                repo_name = attributes.get('friendly_name', '')
                repo_id = attributes.get('repository', '')
                repo_description = attributes.get('description', '')
                
                # Filter by category
                if category and repo_category != category:
                    continue
                
                # Search in name, repository, or description
                if (query_lower in repo_name.lower() or 
                    query_lower in repo_id.lower() or 
                    query_lower in repo_description.lower()):
                    
                    matching_repos.append({
                        'entity_id': entity_id,
                        'name': repo_name,
                        'repository': repo_id,
                        'category': repo_category,
                        'description': repo_description,
                        'installed': attributes.get('installed', False),
                        'available_version': attributes.get('available_version'),
                        'installed_version': attributes.get('installed_version'),
                        'stars': attributes.get('stars', 0),
                        'authors': attributes.get('authors', []),
                    })
        
        logger.info(f"Found {len(matching_repos)} matching repositories")
        
        return Response(
            success=True,
            message=f"Found {len(matching_repos)} repositories matching '{query}'",
            data={
                'repositories': matching_repos,
                'count': len(matching_repos),
                'query': query,
                'category': category or 'all'
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to search HACS repositories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update_all", response_model=Response, dependencies=[Depends(verify_token)])
async def update_all_hacs():
    """
    Update all HACS repositories to latest versions
    
    **⚠️ Warning:** This will update all installed HACS integrations.
    Restart may be required after updates.
    """
    try:
        logger.info("Updating all HACS repositories...")
        
        # Get WebSocket client
        ws_client = await get_ws_client()
        
        # Get list of installed repositories before update
        installed_before = []
        hacs_storage_path = Path("/config/.storage/hacs.repositories")
        if hacs_storage_path.exists():
            try:
                import json
                with open(hacs_storage_path, 'r', encoding='utf-8') as f:
                    storage_data = json.load(f)
                
                repositories_data = storage_data.get('data', {})
                
                logger.info(f"Reading {len(repositories_data)} repositories to get versions before update")
                for repo_id, repo_info in repositories_data.items():
                    if repo_info.get('installed', False) or repo_info.get('version_installed') is not None:
                        repo_name = repo_info.get('full_name', '')
                        version = repo_info.get('version_installed')
                        installed_before.append({
                            'repository': repo_name,
                            'version_before': version,
                        })
                        logger.debug(f"Repository to update: {repo_name} (current version: {version})")
                logger.info(f"Found {len(installed_before)} installed repositories to update")
            except Exception as e:
                logger.warning(f"Could not read repositories before update: {e}")
        
        # Call HACS update_all service
        logger.info(f"Calling hacs/update_all service for {len(installed_before)} repositories...")
        result = await ws_client.call_service(
            domain='hacs',
            service='update_all',
            service_data={}
        )
        
        logger.info(f"WebSocket service call result: {result}")
        logger.info("✅ HACS update initiated for all repositories")
        
        return Response(
            success=True,
            message=f"Update initiated for {len(installed_before)} installed repositories",
            data={
                'websocket_result': result,
                'repositories_count': len(installed_before),
                'repositories_before': installed_before,
                'restart_needed': True,
                'next_steps': [
                    'Wait for downloads to complete (check HACS UI or logs)',
                    'Use /api/hacs/repositories to check updated versions',
                    'Restart Home Assistant to apply updates',
                    'Check logs for any errors'
                ],
                'verification': 'Check repository versions after a few seconds using /api/hacs/repositories'
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to update HACS repositories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repository/{repository_id}", response_model=Response, dependencies=[Depends(verify_token)])
async def get_hacs_repository_details(repository_id: str):
    """
    Get detailed information about a specific HACS repository
    
    **Parameters:**
    - repository_id: Repository identifier (e.g., "123456789" or "author/repo")
    
    **Returns:**
    Detailed repository information
    """
    try:
        logger.info(f"Getting HACS repository details: {repository_id}")
        
        # Get WebSocket client
        ws_client = await get_ws_client()
        
        # Get all states
        states = await ws_client.get_states()
        
        # Find matching repository
        for state in states:
            entity_id = state.get('entity_id', '')
            
            if entity_id.startswith('sensor.hacs_'):
                attributes = state.get('attributes', {})
                repo = attributes.get('repository', '')
                
                # Match by repository name or entity_id
                if repository_id in entity_id or repository_id in repo:
                    return Response(
                        success=True,
                        message=f"Repository details: {repo}",
                        data={
                            'entity_id': entity_id,
                            'repository': repo,
                            'name': attributes.get('friendly_name', ''),
                            'category': attributes.get('category', ''),
                            'description': attributes.get('description', ''),
                            'installed': attributes.get('installed', False),
                            'available_version': attributes.get('available_version'),
                            'installed_version': attributes.get('installed_version'),
                            'stars': attributes.get('stars', 0),
                            'authors': attributes.get('authors', []),
                            'downloads': attributes.get('downloads', 0),
                            'last_updated': attributes.get('last_updated'),
                            'topics': attributes.get('topics', []),
                            'state': state.get('state'),
                        }
                    )
        
        # Not found
        raise HTTPException(
            status_code=404,
            detail=f"Repository not found: {repository_id}. Make sure HACS is configured and repository exists."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get repository details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

