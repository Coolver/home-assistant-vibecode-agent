"""Git versioning manager"""
import os
import git
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import logging
import tempfile
import shutil
import subprocess

logger = logging.getLogger('ha_cursor_agent')

class GitManager:
    """Manages Git versioning for config files"""
    
    def __init__(self):
        self.config_path = Path(os.getenv('CONFIG_PATH', '/config'))
        self.enabled = os.getenv('ENABLE_GIT', 'false').lower() == 'true'
        self.auto_backup = os.getenv('AUTO_BACKUP', 'true').lower() == 'true'
        self.max_backups = int(os.getenv('MAX_BACKUPS', '30'))
        logger.info(f"GitManager initialized: max_backups={self.max_backups}, enabled={self.enabled}")
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
                # Get current branch name
                current_branch = self.repo.active_branch.name
                
                # Use git rev-list to count only commits reachable from HEAD
                # Use --first-parent to follow only the main branch (not merge commits)
                # Note: --first-parent already excludes reflog-only commits, so no need for gc before counting
                # git gc is expensive (takes ~4 minutes) and not needed here
                rev_list_output = self.repo.git.rev_list('--count', '--first-parent', 'HEAD')
                commit_count = int(rev_list_output.strip())
                logger.info(f"Commit count via rev-list --first-parent HEAD ({current_branch}): {commit_count}")
            except Exception as e:
                # Fallback: use git log with explicit HEAD reference
                logger.warning(f"git rev-list failed, using git log fallback: {e}")
                try:
                    log_output = self.repo.git.log('--oneline', '--first-parent', 'HEAD', '--max-count=100')
                    commit_count = len([line for line in log_output.strip().split('\n') if line.strip()])
                    logger.info(f"Commit count via git log --first-parent HEAD: {commit_count}")
                except Exception as e2:
                    # Last fallback: count commits using iter_commits with HEAD
                    logger.warning(f"git log failed, using iter_commits fallback: {e2}")
                    commit_count = len(list(self.repo.iter_commits('HEAD', max_count=1000)))
            
            # Always log this check (not debug) to see what's happening
            logger.info(f"Checking cleanup: commit_count={commit_count}, max_backups={self.max_backups}, need_cleanup={commit_count >= self.max_backups}")
            if commit_count >= self.max_backups:
                commits_to_keep = max(10, self.max_backups - 10)
                logger.info(f"⚠️ Cleanup triggered: commit_count ({commit_count}) >= max_backups ({self.max_backups}), will keep {commits_to_keep} commits")
                # At max_backups, cleanup to keep only (max_backups - 10) commits
                await self._cleanup_old_commits()
                
                # After cleanup, reload repository to ensure we have correct state
                # This is critical because cleanup replaces .git directory
                try:
                    self.repo = git.Repo(self.repo.working_dir)
                    # Verify cleanup worked by checking commit count again
                    rev_list_output = self.repo.git.rev_list('--count', '--first-parent', 'HEAD')
                    new_count = int(rev_list_output.strip())
                    logger.info(f"After cleanup: Repository now has {new_count} commits (was {commit_count})")
                except Exception as reload_error:
                    logger.warning(f"Failed to reload repository after cleanup: {reload_error}")
            else:
                logger.debug(f"No cleanup needed: commit_count ({commit_count}) < max_backups ({self.max_backups})")
            
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
    
    def _check_git_filter_repo_available(self) -> bool:
        """Check if git filter-repo is available in the system"""
        try:
            # Try to run git filter-repo --version
            import subprocess
            result = subprocess.run(['git', 'filter-repo', '--version'], 
                                  capture_output=True, 
                                  timeout=5,
                                  cwd=self.repo.working_dir)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            return False
    
    async def _cleanup_old_commits(self):
        """Remove old commits to save space - keeps only (max_backups - 10) commits when reaching max_backups
        
        This is called automatically when commits reach max_backups.
        We keep (max_backups - 10) commits to have buffer of 10 before next cleanup.
        For manual cleanup with backup branch deletion, use cleanup_commits().
        
        This method safely removes old commits while preserving:
        - All current files on disk (unchanged)
        - Last (max_backups - 10) commits (history)
        - Ability to rollback to any of the last (max_backups - 10) versions
        
        Uses git filter-repo if available (recommended), otherwise falls back to clone method.
        """
        try:
            # Count commits in current branch only (not all commits in repo)
            try:
                # Get current branch name
                current_branch = self.repo.active_branch.name
                
                # Use git rev-list to count only commits reachable from HEAD
                # Use --first-parent to follow only the main branch (not merge commits)
                # Note: --first-parent already excludes reflog-only commits, so no need for gc before counting
                # git gc is expensive (takes ~4 minutes) and not needed here
                rev_list_output = self.repo.git.rev_list('--count', '--first-parent', 'HEAD')
                total_commits = int(rev_list_output.strip())
                logger.info(f"Total commits via rev-list --first-parent HEAD ({current_branch}): {total_commits}")
            except Exception as e:
                # Fallback: use git log with explicit HEAD reference
                logger.warning(f"git rev-list failed, using git log fallback: {e}")
                try:
                    log_output = self.repo.git.log('--oneline', '--first-parent', 'HEAD', '--max-count=100')
                    total_commits = len([line for line in log_output.strip().split('\n') if line.strip()])
                    logger.info(f"Total commits via git log --first-parent HEAD: {total_commits}")
                except Exception as e2:
                    # Last fallback: count commits using iter_commits with HEAD
                    logger.warning(f"git log failed, using iter_commits fallback: {e2}")
                    total_commits = len(list(self.repo.iter_commits('HEAD', max_count=1000)))
            
            # Keep (max_backups - 10) commits when we reach max_backups
            # This provides a buffer of 10 commits before next cleanup
            # For max_backups=30, this keeps 20 commits
            commits_to_keep_count = max(10, self.max_backups - 10)  # Minimum 10 commits, buffer of 10
            
            if total_commits < self.max_backups:
                return  # No cleanup needed yet
            
            logger.info(f"Repository has {total_commits} commits, reached max ({self.max_backups}). Starting automatic cleanup to keep {commits_to_keep_count} commits...")
            
            # Try to use git filter-repo if available (recommended method)
            if self._check_git_filter_repo_available():
                logger.info("Using git filter-repo for cleanup (recommended method)")
                try:
                    # Ensure all current changes are committed before cleanup
                    if self.repo.is_dirty(untracked_files=True):
                        await self.commit_changes("Pre-cleanup commit: save current state")
                    
                    # Use git filter-repo to keep only last N commits
                    # This is the cleanest and most reliable method
                    import subprocess
                    result = subprocess.run(
                        ['git', 'filter-repo', '--max-commit-count', str(commits_to_keep_count)],
                        cwd=self.repo.working_dir,
                        capture_output=True,
                        text=True,
                        timeout=300  # 5 minutes timeout
                    )
                    
                    if result.returncode != 0:
                        raise Exception(f"git filter-repo failed with exit code {result.returncode}: {result.stderr}")
                    
                    # Reload the repository after filter-repo (it modifies the repo)
                    # We need to reinitialize or refresh the repo object
                    # For now, just verify the result
                    rev_list_output = self.repo.git.rev_list('--count', '--no-merges', current_branch)
                    commits_after = int(rev_list_output.strip())
                    logger.info(f"✅ Cleanup complete using git filter-repo: {total_commits} → {commits_after} commits. Removed {total_commits - commits_after} old commits.")
                    return
                except Exception as filter_repo_error:
                    logger.warning(f"git filter-repo failed: {filter_repo_error}. Falling back to orphan branch method.")
                    # Continue with fallback method below
            
            # Use clone with depth method (simpler and more reliable)
            # Note: We don't commit uncommitted changes here because cleanup is called
            # AFTER a commit was just made, so there should be no uncommitted changes.
            # If there are, they will be lost during cleanup (which is acceptable for automatic cleanup).
            
            # Save current branch name
            current_branch = self.repo.active_branch.name
            
            # Use clone with depth method
            await self._cleanup_using_clone_depth(total_commits, commits_to_keep_count, current_branch)
            
            # After cleanup, verify the count is correct and reload repository
            # This ensures we have the correct state for future operations
            try:
                self.repo = git.Repo(self.repo.working_dir)
                # Force refresh by checking commit count again
                rev_list_output = self.repo.git.rev_list('--count', '--first-parent', 'HEAD')
                final_count = int(rev_list_output.strip())
                logger.info(f"✅ Cleanup verification: Repository now has {final_count} commits")
            except Exception as verify_error:
                logger.warning(f"Failed to verify cleanup result: {verify_error}")
            
        except Exception as cleanup_error:
            logger.error(f"Failed to cleanup commits: {cleanup_error}")
            # Don't fail the whole operation if cleanup fails - repository is still usable
    
    async def _cleanup_using_clone_depth(self, total_commits: int, commits_to_keep_count: int, current_branch: str):
        """Cleanup method using git clone with depth - simpler and more reliable
        
        This method:
        1. Clones the existing repository with depth=commits_to_keep_count
        2. Verifies the clone is correct
        3. Replaces the old .git directory with the new one
        4. Runs gc for final cleanup
        """
        try:
            repo_path = self.repo.working_dir
            
            # CRITICAL SAFETY CHECK: Verify repo_path matches config_path
            # This ensures we're working on the correct directory and won't accidentally delete configs
            if str(repo_path) != str(self.config_path):
                raise Exception(f"SAFETY CHECK FAILED: repo_path ({repo_path}) does not match config_path ({self.config_path}). This could cause data loss!")
            
            git_dir = os.path.join(repo_path, '.git')
            
            # Verify git_dir is actually inside repo_path (not the same as repo_path)
            if git_dir == repo_path:
                raise Exception(f"SAFETY CHECK FAILED: git_dir ({git_dir}) equals repo_path ({repo_path}). This would delete all configs!")
            
            # Verify git_dir is a subdirectory of repo_path
            if not git_dir.startswith(str(repo_path) + os.sep):
                raise Exception(f"SAFETY CHECK FAILED: git_dir ({git_dir}) is not inside repo_path ({repo_path})")
            
            # Create temporary directory for clone
            with tempfile.TemporaryDirectory() as tmpdir:
                clone_path = os.path.join(tmpdir, 'cloned_repo')
                
                logger.info(f"Cloning repository with depth={commits_to_keep_count}...")
                
                # Clone the repository with specified depth
                # Use file:// protocol for local clone to avoid hard links
                # --depth creates a shallow clone with only last N commits
                # --single-branch clones only the current branch
                repo_url = f'file://{repo_path}'
                logger.info(f"Starting git clone from {repo_url} to {clone_path} with depth={commits_to_keep_count}...")
                result = subprocess.run(
                    ['git', 'clone', '--depth', str(commits_to_keep_count), 
                     '--branch', current_branch, '--single-branch',
                     repo_url, clone_path],
                    capture_output=True,
                    text=True,
                    timeout=600  # Increased to 10 minutes for large repos
                )
                logger.info(f"git clone completed with return code: {result.returncode}")
                
                if result.returncode != 0:
                    raise Exception(f"git clone failed: {result.stderr}")
                
                # Verify the clone has correct number of commits
                cloned_repo = git.Repo(clone_path)
                cloned_commits = len(list(cloned_repo.iter_commits(max_count=commits_to_keep_count + 10)))
                
                if cloned_commits > commits_to_keep_count:
                    logger.warning(f"Clone has {cloned_commits} commits, expected {commits_to_keep_count}. This is normal for shallow clones.")
                else:
                    logger.info(f"Clone verified: {cloned_commits} commits")
                
                # Backup old .git directory (just in case)
                git_backup = os.path.join(tmpdir, 'git_backup')
                if os.path.exists(git_dir):
                    logger.info(f"Backing up old .git directory from {git_dir} to {git_backup}...")
                    shutil.copytree(git_dir, git_backup)
                    logger.info("Backed up old .git directory")
                
                # Replace .git directory with cloned one
                logger.info("Replacing .git directory with cloned repository...")
                
                # CRITICAL: Verify clone has working tree files before replacing .git
                # This ensures we don't lose uncommitted files
                cloned_git_dir = os.path.join(clone_path, '.git')
                if not os.path.exists(cloned_git_dir):
                    raise Exception("Cloned .git directory does not exist - aborting cleanup to prevent data loss")
                
                # Verify clone is valid before replacing
                try:
                    test_repo = git.Repo(clone_path)
                    if not test_repo.heads:
                        raise Exception("Cloned repository has no branches - aborting cleanup")
                except Exception as verify_error:
                    raise Exception(f"Cloned repository verification failed: {verify_error} - aborting cleanup to prevent data loss")
                
                # CRITICAL SAFETY CHECK: Verify that we're only replacing .git, not the entire config directory
                # This ensures we never accidentally delete config files
                if git_dir != os.path.join(repo_path, '.git'):
                    raise Exception(f"SAFETY CHECK FAILED: git_dir path is incorrect: {git_dir} (expected: {os.path.join(repo_path, '.git')})")
                
                # Verify that repo_path contains config files before replacing .git
                # This ensures we don't accidentally work on wrong directory
                # Use try-except to handle potential timeouts or permission issues
                try:
                    logger.info(f"Checking for config files in {repo_path}...")
                    all_files = os.listdir(repo_path)
                    config_files = [f for f in all_files if f.endswith('.yaml') and f != '.git']
                    if not config_files:
                        logger.warning(f"WARNING: No .yaml config files found in {repo_path} before cleanup. This may indicate a problem.")
                    else:
                        logger.info(f"Safety check: Found {len(config_files)} config files in {repo_path} - safe to proceed")
                except Exception as listdir_error:
                    logger.warning(f"Could not list directory contents: {listdir_error}. Continuing anyway.")
                    config_files = []  # Set to empty list to avoid NameError
                
                # Now safe to replace .git directory ONLY (not the entire repo_path)
                if os.path.exists(git_dir):
                    logger.info(f"Removing old .git directory: {git_dir}")
                    shutil.rmtree(git_dir)
                
                logger.info(f"Copying new .git directory from clone to: {git_dir}")
                shutil.copytree(cloned_git_dir, git_dir)
                
                # Verify config files still exist after .git replacement
                try:
                    config_files_after = [f for f in os.listdir(repo_path) if f.endswith('.yaml') and f != '.git']
                    if config_files and len(config_files_after) < len(config_files):
                        raise Exception(f"SAFETY CHECK FAILED: Config files were lost during cleanup! Before: {len(config_files)}, After: {len(config_files_after)}")
                    elif config_files:
                        logger.info(f"Safety check passed: {len(config_files_after)} config files still present after cleanup")
                except Exception as verify_error:
                    logger.warning(f"Could not verify config files after cleanup: {verify_error}")
                    # Don't fail the whole operation if verification fails - files are likely still there
                
                logger.info("✅ Repository replaced successfully - all config files verified intact")
            
            # Reload repository to get fresh state
            self.repo = git.Repo(repo_path)
            
            # Run gc for final cleanup (optional but recommended)
            try:
                logger.info("Running final git gc...")
                subprocess.run(['git', 'gc', '--prune=now', '--quiet'], 
                             cwd=repo_path, capture_output=True, timeout=600)  # Increased timeout
                logger.info("Final gc completed")
            except Exception as gc_error:
                logger.warning(f"Final gc failed: {gc_error}. Continuing.")
            
            # Reload repository after gc
            self.repo = git.Repo(repo_path)
            
            # Verify final count
            try:
                rev_list_output = self.repo.git.rev_list('--count', '--first-parent', 'HEAD')
                commits_after = int(rev_list_output.strip())
                logger.info(f"Final commit count: {commits_after}")
            except:
                commits_after = commits_to_keep_count
            
            logger.info(f"✅ Automatic cleanup complete: {total_commits} → {commits_after} commits. Removed {total_commits - commits_after} old commits.")
            
        except Exception as cleanup_error:
            logger.error(f"Failed to cleanup commits using clone method: {cleanup_error}")
            # Try to restore from backup if available
            # Don't fail the whole operation if cleanup fails - repository is still usable
            raise
    
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
            # Use subprocess with explicit working directory to avoid "Unable to read current working directory" errors
            if commit1 and commit2:
                result = subprocess.run(
                    ['git', 'diff', commit1, commit2],
                    cwd=str(self.repo.working_dir),
                    capture_output=True,
                    text=True,
                    timeout=240
                )
            elif commit1:
                result = subprocess.run(
                    ['git', 'diff', commit1, 'HEAD'],
                    cwd=str(self.repo.working_dir),
                    capture_output=True,
                    text=True,
                    timeout=240
                )
            else:
                result = subprocess.run(
                    ['git', 'diff', 'HEAD'],
                    cwd=str(self.repo.working_dir),
                    capture_output=True,
                    text=True,
                    timeout=240
                )
            
            if result.returncode != 0:
                logger.warning(f"git diff returned non-zero exit code: {result.stderr}")
                return ""
            
            return result.stdout
        except Exception as e:
            logger.error(f"Failed to get diff: {e}")
            return ""
    
    async def restore_files_from_commit(self, commit_hash: str = None, file_patterns: List[str] = None) -> Dict:
        """Restore files from a specific commit using subprocess (bypasses GitPython issues)
        
        Args:
            commit_hash: Commit hash to restore from (default: HEAD)
            file_patterns: List of file patterns to restore (e.g., ['*.yaml', 'configuration.yaml'])
                          If None, restores all tracked files
        
        Returns:
            Dict with success status and restored files list
        """
        if not self.enabled:
            raise Exception("Git versioning not enabled")
        
        if not self.repo or not self.repo.working_dir:
            raise Exception("Git repository not available or working directory missing")
        
        repo_path = str(self.repo.working_dir)
        
        try:
            # Use HEAD if no commit specified
            if not commit_hash:
                # Try to get HEAD commit hash
                result = subprocess.run(
                    ['git', 'rev-parse', 'HEAD'],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode != 0:
                    raise Exception(f"Cannot get HEAD commit: {result.stderr}")
                commit_hash = result.stdout.strip()
            
            logger.info(f"Restoring files from commit {commit_hash}...")
            
            # If file patterns specified, restore only those files
            if file_patterns:
                restored_files = []
                for pattern in file_patterns:
                    # Get list of files matching pattern in commit
                    result = subprocess.run(
                        ['git', 'ls-tree', '-r', '--name-only', commit_hash, pattern],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        timeout=240
                    )
                    if result.returncode == 0:
                        files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
                        for file_path in files:
                            # Restore individual file
                            restore_result = subprocess.run(
                                ['git', 'checkout', commit_hash, '--', file_path],
                                cwd=repo_path,
                                capture_output=True,
                                text=True,
                                timeout=240
                            )
                            if restore_result.returncode == 0:
                                restored_files.append(file_path)
                                logger.info(f"Restored file: {file_path}")
                            else:
                                logger.warning(f"Failed to restore {file_path}: {restore_result.stderr}")
            else:
                # Restore all tracked files from commit
                result = subprocess.run(
                    ['git', 'checkout', commit_hash, '--', '.'],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=240
                )
                
                if result.returncode != 0:
                    raise Exception(f"Failed to restore files: {result.stderr}")
                
                # Get list of restored files
                status_result = subprocess.run(
                    ['git', 'status', '--porcelain'],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                restored_files = []
                if status_result.returncode == 0:
                    for line in status_result.stdout.split('\n'):
                        if line.strip() and not line.startswith('??'):
                            # Extract filename (handles both staged and unstaged)
                            parts = line.strip().split()
                            if len(parts) >= 2:
                                restored_files.append(parts[-1])
                
                logger.info(f"Restored {len(restored_files)} files from commit {commit_hash}")
            
            return {
                "success": True,
                "commit": commit_hash,
                "restored_files": restored_files,
                "count": len(restored_files)
            }
            
        except Exception as e:
            logger.error(f"Failed to restore files from commit: {e}")
            raise Exception(f"Restore failed: {e}")

# Global instance
git_manager = GitManager()

