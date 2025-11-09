"""Lovelace Dashboard API Endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
import yaml

from app.models.schemas import Response
from app.auth import verify_token
from app.services.lovelace_generator import lovelace_generator
from app.services.ha_client import ha_client
from app.services.file_manager import file_manager
from app.services.git_manager import git_manager

logger = logging.getLogger('ha_cursor_agent')
router = APIRouter()

# ==================== Helper Functions ====================

async def _remove_dashboard_from_config(filename: str) -> bool:
    """
    Remove dashboard from configuration.yaml
    
    Args:
        filename: Dashboard YAML filename
        
    Returns:
        True if successfully removed, False otherwise
    """
    try:
        config_path = "configuration.yaml"
        
        # Read current configuration as text
        config_content = await file_manager.read_file(config_path)
        
        # Extract dashboard key from filename
        dashboard_key = filename.replace('.yaml', '').replace('.yml', '')
        
        # Find and remove dashboard entry using regex
        import re
        
        # Pattern to match dashboard entry (with proper indentation)
        pattern = rf'    {dashboard_key}:\s*\n(?:      .*\n)+'
        
        if re.search(pattern, config_content):
            new_config_content = re.sub(pattern, '', config_content)
            
            # Write updated configuration
            await file_manager.write_file(config_path, new_config_content)
            logger.info(f"Dashboard '{dashboard_key}' removed from configuration.yaml")
            return True
        else:
            logger.info(f"Dashboard '{dashboard_key}' not found in configuration.yaml")
            return False
        
    except Exception as e:
        logger.error(f"Failed to remove dashboard from config: {e}")
        return False


async def _register_dashboard(filename: str, title: str, icon: str) -> bool:
    """
    Register dashboard in configuration.yaml
    
    Args:
        filename: Dashboard YAML filename
        title: Dashboard title
        icon: Dashboard icon
        
    Returns:
        True if successfully registered, False otherwise
    """
    try:
        config_path = "configuration.yaml"
        
        # Read current configuration as text (to preserve !include and other HA directives)
        config_content = await file_manager.read_file(config_path)
        
        # Extract dashboard key from filename (remove .yaml)
        dashboard_key = filename.replace('.yaml', '').replace('.yml', '')
        
        # Check if lovelace section exists
        if 'lovelace:' not in config_content:
            # Add lovelace section at the end
            lovelace_config = f"\n# Lovelace Dashboards\nlovelace:\n  dashboards:\n    {dashboard_key}:\n      mode: yaml\n      title: {title}\n      icon: {icon}\n      filename: {filename}\n      show_in_sidebar: true\n"
            new_config_content = config_content.rstrip() + "\n" + lovelace_config
        else:
            # Check if dashboards section exists
            if f'  dashboards:' not in config_content:
                # Add dashboards section under lovelace
                import re
                lovelace_match = re.search(r'(lovelace:)(\n)', config_content)
                if lovelace_match:
                    insert_pos = lovelace_match.end()
                    dashboard_config = f"  dashboards:\n    {dashboard_key}:\n      mode: yaml\n      title: {title}\n      icon: {icon}\n      filename: {filename}\n      show_in_sidebar: true\n"
                    new_config_content = config_content[:insert_pos] + dashboard_config + config_content[insert_pos:]
                else:
                    # Fallback: append at end
                    dashboard_config = f"\n  dashboards:\n    {dashboard_key}:\n      mode: yaml\n      title: {title}\n      icon: {icon}\n      filename: {filename}\n      show_in_sidebar: true\n"
                    new_config_content = config_content.rstrip() + "\n" + dashboard_config
            else:
                # Add dashboard to existing dashboards section
                # Find the dashboards: line and add after it
                import re
                dashboards_match = re.search(r'(  dashboards:)(\n)', config_content)
                if dashboards_match:
                    insert_pos = dashboards_match.end()
                    dashboard_config = f"    {dashboard_key}:\n      mode: yaml\n      title: {title}\n      icon: {icon}\n      filename: {filename}\n      show_in_sidebar: true\n"
                    new_config_content = config_content[:insert_pos] + dashboard_config + config_content[insert_pos:]
                else:
                    logger.warning("Could not find dashboards section to insert into")
                    return False
        
        # Write updated configuration
        await file_manager.write_file(config_path, new_config_content)
        
        logger.info(f"Dashboard '{dashboard_key}' registered in configuration.yaml")
        
        # Restart Home Assistant to apply configuration changes
        try:
            logger.info("Restarting Home Assistant to apply dashboard registration...")
            await ha_client.restart()
            logger.info("Home Assistant restart initiated")
        except Exception as restart_error:
            logger.warning(f"Dashboard registered but restart failed (manual restart needed): {restart_error}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to register dashboard: {e}")
        return False

# ==================== Request Models ====================

class GenerateDashboardRequest(BaseModel):
    """Request model for generating dashboard"""
    style: str = 'modern'  # modern, classic, minimal
    title: str = 'Home'
    include_views: Optional[List[str]] = None  # ['lights', 'climate', 'media']

class ApplyDashboardRequest(BaseModel):
    """Request model for applying dashboard"""
    dashboard_config: Dict[str, Any]
    create_backup: bool = True
    filename: str = "ai-dashboard.yaml"
    register_dashboard: bool = True  # Automatically register in configuration.yaml

# ==================== Endpoints ====================

@router.get("/analyze", response_model=Response, dependencies=[Depends(verify_token)])
async def analyze_entities():
    """
    Analyze entities and provide dashboard generation recommendations
    
    Returns:
        - Entity counts by domain and area
        - Recommended views
        - Grouping suggestions
    """
    try:
        logger.info("Analyzing entities for dashboard generation")
        
        # Get all entities from Home Assistant
        entities = await ha_client.get_states()
        
        if not entities or len(entities) == 0:
            return Response(
                success=False,
                message="No entities found in Home Assistant",
                data={}
            )
        
        # Analyze entities
        analysis = lovelace_generator.analyze_entities(entities)
        
        return Response(
            success=True,
            message=f"Analyzed {analysis['total_entities']} entities",
            data=analysis
        )
    
    except Exception as e:
        logger.error(f"Error analyzing entities: {e}")
        return Response(success=False, message=f"Failed to analyze entities: {str(e)}")


@router.post("/generate", response_model=Response, dependencies=[Depends(verify_token)])
async def generate_dashboard(request: GenerateDashboardRequest):
    """
    Generate complete Lovelace dashboard configuration
    
    Args:
        request: Dashboard generation parameters
        
    Returns:
        Generated dashboard configuration ready to apply
    """
    try:
        logger.info(f"Generating {request.style} dashboard: {request.title}")
        
        # Get all entities
        entities = await ha_client.get_states()
        
        if not entities or len(entities) == 0:
            return Response(
                success=False,
                message="No entities found to generate dashboard",
                data={}
            )
        
        # Generate dashboard
        dashboard_config = lovelace_generator.generate_dashboard(
            entities=entities,
            style=request.style
        )
        
        # Update title if provided
        if request.title:
            dashboard_config['title'] = request.title
        
        # Filter views if specified
        if request.include_views:
            dashboard_config['views'] = [
                view for view in dashboard_config['views']
                if view.get('path') in request.include_views or view.get('title') in request.include_views
            ]
        
        # Convert to YAML for preview
        dashboard_yaml = yaml.dump(dashboard_config, default_flow_style=False, allow_unicode=True)
        
        return Response(
            success=True,
            message=f"Dashboard generated with {len(dashboard_config['views'])} views",
            data={
                'config': dashboard_config,
                'yaml': dashboard_yaml,
                'views': [v['title'] for v in dashboard_config['views']],
                'total_views': len(dashboard_config['views'])
            }
        )
    
    except Exception as e:
        logger.error(f"Error generating dashboard: {e}")
        return Response(success=False, message=f"Failed to generate dashboard: {str(e)}")


@router.get("/preview", response_model=Response, dependencies=[Depends(verify_token)])
async def preview_current_dashboard():
    """
    Preview current Lovelace dashboard configuration
    
    Returns:
        Current dashboard configuration (if exists)
    """
    try:
        logger.info("Reading current dashboard configuration")
        
        # Try to read ui-lovelace.yaml
        lovelace_path = "ui-lovelace.yaml"
        
        try:
            content = await file_manager.read_file(lovelace_path)
            config = yaml.safe_load(content)
            
            return Response(
                success=True,
                message="Current dashboard configuration",
                data={
                    'path': lovelace_path,
                    'config': config,
                    'yaml': content
                }
            )
        except FileNotFoundError:
            return Response(
                success=True,
                message="No custom dashboard configured (using default UI mode)",
                data={
                    'path': lovelace_path,
                    'exists': False,
                    'note': 'Home Assistant is in storage mode or using default dashboard'
                }
            )
    
    except Exception as e:
        logger.error(f"Error previewing dashboard: {e}")
        return Response(success=False, message=f"Failed to preview dashboard: {str(e)}")


@router.post("/apply", response_model=Response, dependencies=[Depends(verify_token)])
async def apply_dashboard(request: ApplyDashboardRequest):
    """
    Apply generated dashboard configuration to Home Assistant
    
    Args:
        request: Dashboard configuration to apply
        
    **⚠️ Warning:** This will overwrite existing ui-lovelace.yaml
    **💾 Backup:** Creates Git backup by default
    """
    try:
        logger.info("Applying dashboard configuration")
        
        # Create backup if requested
        if request.create_backup:
            logger.info("Creating backup before applying dashboard")
            commit_msg = await git_manager.commit_changes("Before applying generated dashboard")
            logger.info(f"Backup created: {commit_msg}")
        
        # Convert config to YAML
        dashboard_yaml = yaml.dump(
            request.dashboard_config,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False
        )
        
        # Write dashboard file
        lovelace_path = request.filename
        await file_manager.write_file(lovelace_path, dashboard_yaml)
        
        logger.info(f"Dashboard written to {lovelace_path}")
        
        # Automatically register dashboard in configuration.yaml
        dashboard_registered = False
        if request.register_dashboard and lovelace_path != "ui-lovelace.yaml":
            try:
                dashboard_registered = await _register_dashboard(
                    filename=lovelace_path,
                    title=request.dashboard_config.get('title', 'AI Dashboard'),
                    icon='mdi:creation'
                )
                if dashboard_registered:
                    logger.info(f"Dashboard registered in configuration.yaml")
            except Exception as reg_error:
                logger.warning(f"Failed to auto-register dashboard: {reg_error}")
        
        # Commit changes
        if request.create_backup:
            commit_msg = f"Applied generated dashboard: {lovelace_path}"
            if dashboard_registered:
                commit_msg += " (auto-registered)"
            await git_manager.commit_changes(commit_msg)
        
        note = 'Dashboard created successfully!'
        if dashboard_registered:
            note = f'✅ Dashboard auto-registered and available in sidebar! Refresh your Home Assistant UI to see it.'
        elif lovelace_path == "ui-lovelace.yaml":
            note = 'Refresh your Home Assistant UI to see changes. You may need to enable YAML mode in Lovelace settings.'
        else:
            note = f'Dashboard file created. To use it, register in configuration.yaml or use UI to add dashboard with filename: {lovelace_path}'
        
        return Response(
            success=True,
            message=f"Dashboard applied successfully to {lovelace_path}",
            data={
                'path': lovelace_path,
                'views': len(request.dashboard_config.get('views', [])),
                'backup_created': request.create_backup,
                'dashboard_registered': dashboard_registered,
                'note': note
            }
        )
    
    except Exception as e:
        logger.error(f"Error applying dashboard: {e}")
        return Response(success=False, message=f"Failed to apply dashboard: {str(e)}")


@router.delete("/delete/{filename}", response_model=Response, dependencies=[Depends(verify_token)])
async def delete_dashboard(filename: str, remove_from_config: bool = True, create_backup: bool = True):
    """
    Delete a dashboard file and optionally remove from configuration.yaml
    
    Args:
        filename: Dashboard filename to delete (e.g., 'ai-dashboard.yaml')
        remove_from_config: Remove from configuration.yaml (default: true)
        create_backup: Create Git backup before deleting (default: true)
    
    **⚠️ Warning:** This will permanently delete the dashboard file
    **💾 Backup:** Creates Git backup by default
    """
    try:
        logger.info(f"Deleting dashboard: {filename}")
        
        # Create backup if requested
        if create_backup:
            logger.info("Creating backup before deleting dashboard")
            commit_msg = await git_manager.commit_changes(f"Before deleting dashboard: {filename}")
            logger.info(f"Backup created: {commit_msg}")
        
        # Check if file exists
        try:
            await file_manager.read_file(filename)
        except FileNotFoundError:
            return Response(
                success=True,
                message=f"Dashboard {filename} does not exist",
                data={'existed': False}
            )
        
        # Delete dashboard file
        import os
        from pathlib import Path
        file_path = Path('/config') / filename
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Dashboard file deleted: {filename}")
        
        # Remove from configuration.yaml if requested
        dashboard_removed = False
        if remove_from_config:
            try:
                dashboard_removed = await _remove_dashboard_from_config(filename)
                if dashboard_removed:
                    logger.info(f"Dashboard removed from configuration.yaml")
            except Exception as remove_error:
                logger.warning(f"Failed to remove dashboard from config: {remove_error}")
        
        # Commit changes
        if create_backup:
            commit_msg = f"Deleted dashboard: {filename}"
            if dashboard_removed:
                commit_msg += " (removed from config)"
            await git_manager.commit_changes(commit_msg)
        
        # Restart HA if config was modified
        if dashboard_removed:
            try:
                logger.info("Restarting Home Assistant to apply configuration changes...")
                await ha_client.restart()
                logger.info("Home Assistant restart initiated")
            except Exception as restart_error:
                logger.warning(f"Dashboard deleted but restart failed: {restart_error}")
        
        return Response(
            success=True,
            message=f"Dashboard {filename} deleted successfully",
            data={
                'filename': filename,
                'removed_from_config': dashboard_removed,
                'backup_created': create_backup,
                'restart_initiated': dashboard_removed
            }
        )
    
    except Exception as e:
        logger.error(f"Error deleting dashboard: {e}")
        return Response(success=False, message=f"Failed to delete dashboard: {str(e)}")


