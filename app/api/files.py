"""Files API endpoints"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Tuple
import logging
import os
import yaml

from app.models.schemas import FileContent, FileAppend, Response
from app.services.file_manager import file_manager
from app.services.git_manager import git_manager

router = APIRouter()
logger = logging.getLogger('ha_cursor_agent')


def _is_yaml_path(path: str) -> bool:
    """Return True if path looks like a YAML file."""
    lower = path.lower()
    return lower.endswith(".yaml") or lower.endswith(".yml")


def _validate_yaml_syntax(path: str, content: str) -> None:
    """
    Basic YAML syntax validation.

    Prevents writing obviously invalid YAML that would break Home Assistant.
    """
    if not _is_yaml_path(path):
        return

    try:
        # We don't care about structure here, only that YAML parses
        yaml.safe_load(content or "")  # empty file is valid YAML (None)
    except Exception as e:  # yaml.YAMLError and others
        logger.error(f"Invalid YAML when writing {path}: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid YAML in {path}: {e}")


def _validate_automations_structure(path: str, content: str) -> None:
    """
    Optional structural validation for automations.yaml.

    Current goal: detect duplicate automation ids, which can lead to
    confusing behaviour in Home Assistant. We keep the validation minimal
    to avoid being too opinionated about future format changes:

    - Only runs for files named 'automations.yaml' (any directory).
    - Only checks when top-level YAML is a list.
    - Only looks at 'id' fields; if there are duplicates, we reject the write.
    """
    # Only apply to automations.yaml files
    if os.path.basename(path) != "automations.yaml":
        return

    try:
        data = yaml.safe_load(content or "")
    except Exception as e:
        # Syntax errors are handled separately in _validate_yaml_syntax
        logger.debug(f"Skipping automations structure check for {path} due to YAML error: {e}")
        return

    if not isinstance(data, list):
        # Format might change in the future; don't enforce strict structure here
        logger.debug(
            f"Automations file {path} is not a list at top level; "
            f"skipping duplicate id validation to avoid being too strict."
        )
        return

    seen_ids = set()
    duplicate_ids = set()

    for item in data:
        if not isinstance(item, dict):
            continue
        automation_id = item.get("id")
        if not automation_id:
            continue
        if automation_id in seen_ids:
            duplicate_ids.add(automation_id)
        else:
            seen_ids.add(automation_id)

    if duplicate_ids:
        ids_str = ", ".join(sorted(str(i) for i in duplicate_ids))
        logger.error(f"Duplicate automation ids detected in {path}: {ids_str}")
        raise HTTPException(
            status_code=400,
            detail=(
                f"Duplicate automation id values detected in {path}: {ids_str}. "
                "Each automation id must be unique. Please remove or merge duplicates."
            ),
        )

@router.get("/list")
async def list_files(
    directory: str = Query("", description="Directory to list (relative to /config)"),
    pattern: str = Query("*.yaml", description="File pattern (e.g., '*.yaml', '*.py')")
):
    """
    List files in directory
    
    Examples:
    - `/api/files/list` - List all YAML files
    - `/api/files/list?directory=custom_components` - List files in custom_components
    - `/api/files/list?pattern=*.py` - List all Python files
    """
    try:
        files = await file_manager.list_files(directory, pattern)
        logger.info(f"Listed {len(files)} files in '{directory}' with pattern '{pattern}'")
        return {
            "success": True,
            "count": len(files),
            "files": files
        }
    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/read")
async def read_file(path: str = Query(..., description="File path relative to /config")):
    """
    Read file contents
    
    Example:
    - `/api/files/read?path=configuration.yaml`
    - `/api/files/read?path=automations.yaml`
    """
    try:
        content = await file_manager.read_file(path)
        return {
            "success": True,
            "path": path,
            "content": content,
            "size": len(content)
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    except Exception as e:
        logger.error(f"Failed to read file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/write", response_model=Response)
async def write_file(file_data: FileContent):
    """
    Write or create file
    
    **Automatically creates backup if file exists!**
    **Note:** Does NOT auto-reload. Use /api/system/reload after changes.
    
    For YAML files (e.g. `automations.yaml`, `scripts.yaml`), this endpoint performs:
    - Basic YAML syntax validation (rejects invalid YAML before writing).
    - Additional safety checks for known files like `automations.yaml`
      (e.g. detect duplicate automation ids).
    
    Example request:
    ```json
    {
      "path": "scripts.yaml",
      "content": "my_script:\\n  alias: Test\\n  sequence: []",
      "create_backup": true
    }
    ```
    """
    try:
        # YAML safety checks (syntax + known domain-specific validations)
        _validate_yaml_syntax(file_data.path, file_data.content)
        _validate_automations_structure(file_data.path, file_data.content)

        result = await file_manager.write_file(
            file_data.path,
            file_data.content,
            file_data.create_backup,
            file_data.commit_message
        )
        
        # Commit is already done in file_manager.write_file() if git_versioning_auto is enabled
        # Just rename the key for consistency
        if result.get('commit'):
            result['git_commit'] = result['commit']
        
        logger.info(f"File written: {file_data.path}. Remember to reload components if needed!")
        
        return Response(success=True, message=f"File written: {file_data.path}", data=result)
    except Exception as e:
        logger.error(f"Failed to write file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/append", response_model=Response)
async def append_to_file(file_data: FileAppend):
    """
    Append content to file
    
    **Note:** Does NOT auto-reload. Use /api/system/reload after changes.
    
    For YAML files, the agent will validate the *resulting* content after append:
    - YAML syntax must be valid.
    - For `automations.yaml`, duplicate `id` values are rejected.
    
    Example:
    ```json
    {
      "path": "automations.yaml",
      "content": "\\n- id: my_automation\\n  alias: Test\\n  ..."
    }
    ```
    """
    try:
        # For YAML, validate the combined content (existing + appended) before writing
        if _is_yaml_path(file_data.path):
            try:
                existing = await file_manager.read_file(file_data.path, suppress_not_found_logging=True)
            except FileNotFoundError:
                existing = ""
            new_content = (existing + "\n" + file_data.content) if existing else file_data.content
            _validate_yaml_syntax(file_data.path, new_content)
            _validate_automations_structure(file_data.path, new_content)

        result = await file_manager.append_file(file_data.path, file_data.content, file_data.commit_message)
        
        # Auto-commit (use custom message if provided, otherwise default)
        if git_manager.git_versioning_auto:
            commit_msg = file_data.commit_message or f"Append to file: {file_data.path}"
            commit = await git_manager.commit_changes(
                commit_msg,
                skip_if_processing=True
            )
            if commit:
                result['git_commit'] = commit
        
        logger.info(f"Content appended to: {file_data.path}. Remember to reload components if needed!")
        
        return Response(success=True, message=f"Content appended to: {file_data.path}", data=result)
    except Exception as e:
        logger.error(f"Failed to append to file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete")
async def delete_file(path: str = Query(..., description="File path to delete")):
    """
    Delete file
    
    **Automatically creates backup before deletion!**
    """
    try:
        result = await file_manager.delete_file(path)
        return Response(success=True, message=f"File deleted: {path}", data=result)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    except Exception as e:
        logger.error(f"Failed to delete file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/parse_yaml")
async def parse_yaml(path: str = Query(..., description="YAML file path")):
    """
    Parse YAML file and return as JSON
    
    Useful for reading and understanding YAML structure
    """
    try:
        data = await file_manager.parse_yaml(path)
        return {
            "success": True,
            "path": path,
            "data": data
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    except Exception as e:
        logger.error(f"Failed to parse YAML: {e}")
        raise HTTPException(status_code=500, detail=str(e))

