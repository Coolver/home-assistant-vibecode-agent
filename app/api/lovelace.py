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
        
        # Read current configuration
        config_content = await file_manager.read_file(config_path)
        config = yaml.safe_load(config_content) or {}
        
        # Get or create lovelace section
        if 'lovelace' not in config:
            config['lovelace'] = {}
        
        # Ensure dashboards section exists
        if 'dashboards' not in config['lovelace']:
            config['lovelace']['dashboards'] = {}
        
        # Extract dashboard key from filename (remove .yaml)
        dashboard_key = filename.replace('.yaml', '').replace('.yml', '')
        
        # Add dashboard configuration
        config['lovelace']['dashboards'][dashboard_key] = {
            'mode': 'yaml',
            'title': title,
            'icon': icon,
            'filename': filename,
            'show_in_sidebar': True
        }
        
        # Write updated configuration
        new_config_content = yaml.dump(config, default_flow_style=False, allow_unicode=True, sort_keys=False)
        await file_manager.write_file(config_path, new_config_content)
        
        logger.info(f"Dashboard '{dashboard_key}' registered in configuration.yaml")
        
        # Reload Lovelace configuration
        try:
            await ha_client.reload_config('lovelace')
            logger.info("Lovelace configuration reloaded")
        except Exception as reload_error:
            logger.warning(f"Dashboard registered but reload failed (manual restart may be needed): {reload_error}")
        
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
            commit_msg = git_manager.commit("Before applying generated dashboard")
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
            git_manager.commit(commit_msg)
        
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


