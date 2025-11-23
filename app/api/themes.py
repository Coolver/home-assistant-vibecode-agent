"""Themes API endpoints"""
from fastapi import APIRouter, HTTPException, Body, Query
from typing import List, Dict, Optional, Any
import logging
import yaml

from app.services.file_manager import file_manager
from app.services.ha_client import ha_client

router = APIRouter()
logger = logging.getLogger('ha_cursor_agent')


@router.get("/list")
async def list_themes():
    """
    List all available themes
    
    Returns list of theme files in themes/ directory
    """
    try:
        # List all YAML files in themes directory
        files = await file_manager.list_files("themes", "*.yaml")
        
        # Also check for .yml files
        yml_files = await file_manager.list_files("themes", "*.yml")
        files.extend(yml_files)
        
        # Extract theme names from files
        themes = []
        for file_info in files:
            theme_name = file_info['name'].replace('.yaml', '').replace('.yml', '')
            themes.append({
                "name": theme_name,
                "file": file_info['path'],
                "size": file_info['size'],
                "modified": file_info['modified']
            })
        
        logger.info(f"Listed {len(themes)} themes")
        return {
            "success": True,
            "count": len(themes),
            "themes": themes
        }
    except Exception as e:
        logger.error(f"Failed to list themes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get")
async def get_theme(
    theme_name: str = Query(..., description="Theme name (without .yaml extension)")
):
    """
    Get theme content
    
    Example:
    - `/api/themes/get?theme_name=nice_dark`
    """
    try:
        # Try .yaml first, then .yml
        file_path = f"themes/{theme_name}.yaml"
        try:
            content = await file_manager.read_file(file_path)
        except FileNotFoundError:
            file_path = f"themes/{theme_name}.yml"
            content = await file_manager.read_file(file_path)
        
        # Parse YAML to get theme data
        theme_data = yaml.safe_load(content)
        
        return {
            "success": True,
            "theme_name": theme_name,
            "file": file_path,
            "content": content,
            "data": theme_data
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Theme '{theme_name}' not found")
    except Exception as e:
        logger.error(f"Failed to get theme {theme_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create")
async def create_theme(
    theme_name: str = Body(..., description="Theme name (without .yaml extension)"),
    theme_config: Dict[str, Any] = Body(..., description="Theme configuration (CSS variables)")
):
    """
    Create a new theme
    
    Example:
    {
        "theme_name": "nice_dark",
        "theme_config": {
            "primary-color": "#ffb74d",
            "accent-color": "#ffb74d",
            "primary-background-color": "#101018",
            ...
        }
    }
    """
    try:
        # Create YAML content
        theme_yaml = {theme_name: theme_config}
        content = yaml.dump(theme_yaml, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
        # Write theme file
        file_path = f"themes/{theme_name}.yaml"
        result = await file_manager.write_file(file_path, content)
        
        logger.info(f"Created theme: {theme_name}")
        return {
            "success": True,
            "theme_name": theme_name,
            "file": file_path,
            "message": f"Theme '{theme_name}' created. Don't forget to reload themes (frontend.reload_themes) or restart HA."
        }
    except Exception as e:
        logger.error(f"Failed to create theme {theme_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create theme: {str(e)}")


@router.put("/update")
async def update_theme(
    theme_name: str = Body(..., description="Theme name (without .yaml extension)"),
    theme_config: Dict[str, Any] = Body(..., description="Theme configuration (CSS variables)")
):
    """
    Update an existing theme
    
    Example:
    {
        "theme_name": "nice_dark",
        "theme_config": {
            "primary-color": "#ffb74d",
            "accent-color": "#ffb74d",
            ...
        }
    }
    """
    try:
        # Check if theme exists
        try:
            await get_theme(theme_name)
        except HTTPException as e:
            if e.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Theme '{theme_name}' not found. Use POST /create to create a new theme.")
            raise
        
        # Create YAML content
        theme_yaml = {theme_name: theme_config}
        content = yaml.dump(theme_yaml, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
        # Write theme file
        file_path = f"themes/{theme_name}.yaml"
        result = await file_manager.write_file(file_path, content)
        
        logger.info(f"Updated theme: {theme_name}")
        return {
            "success": True,
            "theme_name": theme_name,
            "file": file_path,
            "message": f"Theme '{theme_name}' updated. Don't forget to reload themes (frontend.reload_themes) or restart HA."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update theme {theme_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update theme: {str(e)}")


@router.delete("/delete")
async def delete_theme(
    theme_name: str = Query(..., description="Theme name (without .yaml extension)")
):
    """
    Delete a theme
    
    Example:
    - `/api/themes/delete?theme_name=nice_dark`
    """
    try:
        # Try .yaml first, then .yml
        file_path = f"themes/{theme_name}.yaml"
        try:
            await file_manager.read_file(file_path)
        except FileNotFoundError:
            file_path = f"themes/{theme_name}.yml"
            await file_manager.read_file(file_path)
        
        # Delete file
        result = await file_manager.delete_file(file_path)
        
        logger.info(f"Deleted theme: {theme_name}")
        return {
            "success": True,
            "theme_name": theme_name,
            "file": file_path,
            "message": f"Theme '{theme_name}' deleted. Don't forget to reload themes (frontend.reload_themes) or restart HA."
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Theme '{theme_name}' not found")
    except Exception as e:
        logger.error(f"Failed to delete theme {theme_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete theme: {str(e)}")


@router.post("/reload")
async def reload_themes():
    """
    Reload themes in Home Assistant
    
    Calls frontend.reload_themes service
    """
    try:
        result = await ha_client.call_service('frontend', 'reload_themes', {})
        logger.info("Reloaded themes")
        return {
            "success": True,
            "message": "Themes reloaded successfully"
        }
    except Exception as e:
        logger.error(f"Failed to reload themes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reload themes: {str(e)}")


@router.get("/check_config")
async def check_theme_config():
    """
    Check if themes are configured in configuration.yaml
    
    Returns whether themes directory is included in configuration
    """
    try:
        config_content = await file_manager.read_file("configuration.yaml")
        
        # Check if themes are configured
        has_themes_config = "themes:" in config_content and "!include_dir_merge_named themes" in config_content
        
        # Check if themes directory exists
        themes_dir_exists = False
        try:
            files = await file_manager.list_files("themes")
            themes_dir_exists = True
        except:
            pass
        
        return {
            "success": True,
            "themes_configured": has_themes_config,
            "themes_directory_exists": themes_dir_exists,
            "message": "Themes are configured" if has_themes_config else "Themes not configured in configuration.yaml. Add 'themes: !include_dir_merge_named themes' under 'frontend:' section."
        }
    except Exception as e:
        logger.error(f"Failed to check theme config: {e}")
        raise HTTPException(status_code=500, detail=str(e))



