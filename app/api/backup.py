"""Backup/Restore API endpoints"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional
import logging

from app.models.schemas import BackupRequest, RollbackRequest, Response
from app.services.git_manager import git_manager

router = APIRouter()
logger = logging.getLogger('ha_cursor_agent')

@router.post("/commit", response_model=Response)
async def create_backup(backup: BackupRequest):
    """
    Create backup (Git commit) of current state
    
    **Behavior:**
    - If `message` is provided: commits immediately with that message
    - If `message` is None and `git_versioning_auto=false`: 
      returns suggested commit message (does not commit)
      AI should show this to user, allow editing, then call again with message
    - If `message` is None and `git_versioning_auto=true`: 
      commits with auto-generated message
    
    **Example (with message):**
    ```json
    {
      "message": "Before installing climate control system"
    }
    ```
    
    **Example (without message, manual mode):**
    ```json
    {}
    ```
    Returns suggested message that user can edit and confirm.
    """
    try:
        if not git_manager.enabled:
            raise HTTPException(status_code=400, detail="Git versioning is not enabled")
        
        # If no message provided and auto mode is disabled, return suggested message
        if backup.message is None and not git_manager.git_versioning_auto:
            # Get pending changes
            pending_info = await git_manager.get_pending_changes()
            
            if not pending_info.get("has_changes"):
                return Response(
                    success=True,
                    message="No changes to commit",
                    data={"has_changes": False}
                )
            
            # Generate suggested commit message
            suggested_message = git_manager._generate_commit_message_from_changes(pending_info)
            
            return Response(
                success=False,  # Not committed yet, needs confirmation
                message="Commit message suggestion (needs user confirmation)",
                data={
                    "needs_confirmation": True,
                    "suggested_message": suggested_message,
                    "summary": pending_info.get("summary"),
                    "files_modified": pending_info.get("files_modified", []),
                    "files_added": pending_info.get("files_added", []),
                    "files_deleted": pending_info.get("files_deleted", []),
                    "diff": pending_info.get("diff", "")  # Optional, can be large
                }
            )
        
        # Commit with provided message (or auto-generated if auto mode is on)
        commit_hash = await git_manager.commit_changes(
            backup.message,
            force=True  # Force commit when explicitly called via API
        )
        
        if not commit_hash:
            return Response(
                success=True,
                message="No changes to commit",
                data=None
            )
        
        logger.info(f"Created backup: {commit_hash}")
        
        return Response(
            success=True,
            message=f"Backup created: {commit_hash}",
            data={"commit_hash": commit_hash}
        )
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_history(limit: int = 20):
    """
    Get backup history (Git commits)
    
    Returns list of commits with details
    """
    try:
        if not git_manager.enabled:
            raise HTTPException(status_code=400, detail="Git versioning is not enabled")
        
        history = await git_manager.get_history(limit)
        
        return {
            "success": True,
            "count": len(history),
            "commits": history
        }
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rollback/{commit_hash}", response_model=Response)
async def rollback_to_commit_path(commit_hash: str):
    """
    Rollback configuration to specific commit (path parameter version)
    
    **⚠️ WARNING: This will overwrite current configuration!**
    
    **Example:**
    - POST `/api/backup/rollback/a1b2c3d4`
    """
    try:
        if not git_manager.enabled:
            raise HTTPException(status_code=400, detail="Git versioning is not enabled")
        
        result = await git_manager.rollback(commit_hash)
        
        logger.warning(f"Rolled back to: {commit_hash}")
        
        return Response(
            success=True,
            message=f"Rolled back to commit: {commit_hash}",
            data=result
        )
    except Exception as e:
        logger.error(f"Failed to rollback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rollback", response_model=Response)
async def rollback_to_commit_body(rollback: RollbackRequest):
    """
    Rollback configuration to specific commit (body parameter version)
    
    **⚠️ WARNING: This will overwrite current configuration!**
    
    **Example:**
    ```json
    {
      "commit_hash": "a1b2c3d4"
    }
    ```
    """
    # Delegate to path parameter version
    return await rollback_to_commit_path(rollback.commit_hash)

@router.get("/diff")
async def get_diff(
    commit1: str = None,
    commit2: str = None
):
    """
    Get diff between commits or current changes
    
    **Examples:**
    - `/api/backup/diff` - Current uncommitted changes
    - `/api/backup/diff?commit1=a1b2c3d4` - Changes since commit
    - `/api/backup/diff?commit1=a1b2c3d4&commit2=e5f6g7h8` - Between two commits
    """
    try:
        if not git_manager.enabled:
            raise HTTPException(status_code=400, detail="Git versioning is not enabled")
        
        diff = await git_manager.get_diff(commit1, commit2)
        
        return {
            "success": True,
            "diff": diff
        }
    except Exception as e:
        logger.error(f"Failed to get diff: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/checkpoint")
async def create_checkpoint(user_request: str = Query(..., description="Description of the user request")):
    """
    Create checkpoint with tag at the start of user request processing
    
    This should be called at the beginning of each user request to:
    1. Save current state with a commit
    2. Create a tag with timestamp and user request description
    3. Disable auto-commits during request processing
    
    **Example:**
    - POST `/api/backup/checkpoint?user_request=Create nice_dark theme with dark blue header`
    """
    try:
        if not git_manager.enabled:
            raise HTTPException(status_code=400, detail="Git versioning is not enabled")
        
        if not user_request:
            user_request = "User request processing"
        
        result = await git_manager.create_checkpoint(user_request)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["message"])
        
        logger.info(f"Created checkpoint: {result['tag']} - {user_request}")
        
        return {
            "success": True,
            "message": result["message"],
            "commit_hash": result["commit_hash"],
            "tag": result["tag"],
            "timestamp": result["timestamp"]
        }
    except Exception as e:
        logger.error(f"Failed to create checkpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/checkpoint/end")
async def end_checkpoint():
    """
    End request processing - re-enable auto-commits
    
    This should be called at the end of user request processing
    """
    try:
        git_manager.end_request_processing()
        return {
            "success": True,
            "message": "Request processing ended - auto-commits re-enabled"
        }
    except Exception as e:
        logger.error(f"Failed to end checkpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cleanup")
async def cleanup_commits(delete_backup_branches: bool = True):
    """
    Manually cleanup old commits - keeps only last max_backups commits
    
    This function:
    1. Removes old commits (keeps only last max_backups commits, typically 50)
    2. Optionally deletes old backup_before_cleanup branches
    
    **Example:**
    - POST `/api/backup/cleanup?delete_backup_branches=true`
    """
    try:
        if not git_manager.enabled:
            raise HTTPException(status_code=400, detail="Git versioning is not enabled")
        
        result = await git_manager.cleanup_commits(delete_backup_branches=delete_backup_branches)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["message"])
        
        logger.info(f"Manual cleanup completed: {result['commits_before']} → {result['commits_after']} commits")
        
        return {
            "success": True,
            "message": result["message"],
            "commits_before": result["commits_before"],
            "commits_after": result["commits_after"],
            "backup_branches_deleted": result["backup_branches_deleted"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cleanup commits: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pending")
async def get_pending_changes():
    """
    Get information about uncommitted changes in shadow repository
    
    Useful when `git_versioning_auto=false` to see what changes are pending commit.
    
    Returns:
    - has_changes: bool
    - files_modified, files_added, files_deleted: lists
    - summary: counts
    - diff: full diff (can be large)
    """
    try:
        if not git_manager.enabled:
            raise HTTPException(status_code=400, detail="Git versioning is not enabled")
        
        pending_info = await git_manager.get_pending_changes()
        
        return {
            "success": True,
            "has_changes": pending_info.get("has_changes", False),
            "files_modified": pending_info.get("files_modified", []),
            "files_added": pending_info.get("files_added", []),
            "files_deleted": pending_info.get("files_deleted", []),
            "summary": pending_info.get("summary", {}),
            "diff": pending_info.get("diff", "")
        }
    except Exception as e:
        logger.error(f"Failed to get pending changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/restore", response_model=Response)
async def restore_files(
    commit_hash: Optional[str] = Body(None, description="Commit hash to restore from (default: HEAD)"),
    file_patterns: Optional[List[str]] = Body(None, description="File patterns to restore (e.g., ['*.yaml', 'configuration.yaml']). If None, restores all tracked files")
):
    """
    Restore files from a specific commit
    
    **⚠️ WARNING: This will overwrite current files!**
    
    **Examples:**
    ```json
    {
      "commit_hash": "482c5443",
      "file_patterns": ["configuration.yaml", "automations.yaml", "*.yaml"]
    }
    ```
    
    Or restore all files from HEAD:
    ```json
    {}
    ```
    """
    try:
        if not git_manager.enabled:
            raise HTTPException(status_code=400, detail="Git versioning is not enabled")
        
        result = await git_manager.restore_files_from_commit(commit_hash, file_patterns)
        
        logger.warning(f"Restored {result['count']} files from commit {result['commit']}")
        
        return Response(
            success=True,
            message=f"Restored {result['count']} files from commit {result['commit']}",
            data=result
        )
    except Exception as e:
        logger.error(f"Failed to restore files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

