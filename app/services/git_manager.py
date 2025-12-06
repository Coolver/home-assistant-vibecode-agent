"""Git versioning manager"""
import os
import git
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger('ha_cursor_agent')

class GitManager:
    """Manages Git versioning for config files"""
    
    def __init__(self):
        self.config_path = Path(os.getenv('CONFIG_PATH', '/config'))
        self.enabled = os.getenv('ENABLE_GIT', 'false').lower() == 'true'
        self.auto_backup = os.getenv('AUTO_BACKUP', 'true').lower() == 'true'
        self.max_backups = int(os.getenv('MAX_BACKUPS', '50'))
        self.repo = None
        self.processing_request = False  # Flag to disable auto-commits during request processing
        
        if self.enabled:
            self._init_repo()
    
    def _init_repo(self):
        """Initialize Git repository"""
        try:
            if (self.config_path / '.git').exists():
                self.repo = git.Repo(self.config_path)
                logger.info("Git repository loaded")
                # Ensure .gitignore exists even for existing repos
                self._create_gitignore()
            else:
                self.repo = git.Repo.init(self.config_path)
                self.repo.config_writer().set_value("user", "name", "HA Cursor Agent").release()
                self.repo.config_writer().set_value("user", "email", "agent@homeassistant.local").release()
                # Create .gitignore to exclude large files
                self._create_gitignore()
                logger.info("Git repository initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Git: {e}")
            self.enabled = False
    
    def _create_gitignore(self):
        """Create .gitignore file in config directory to exclude large files"""
        gitignore_path = self.config_path / '.gitignore'
        gitignore_content = """# Home Assistant Git Backup - Exclude Large Files
# This file is automatically created by HA Vibecode Agent

# Database files (can be several GB)
*.db
*.db-shm
*.db-wal
*.db-journal
*.sqlite
*.sqlite3

# Log files
*.log
home-assistant.log
*.log.*

# Media and static files
/www/
/media/
/storage/
/tmp/

# Home Assistant internal directories
/.storage/
/.cloud/
/.homeassistant/
/home-assistant_v2.db*

# Python cache
__pycache__/
*.py[cod]
*.pyc
*.pyo

# Node.js
node_modules/
npm-debug.log*

# Temporary files
*.tmp
*.temp
*.swp
*.swo
*~

# OS files
.DS_Store
Thumbs.db
desktop.ini

# IDE files
.vscode/
.idea/
*.code-workspace

# Backup files
*.bak
*.backup
*.old

# Secrets and tokens (should not be in Git anyway)
secrets.yaml
.secrets.yaml
*.pem
*.key
*.crt
"""
        try:
            # Only create if it doesn't exist, or update if it's missing critical patterns
            was_new = not gitignore_path.exists()
            if not gitignore_path.exists():
                gitignore_path.write_text(gitignore_content)
                logger.info("Created .gitignore file in config directory")
            else:
                # Check if it has our marker comment
                existing_content = gitignore_path.read_text()
                if "# Home Assistant Git Backup" not in existing_content:
                    # Append our patterns (user might have custom .gitignore)
                    gitignore_path.write_text(existing_content + "\n\n# HA Vibecode Agent patterns\n" + gitignore_content)
                    logger.info("Updated .gitignore file with agent patterns")
                    was_new = True  # Treat as new if we just added patterns
            
            # Remove already tracked files that should be ignored
            # This is important for existing repos where large files were already committed
            # Always try to clean up, not just when .gitignore is new
            if self.repo is not None:
                self._remove_tracked_ignored_files()
        except Exception as e:
            logger.warning(f"Failed to create/update .gitignore: {e}")
    
    def _remove_tracked_ignored_files(self):
        """Remove already tracked files from Git index that should be ignored"""
        try:
            if self.repo is None:
                return
            
            # Get all tracked files
            tracked_files = [item.path for item in self.repo.index.entries.values()]
            
            # Patterns to match (files that should be ignored)
            import fnmatch
            patterns_to_ignore = [
                '*.db',
                '*.db-shm',
                '*.db-wal',
                '*.db-journal',
                '*.sqlite',
                '*.sqlite3',
                '.storage/*',
                '.cloud/*',
                '.homeassistant/*',
                'home-assistant_v2.db*',
                'www/*',
                'media/*',
                'storage/*',
                'tmp/*',
            ]
            
            # Find files that match ignore patterns
            files_to_remove = []
            for file_path in tracked_files:
                for pattern in patterns_to_ignore:
                    # Remove leading slash for matching
                    normalized_pattern = pattern.lstrip('/')
                    # Check if file matches pattern
                    if fnmatch.fnmatch(file_path, normalized_pattern):
                        files_to_remove.append(file_path)
                        break
                    # Check if file is in a directory that matches pattern (e.g., .storage/* matches .storage/file)
                    elif normalized_pattern.endswith('/*') and file_path.startswith(normalized_pattern.rstrip('/*') + '/'):
                        files_to_remove.append(file_path)
                        break
                    # Check for wildcard patterns like home-assistant_v2.db*
                    elif '*' in normalized_pattern and fnmatch.fnmatch(file_path, normalized_pattern):
                        files_to_remove.append(file_path)
                        break
            
            # Remove files from Git index (but keep on disk)
            removed_count = 0
            for file_path in files_to_remove:
                try:
                    self.repo.git.rm('--cached', '--ignore-unmatch', file_path)
                    removed_count += 1
                    logger.debug(f"Removed {file_path} from Git tracking")
                except Exception as e:
                    logger.debug(f"Failed to remove {file_path}: {e}")
            
            if removed_count > 0:
                logger.info(f"Removed {removed_count} ignored files from Git tracking (files kept on disk)")
        except Exception as e:
            logger.warning(f"Failed to remove tracked ignored files: {e}")
    
    def _add_config_files_only(self):
        """Add configuration files to Git, excluding large files via .gitignore"""
        try:
            # Use git add -A which respects .gitignore
            # Since we create .gitignore with proper exclusions, this is safe
            # .gitignore excludes: *.db, *.log, /www/, /media/, /.storage/, etc.
            self.repo.git.add(A=True)
            
            # Note: Git automatically respects .gitignore, so large files
            # (databases, logs, media) won't be added even with -A flag
                    
        except Exception as e:
            logger.error(f"Failed to add config files: {e}")
            raise
    
    async def commit_changes(self, message: str = None, skip_if_processing: bool = False) -> Optional[str]:
        """Commit current changes"""
        if not self.enabled or not self.repo:
            return None
        
        # Skip auto-commits if processing a request (unless explicitly requested)
        if skip_if_processing and self.processing_request:
            logger.debug("Skipping auto-commit - request processing in progress")
            return None
        
        try:
            # Check if there are changes (only for tracked files and config files)
            if not self.repo.is_dirty(untracked_files=True):
                logger.debug("No changes to commit")
                return None
            
            # Add only configuration files, not all files
            # This respects .gitignore and only adds config files
            self._add_config_files_only()
            
            # Create commit message
            if not message:
                message = f"Auto-commit by HA Cursor Agent at {datetime.now().isoformat()}"
            
            # Commit
            commit = self.repo.index.commit(message)
            commit_hash = commit.hexsha[:8]
            
            logger.info(f"Committed changes: {commit_hash} - {message}")
            
            # Cleanup old commits if needed
            # When we reach max_backups (50), we keep only 30 commits and continue
            # Count commits in current branch only (not all commits in repo)
            try:
                # Use git rev-list to count only commits reachable from HEAD
                # This excludes dangling objects that may still exist after cleanup
                # Use --no-merges to avoid counting merge commits separately
                rev_list_output = self.repo.git.rev_list('--count', '--no-merges', 'HEAD')
                commit_count = int(rev_list_output.strip())
                logger.info(f"Commit count via rev-list: {commit_count}")
            except Exception as e:
                # Fallback: count commits using iter_commits with HEAD
                logger.warning(f"git rev-list failed, using iter_commits fallback: {e}")
                commit_count = len(list(self.repo.iter_commits('HEAD', max_count=1000)))
            
            if commit_count >= self.max_backups:
                # At max_backups, cleanup to keep only 30 commits
                await self._cleanup_old_commits()
            
            return commit_hash
        except Exception as e:
            logger.error(f"Failed to commit changes: {e}")
            return None
    
    async def create_checkpoint(self, user_request: str) -> Dict:
        """Create checkpoint with tag at the start of user request processing"""
        if not self.enabled or not self.repo:
            return {
                "success": False,
                "message": "Git versioning not enabled",
                "commit_hash": None,
                "tag": None
            }
        
        try:
            # Commit current state first (if there are changes)
            commit_hash = await self.commit_changes(
                f"Checkpoint before: {user_request}",
                skip_if_processing=False
            )
            
            # If no changes, get current HEAD
            if not commit_hash:
                try:
                    commit_hash = self.repo.head.commit.hexsha[:8]
                except:
                    commit_hash = None
            
            # Create tag with timestamp and description
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            tag_name = f"checkpoint_{timestamp}"
            tag_message = f"Checkpoint before: {user_request}"
            
            # Create tag
            if commit_hash:
                try:
                    # Use HEAD for tag creation (commit_hash is already committed)
                    tag = self.repo.create_tag(
                        tag_name,
                        ref="HEAD",
                        message=tag_message
                    )
                    logger.info(f"Created checkpoint tag: {tag_name} - {tag_message}")
                except Exception as e:
                    logger.warning(f"Failed to create tag (may already exist): {e}")
                    tag = None
            else:
                try:
                    # Try to create tag on HEAD even if no new commit
                    tag = self.repo.create_tag(
                        tag_name,
                        ref="HEAD",
                        message=tag_message
                    )
                    logger.info(f"Created checkpoint tag: {tag_name} - {tag_message}")
                except Exception as e:
                    logger.warning(f"Failed to create tag: {e}")
                    tag = None
            
            # Set flag to disable auto-commits during request processing
            self.processing_request = True
            
            return {
                "success": True,
                "message": f"Checkpoint created: {tag_name}",
                "commit_hash": commit_hash,
                "tag": tag_name,
                "timestamp": timestamp
            }
        except Exception as e:
            logger.error(f"Failed to create checkpoint: {e}")
            return {
                "success": False,
                "message": f"Failed to create checkpoint: {e}",
                "commit_hash": None,
                "tag": None
            }
    
    def end_request_processing(self):
        """End request processing - re-enable auto-commits"""
        self.processing_request = False
        logger.debug("Request processing ended - auto-commits re-enabled")
    
    async def _cleanup_old_commits(self):
        """Remove old commits to save space - keeps only 30 commits when reaching 50
        
        This is called automatically when commits reach max_backups (50).
        We keep only 30 commits to have buffer before next cleanup.
        For manual cleanup with backup branch deletion, use cleanup_commits().
        
        This method safely removes old commits while preserving:
        - All current files on disk (unchanged)
        - Last 30 commits (history)
        - Ability to rollback to any of the last 30 versions
        """
        try:
            # Count commits in current branch only (not all commits in repo)
            try:
                # Use git rev-list to count only commits reachable from HEAD
                # This excludes dangling objects that may still exist after cleanup
                # Use --no-merges to avoid counting merge commits separately
                rev_list_output = self.repo.git.rev_list('--count', '--no-merges', 'HEAD')
                total_commits = int(rev_list_output.strip())
                logger.info(f"Total commits via rev-list: {total_commits}")
            except Exception as e:
                # Fallback: count commits using iter_commits with HEAD
                logger.warning(f"git rev-list failed, using iter_commits fallback: {e}")
                total_commits = len(list(self.repo.iter_commits('HEAD', max_count=1000)))
            
            # Keep 30 commits when we reach 50 (max_backups)
            commits_to_keep_count = 30
            
            if total_commits < self.max_backups:
                return  # No cleanup needed yet
            
            logger.info(f"Repository has {total_commits} commits, reached max ({self.max_backups}). Starting automatic cleanup to keep {commits_to_keep_count} commits...")
            
            # Get the commits we want to keep (last 30)
            commits_to_keep = list(self.repo.iter_commits(max_count=commits_to_keep_count))
            if not commits_to_keep:
                return
            
            # Verify we got the right number of commits
            if len(commits_to_keep) != commits_to_keep_count:
                logger.warning(f"Expected {commits_to_keep_count} commits to keep, but got {len(commits_to_keep)}. Using what we have.")
            
            logger.info(f"Keeping {len(commits_to_keep)} commits: from {commits_to_keep[-1].hexsha[:8]} (oldest) to {commits_to_keep[0].hexsha[:8]} (newest)")
            
            try:
                # Save current branch name
                current_branch = self.repo.active_branch.name
                
                # Ensure all current changes are committed before cleanup
                if self.repo.is_dirty(untracked_files=True):
                    await self.commit_changes("Pre-cleanup commit: save current state")
                
                # Get the oldest commit we want to keep (last in list is oldest)
                oldest_keep_commit = commits_to_keep[-1]
                newest_keep_commit = commits_to_keep[0]  # HEAD
                
                # Strategy: Create a new orphan branch and cherry-pick commits we want to keep
                # This is simpler and more reliable than rebase --onto
                
                # Save current HEAD
                current_head_sha = self.repo.head.commit.hexsha
                
                # Create a temporary orphan branch (no parent, clean history)
                temp_branch = f"temp_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self.repo.git.checkout('--orphan', temp_branch)
                
                # Reset to oldest commit we want to keep (this gives us that commit's tree)
                self.repo.git.reset('--hard', oldest_keep_commit.hexsha)
                
                # Now cherry-pick all commits from oldest+1 to newest (in order)
                # commits_to_keep is ordered newest to oldest, so we reverse it
                commits_to_cherry_pick = list(reversed(commits_to_keep[:-1]))  # All except oldest
                logger.info(f"Cherry-picking {len(commits_to_cherry_pick)} commits (excluding oldest)")
                
                cherry_picked_count = 0
                for commit in commits_to_cherry_pick:
                    try:
                        # Cherry-pick with --no-commit to avoid creating merge commits
                        self.repo.git.cherry_pick('--no-commit', commit.hexsha)
                        # Commit with original message
                        if self.repo.is_dirty():
                            self.repo.index.commit(commit.message.strip())
                            cherry_picked_count += 1
                    except Exception as cp_error:
                        # If cherry-pick fails, abort and skip this commit
                        logger.warning(f"Cherry-pick failed for {commit.hexsha[:8]}: {cp_error}")
                        try:
                            self.repo.git.cherry_pick('--abort')
                        except:
                            pass
                        # Continue with next commit
                
                logger.info(f"Cherry-picked {cherry_picked_count} commits. Total should be: 1 (oldest) + {cherry_picked_count} (cherry-picked) = {1 + cherry_picked_count}")
                
                # Replace the original branch with the cleaned branch
                self.repo.git.branch('-D', current_branch)
                self.repo.git.branch('-m', current_branch)
                self.repo.git.checkout(current_branch)
                
                # We know we created exactly commits_to_keep_count commits:
                # 1 (oldest commit via reset) + (commits_to_keep_count - 1) (cherry-picked) = commits_to_keep_count
                # Use this expected count instead of trying to count (which may include old dangling commits)
                commits_after = commits_to_keep_count
                
                logger.info(f"Created {commits_after} commits in cleaned branch (1 oldest + {commits_to_keep_count - 1} cherry-picked)")
                
                # Use simpler gc without aggressive pruning to avoid OOM
                # This removes dangling objects (old unreachable commits)
                try:
                    self.repo.git.gc('--prune=now')
                except Exception as gc_error:
                    # If gc fails, try even simpler approach
                    logger.warning(f"git gc failed: {gc_error}. Trying simpler cleanup...")
                    self.repo.git.prune('--expire=now')
                
                # Don't verify count after gc - rev-list may still count old dangling commits
                # We know we created exactly commits_after commits, so use that
                logger.info(f"✅ Automatic cleanup complete: {total_commits} → {commits_after} commits. Removed {total_commits - commits_after} old commits.")
                
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup commits: {cleanup_error}")
                # Try to restore to original branch if cleanup failed
                try:
                    self.repo.git.checkout(current_branch)
                except:
                    pass
                # Don't fail the whole operation if cleanup fails - repository is still usable
                
        except Exception as e:
            logger.error(f"Failed to cleanup commits: {e}")
    
    async def cleanup_commits(self, delete_backup_branches: bool = True) -> Dict:
        """Manually cleanup old commits - keeps only last max_backups commits
        
        This is a manual cleanup function that:
        1. Removes old commits (keeps only last max_backups)
        2. Optionally deletes old backup_before_cleanup branches
        
        Returns:
            Dict with cleanup results
        """
        if not self.enabled or not self.repo:
            return {
                "success": False,
                "message": "Git versioning not enabled",
                "commits_before": 0,
                "commits_after": 0,
                "backup_branches_deleted": 0
            }
        
        try:
            commits = list(self.repo.iter_commits())
            total_commits = len(commits)
            
            if total_commits <= self.max_backups:
                # Still clean up backup branches if requested
                deleted_branches = 0
                if delete_backup_branches:
                    deleted_branches = self._delete_backup_branches()
                
                return {
                    "success": True,
                    "message": f"No cleanup needed - repository has {total_commits} commits (max: {self.max_backups})",
                    "commits_before": total_commits,
                    "commits_after": total_commits,
                    "backup_branches_deleted": deleted_branches
                }
            
            logger.info(f"Manual cleanup: Repository has {total_commits} commits, max is {self.max_backups}. Starting cleanup...")
            
            # Get the commits we want to keep (last max_backups)
            commits_to_keep = list(self.repo.iter_commits(max_count=self.max_backups))
            if not commits_to_keep:
                return {
                    "success": False,
                    "message": "No commits to keep",
                    "commits_before": total_commits,
                    "commits_after": total_commits,
                    "backup_branches_deleted": 0
                }
            
            # Save current branch name
            current_branch = self.repo.active_branch.name
            
            # Ensure all current changes are committed before cleanup
            if self.repo.is_dirty(untracked_files=True):
                await self.commit_changes("Pre-cleanup commit: save current state")
            
            # Get the oldest commit we want to keep (last in list is oldest)
            oldest_keep_commit = commits_to_keep[-1]
            newest_keep_commit = commits_to_keep[0]  # HEAD
            
            # Strategy: Create a new orphan branch and cherry-pick commits we want to keep
            # This is simpler and more reliable than rebase --onto
            
            # Save current HEAD
            current_head_sha = self.repo.head.commit.hexsha
            
            # Create a temporary orphan branch (no parent, clean history)
            temp_branch = f"temp_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.repo.git.checkout('--orphan', temp_branch)
            
            # Reset to oldest commit we want to keep (this gives us that commit's tree)
            self.repo.git.reset('--hard', oldest_keep_commit.hexsha)
            
            # Now cherry-pick all commits from oldest+1 to newest (in order)
            # commits_to_keep is ordered newest to oldest, so we reverse it
            commits_to_cherry_pick = list(reversed(commits_to_keep[:-1]))  # All except oldest
            
            for commit in commits_to_cherry_pick:
                try:
                    # Cherry-pick with --no-commit to avoid creating merge commits
                    self.repo.git.cherry_pick('--no-commit', commit.hexsha)
                    # Commit with original message
                    if self.repo.is_dirty():
                        self.repo.index.commit(commit.message.strip())
                except Exception as cp_error:
                    # If cherry-pick fails, abort and skip this commit
                    logger.warning(f"Cherry-pick failed for {commit.hexsha[:8]}: {cp_error}")
                    try:
                        self.repo.git.cherry_pick('--abort')
                    except:
                        pass
                    # Continue with next commit
            
            # Replace the original branch with the cleaned branch
            self.repo.git.branch('-D', current_branch)
            self.repo.git.branch('-m', current_branch)
            self.repo.git.checkout(current_branch)
            
            # Clean up backup branches if requested
            deleted_branches = 0
            if delete_backup_branches:
                deleted_branches = self._delete_backup_branches()
            
            # Use simpler gc without aggressive pruning to avoid OOM
            # This removes dangling objects (old unreachable commits)
            try:
                self.repo.git.gc('--prune=now')
            except Exception as gc_error:
                logger.warning(f"git gc failed: {gc_error}. Trying simpler cleanup...")
                self.repo.git.prune('--expire=now')
            
            # Count commits in current branch only (not all commits in repo)
            commits_after = len(list(self.repo.iter_commits(current_branch)))
            
            logger.info(f"✅ Manual cleanup complete: {total_commits} → {commits_after} commits. Removed {total_commits - commits_after} old commits.")
            if delete_backup_branches and deleted_branches > 0:
                logger.info(f"✅ Deleted {deleted_branches} old backup branches.")
            
            return {
                "success": True,
                "message": f"Cleanup complete: {total_commits} → {commits_after} commits",
                "commits_before": total_commits,
                "commits_after": commits_after,
                "backup_branches_deleted": deleted_branches
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup commits: {e}")
            return {
                "success": False,
                "message": f"Cleanup failed: {e}",
                "commits_before": total_commits if 'total_commits' in locals() else 0,
                "commits_after": 0,
                "backup_branches_deleted": 0
            }
    
    def _delete_backup_branches(self) -> int:
        """Delete all backup_before_cleanup branches"""
        try:
            backup_branches = [
                branch for branch in self.repo.branches
                if branch.name.startswith('backup_before_cleanup_')
            ]
            
            deleted_count = 0
            for branch in backup_branches:
                try:
                    self.repo.git.branch('-D', branch.name)
                    deleted_count += 1
                    logger.debug(f"Deleted backup branch: {branch.name}")
                except Exception as e:
                    logger.warning(f"Failed to delete backup branch {branch.name}: {e}")
            
            return deleted_count
        except Exception as e:
            logger.warning(f"Failed to delete backup branches: {e}")
            return 0
    
    async def get_history(self, limit: int = 20) -> List[Dict]:
        """Get commit history"""
        if not self.enabled or not self.repo:
            return []
        
        try:
            commits = []
            for commit in self.repo.iter_commits(max_count=limit):
                commits.append({
                    "hash": commit.hexsha[:8],
                    "message": commit.message.strip(),
                    "author": str(commit.author),
                    "date": datetime.fromtimestamp(commit.committed_date).isoformat(),
                    "files_changed": len(commit.stats.files)
                })
            return commits
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            return []
    
    async def rollback(self, commit_hash: str) -> Dict:
        """Rollback to specific commit"""
        if not self.enabled or not self.repo:
            raise Exception("Git versioning not enabled")
        
        try:
            # Commit current state before rollback
            await self.commit_changes(f"Before rollback to {commit_hash}")
            
            # Reset to commit
            self.repo.git.reset('--hard', commit_hash)
            
            logger.info(f"Rolled back to commit: {commit_hash}")
            
            return {
                "success": True,
                "commit": commit_hash,
                "message": f"Rolled back to {commit_hash}"
            }
        except Exception as e:
            logger.error(f"Failed to rollback: {e}")
            raise Exception(f"Rollback failed: {e}")
    
    async def get_diff(self, commit1: str = None, commit2: str = None) -> str:
        """Get diff between commits or current changes"""
        if not self.enabled or not self.repo:
            return ""
        
        try:
            if commit1 and commit2:
                diff = self.repo.git.diff(commit1, commit2)
            elif commit1:
                diff = self.repo.git.diff(commit1, 'HEAD')
            else:
                diff = self.repo.git.diff('HEAD')
            
            return diff
        except Exception as e:
            logger.error(f"Failed to get diff: {e}")
            return ""

# Global instance
git_manager = GitManager()

