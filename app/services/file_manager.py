"""File management service"""
import os
import aiofiles
import yaml
from pathlib import Path
from typing import List, Dict, Optional
import logging

logger = logging.getLogger('ha_cursor_agent')

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
    
    async def read_file(self, file_path: str) -> str:
        """Read file contents"""
        try:
            full_path = self._get_full_path(file_path)
            
            if not full_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            async with aiofiles.open(full_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            logger.info(f"Read file: {file_path} ({len(content)} bytes)")
            return content
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
            
            # Commit changes after writing (if git enabled and auto_backup is on)
            # Use custom commit_message if provided, otherwise default
            commit_hash = None
            if git_manager.enabled and git_manager.auto_backup:
                commit_msg = commit_message or f"Write file: {file_path}"
                commit_hash = await git_manager.commit_changes(
                    commit_msg,
                    skip_if_processing=True
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
            
            logger.info(f"Deleted file: {file_path}")
            
            return {"success": True, "path": file_path}
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

