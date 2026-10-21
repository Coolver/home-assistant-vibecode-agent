"""File management service"""
import os
import aiofiles
import yaml
from pathlib import Path
from typing import List, Dict, Optional
import logging

logger = logging.getLogger('ha_cursor_agent')

_BLOCKED_FILENAMES = {"secrets.yaml", ".secrets.yaml"}
_BLOCKED_SUFFIXES = (".key", ".pem", ".crt")
_BLOCKED_STORAGE_EXACT = {"core.config_entries", "cloud", "application_credentials"}
_BLOCKED_STORAGE_PREFIXES = ("auth", "http")


class SensitivePathError(ValueError):
    """Raised when a file API call targets credentials or key material."""


def allow_sensitive_files() -> bool:
    return os.getenv("ALLOW_SENSITIVE_FILES", "false").strip().lower() in ("1", "true", "yes")


def is_sensitive_relative_path(relative_path: str) -> bool:
    """True for files that usually hold credentials.

    Dashboards and the rest of `.storage` (registries, lovelace) stay readable.
    `ALLOW_SENSITIVE_FILES=true` turns the block off.
    """
    if allow_sensitive_files():
        return False
    rel = relative_path.replace("\\", "/").strip("/")
    if not rel or rel == ".":
        return False
    parts = [part for part in rel.split("/") if part not in ("", ".")]
    collapsed = []
    for part in parts:
        if part == "..":
            if not collapsed:
                return False
            collapsed.pop()
        else:
            collapsed.append(part)
    if not collapsed:
        return False
    name = collapsed[-1]
    if name in _BLOCKED_FILENAMES or name.lower().endswith(_BLOCKED_SUFFIXES):
        return True
    if len(collapsed) >= 2 and collapsed[0] == ".storage":
        storage_name = collapsed[1]
        if storage_name in _BLOCKED_STORAGE_EXACT or storage_name.startswith(_BLOCKED_STORAGE_PREFIXES):
            return True
    return False


class FileManager:
    """Manages Home Assistant configuration files"""
    
    def __init__(self):
        self.config_path = Path(os.getenv('CONFIG_PATH', '/config'))
    
    def _get_full_path(self, relative_path: str) -> Path:
        """Get full path from relative path"""
        # Handle "/" as root config directory
        if relative_path == "/" or relative_path == "":
            return self.config_path
        
        # Remove leading slash if present (treat as relative)
        if relative_path.startswith("/"):
            relative_path = relative_path[1:]
        
        full_path = self.config_path / relative_path
        
        # Security: ensure path is within config directory
        if not str(full_path.resolve()).startswith(str(self.config_path.resolve())):
            raise ValueError(f"Path outside config directory: {relative_path}")

        try:
            rel = full_path.resolve().relative_to(self.config_path.resolve()).as_posix()
        except ValueError:
            raise ValueError(f"Path outside config directory: {relative_path}")
        if is_sensitive_relative_path(rel):
            logger.warning(f"Blocked sensitive file: {rel}")
            raise SensitivePathError(
                "This file is blocked because it can contain credentials "
                "(secrets, keys, or Home Assistant auth and config entries). "
                "Set the add-on option allow_sensitive_files to true to allow it."
            )
        
        return full_path
    
    async def list_files(self, directory: str = "", pattern: str = "*") -> List[Dict]:
        """List files in directory"""
        try:
            dir_path = self._get_full_path(directory)
            
            if not dir_path.exists():
                return []
            
            files = []
            for item in dir_path.rglob(pattern):
                if item.is_file():
                    rel_path = item.relative_to(self.config_path)
                    if is_sensitive_relative_path(rel_path.as_posix()):
                        continue
                    files.append({
                        "path": str(rel_path),
                        "name": item.name,
                        "size": item.stat().st_size,
                        "modified": item.stat().st_mtime,
                        "is_yaml": item.suffix in ['.yaml', '.yml']
                    })
            
            return sorted(files, key=lambda x: x['path'])
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            raise
    
    async def read_file(self, file_path: str, suppress_not_found_logging: bool = False) -> str:
        """Read file contents
        
        Args:
            file_path: Relative path to file
            suppress_not_found_logging: If True, FileNotFoundError will be logged as DEBUG instead of ERROR
        """
        try:
            full_path = self._get_full_path(file_path)
            
            if not full_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            async with aiofiles.open(full_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            logger.info(f"Read file: {file_path} ({len(content)} bytes)")
            return content
        except FileNotFoundError as e:
            if suppress_not_found_logging:
                logger.debug(f"File not found (expected): {file_path}")
            else:
                logger.error(f"Error reading file {file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raise
    
    async def write_file(self, file_path: str, content: str, create_backup: bool = True, commit_message: Optional[str] = None) -> Dict:
        """Write file contents
        
        Args:
            file_path: Relative path to file
            content: File content to write
            create_backup: Whether to create backup before writing
            commit_message: Optional custom commit message for Git backup
        """
        try:
            from app.services.git_manager import git_manager
            full_path = self._get_full_path(file_path)
            
            # Create backup if file exists (but skip if processing request - checkpoint already created)
            backup_path = None
            if create_backup and full_path.exists():
                backup_msg = f"Backup before writing {file_path}"
                backup_path = await git_manager.commit_changes(
                    backup_msg,
                    skip_if_processing=True
                )
            
            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            async with aiofiles.open(full_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            logger.info(f"Wrote file: {file_path} ({len(content)} bytes)")
            
            # Commit the write even if a checkpoint is open. The checkpoint
            # already stored the previous state; skipping here dropped the edit.
            commit_hash = None
            if git_manager.git_versioning_auto:
                commit_msg = commit_message or f"Write file: {file_path}"
                commit_hash = await git_manager.commit_changes(
                    commit_msg,
                    skip_if_processing=False
                )
            
            return {
                "success": True,
                "path": file_path,
                "size": len(content),
                "backup": backup_path,
                "commit": commit_hash
            }
        except Exception as e:
            logger.error(f"Error writing file {file_path}: {e}")
            raise
    
    async def append_file(self, file_path: str, content: str, commit_message: Optional[str] = None) -> Dict:
        """Append content to file
        
        Args:
            file_path: Relative path to file
            content: Content to append
            commit_message: Optional custom commit message for Git backup
        """
        try:
            full_path = self._get_full_path(file_path)
            
            # Create file if doesn't exist
            if not full_path.exists():
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.touch()
            
            # Read existing content
            async with aiofiles.open(full_path, 'r', encoding='utf-8') as f:
                existing = await f.read()
            
            # Append new content
            new_content = existing + '\n' + content if existing else content
            
            # Write back
            async with aiofiles.open(full_path, 'w', encoding='utf-8') as f:
                await f.write(new_content)
            
            logger.info(f"Appended to file: {file_path} ({len(content)} bytes)")
            
            return {
                "success": True,
                "path": file_path,
                "added_bytes": len(content),
                "total_size": len(new_content)
            }
        except Exception as e:
            logger.error(f"Error appending to file {file_path}: {e}")
            raise
    
    async def delete_file(self, file_path: str) -> Dict:
        """Delete file"""
        try:
            full_path = self._get_full_path(file_path)
            
            if not full_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Backup before delete (but skip if processing request - checkpoint already created)
            from app.services.git_manager import git_manager
            await git_manager.commit_changes(
                f"Backup before deleting {file_path}",
                skip_if_processing=True
            )
            
            full_path.unlink()

            commit_hash = None
            if git_manager.git_versioning_auto:
                commit_hash = await git_manager.commit_changes(
                    f"Delete file: {file_path}",
                    skip_if_processing=False,
                )
            
            logger.info(f"Deleted file: {file_path}")
            
            return {"success": True, "path": file_path, "commit": commit_hash}
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            raise
    
    async def parse_yaml(self, file_path: str) -> Dict:
        """Parse YAML file"""
        try:
            content = await self.read_file(file_path)
            data = yaml.safe_load(content)
            return data or {}
        except yaml.YAMLError as e:
            logger.error(f"YAML parse error in {file_path}: {e}")
            raise ValueError(f"Invalid YAML: {e}")
        except Exception as e:
            logger.error(f"Error parsing YAML {file_path}: {e}")
            raise

# Global instance
file_manager = FileManager()

