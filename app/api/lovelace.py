"""Lovelace Dashboard API Endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
import yaml

from app.models.schemas import Response
from app.auth import verify_token
from app.services.ha_client import ha_client
from app.services.file_manager import file_manager
from app.services.git_manager import git_manager
from app.utils.yaml_editor import YAMLEditor

logger = logging.getLogger('ha_cursor_agent')
router = APIRouter()

# ==================== Helper Functions ====================

def _validate_dashboard_filename(filename: str) -> tuple[bool, str]:
    """
    Validate dashboard filename meets HA requirements
    
    Args:
        filename: Dashboard filename (e.g., "heating-now.yaml")
        
    Returns:
        (is_valid, error_message)
    """
    # Remove .yaml/.yml extension for validation
    name_without_ext = filename.replace('.yaml', '').replace('.yml', '')
    
    # Check for hyphen
    if '-' not in name_without_ext:
        return False, f"Dashboard filename must contain a hyphen (-). Got: '{name_without_ext}'. Try: '{name_without_ext}-dashboard' or convert to kebab-case (e.g., 'my-dashboard')."
    
    # Check for invalid characters (spaces, special chars)
    if ' ' in name_without_ext:
        return False, f"Dashboard filename cannot contain spaces. Got: '{name_without_ext}'. Use hyphens instead (e.g., 'heating-now')."
    
    # Check for uppercase
    if name_without_ext != name_without_ext.lower():
        return False, f"Dashboard filename should be lowercase. Got: '{name_without_ext}'. Use lowercase: '{name_without_ext.lower()}'."
    
    return True, ""

async def _rollback_on_error(backup_commit: str, error_msg: str) -> None:
    """
    Automatically rollback changes if error occurred
    
    Args:
        backup_commit: Commit hash to rollback to
        error_msg: Error message that triggered rollback
    """
    try:
        logger.error(f"Error occurred: {error_msg}")
        logger.warning(f"Attempting automatic rollback to commit: {backup_commit}")
        
        # Use git_manager to rollback
        rollback_result = await git_manager.rollback(backup_commit)
        
        if rollback_result:
            logger.info(f"✅ Automatic rollback successful: {rollback_result}")
        else:
            logger.error("❌ Automatic rollback failed - manual intervention required")
            
    except Exception as rollback_error:
        logger.error(f"Failed to perform automatic rollback: {rollback_error}")


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
        
        # Use YAMLEditor utility to remove entry and clean up empty sections
        new_config_content, was_found = YAMLEditor.remove_yaml_entry(
            content=config_content,
            section='lovelace',
            key=dashboard_key
        )
        
        if was_found:
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
        commit_msg = f"Register dashboard in config: {dashboard_key}"
        await file_manager.write_file(config_path, new_config_content, commit_message=commit_msg)
        
        logger.info(f"Dashboard '{dashboard_key}' registered in configuration.yaml")
        
        # Reload core config to apply dashboard registration (safer than full restart)
        try:
            logger.info("Reloading core configuration to apply dashboard registration...")
            await ha_client.reload_component('core')
            logger.info("Core configuration reloaded")
        except Exception as reload_error:
            logger.warning(f"Dashboard registered but config reload failed (may need manual restart): {reload_error}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to register dashboard: {e}")
        return False

# ==================== Request Models ====================

class ApplyDashboardRequest(BaseModel):
    """Request model for applying dashboard"""
    dashboard_config: Dict[str, Any]
    create_backup: bool = True
    filename: str = "ai-dashboard.yaml"
    register_dashboard: bool = True  # Automatically register in configuration.yaml
    commit_message: Optional[str] = None  # Custom commit message for Git backup

# ==================== Endpoints ====================

@router.get("/analyze", response_model=Response, dependencies=[Depends(verify_token)])
async def analyze_entities():
    """
    Analyze entities and provide data for AI-driven dashboard generation
    
    Returns raw entity data for AI to analyze and generate dashboard in Cursor.
    AI will ask user questions and create custom dashboard based on requirements.
    
    Returns:
        - Complete entity list with attributes
        - Entity counts by domain
        - Areas (if configured)
    """
    try:
        logger.info("Fetching entities for AI dashboard generation")
        
        # Get all entities from Home Assistant
        entities = await ha_client.get_states()
        
        if not entities or len(entities) == 0:
            return Response(
                success=False,
                message="No entities found in Home Assistant",
                data={}
            )
        
        # Simple grouping by domain (no generation logic)
        from collections import defaultdict
        by_domain = defaultdict(list)
        
        for entity in entities:
            entity_id = entity.get('entity_id', '')
            domain = entity_id.split('.')[0] if '.' in entity_id else 'unknown'
            by_domain[domain].append({
                'entity_id': entity_id,
                'state': entity.get('state'),
                'attributes': entity.get('attributes', {}),
                'friendly_name': entity.get('attributes', {}).get('friendly_name', entity_id)
            })
        
        return Response(
            success=True,
            message=f"Found {len(entities)} entities for AI analysis",
            data={
                'total_entities': len(entities),
                'entities': entities,
                'by_domain': dict(by_domain),
                'domain_counts': {domain: len(ents) for domain, ents in by_domain.items()}
            }
        )
    
    except Exception as e:
        logger.error(f"Error fetching entities: {e}")
        return Response(success=False, message=f"Failed to fetch entities: {str(e)}")


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
        
        # Validate filename first
        is_valid, error_msg = _validate_dashboard_filename(request.filename)
        if not is_valid:
            logger.error(f"Invalid dashboard filename: {error_msg}")
            return Response(
                success=False,
                message=error_msg,
                data=None
            )
        
        # Check if dashboard already exists
        dashboard_key = request.filename.replace('.yaml', '').replace('.yml', '')
        config_content = await file_manager.read_file("configuration.yaml")
        
        if f'{dashboard_key}:' in config_content:
            logger.warning(f"Dashboard '{dashboard_key}' already exists in configuration.yaml")
            # Note: We allow overwriting, but log it
        
        # Create backup if requested
        if request.create_backup:
            logger.info("Creating backup before applying dashboard")
            backup_commit = await git_manager.commit_changes(
                "Before applying generated dashboard",
                skip_if_processing=True
            )
            logger.info(f"Backup created: {backup_commit}")
        
        # Convert config to YAML
        dashboard_yaml = yaml.dump(
            request.dashboard_config,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False
        )
        
        # Write dashboard file
        lovelace_path = request.filename
        commit_msg = request.commit_message or f"Apply dashboard: {lovelace_path}"
        await file_manager.write_file(lovelace_path, dashboard_yaml, commit_message=commit_msg)
        
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
        
        # Commit changes (if not already committed via write_file)
        # Note: write_file already commits if auto_backup is enabled, but we may need to commit config changes
        if request.create_backup and git_manager.enabled and git_manager.auto_backup:
            if dashboard_registered:
                # Config was changed, commit it separately
                config_commit_msg = request.commit_message or f"Register dashboard in config: {lovelace_path}"
                await git_manager.commit_changes(
                    config_commit_msg,
                skip_if_processing=True
            )
        
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
            commit_msg = await git_manager.commit_changes(
                f"Before deleting dashboard: {filename}",
                skip_if_processing=True
            )
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
            await git_manager.commit_changes(
                commit_msg,
                skip_if_processing=True
            )
        
        # Reload core config if config was modified (safer than full restart)
        if dashboard_removed:
            try:
                logger.info("Reloading core configuration to apply dashboard removal...")
                await ha_client.reload_component('core')
                logger.info("Core configuration reloaded")
            except Exception as reload_error:
                logger.warning(f"Dashboard deleted but config reload failed (may need manual restart): {reload_error}")
        
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


