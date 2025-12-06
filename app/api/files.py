"""Files API endpoints"""
from fastapi import APIRouter, HTTPException, Query
from typing import List
import logging

from app.models.schemas import FileContent, FileAppend, Response
from app.services.file_manager import file_manager
from app.services.git_manager import git_manager

router = APIRouter()
logger = logging.getLogger('ha_cursor_agent')

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
        result = await file_manager.write_file(
            file_data.path, 
            file_data.content, 
            file_data.create_backup,
            file_data.commit_message
        )
        
        # Commit is already done in file_manager.write_file() if auto_backup is enabled
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
    
    Example:
    ```json
    {
      "path": "automations.yaml",
      "content": "\\n- id: my_automation\\n  alias: Test\\n  ..."
    }
    ```
    """
    try:
        result = await file_manager.append_file(file_data.path, file_data.content, file_data.commit_message)
        
        # Auto-commit (use custom message if provided, otherwise default)
        if git_manager.enabled and git_manager.auto_backup:
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

