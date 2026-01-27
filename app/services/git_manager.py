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
    """Manages Git versioning for config files (using a shadow Git repo)"""
    
    def __init__(self):
        # Root of the actual Home Assistant config
        self.config_path = Path(os.getenv('CONFIG_PATH', '/config'))
        # Shadow repository root where the agent keeps its own Git history.
        # IMPORTANT: We no longer use /config/.git at all to avoid interfering
        # with the user's own Git (e.g. GitHub remote).
        self.shadow_root = self.config_path / 'ha_vibecode_git'

        # git_versioning_auto: if True, commits happen automatically after each operation
        # if False, commits only happen when explicitly requested via /api/backup/commit
        # Git is always enabled in shadow repo, but commits only happen based on this setting
        self.git_versioning_auto = os.getenv('GIT_VERSIONING_AUTO', 'true').lower() == 'true'
        self.max_backups = int(os.getenv('MAX_BACKUPS', '30'))
        logger.info(f"GitManager initialized: max_backups={self.max_backups}, auto={self.git_versioning_auto}")
        self.repo = None
        self.processing_request = False  # Flag to disable auto-commits during request processing
        
        # Always initialize shadow repo (Git is always enabled)
        self._init_repo()
    
    def _init_repo(self):
        """Initialize shadow Git repository used by the agent.
        
        NOTE:
        - We intentionally do NOT touch /config/.git anymore.
        - All Git operations happen inside /config/ha_vibecode_git.
        """
        try:
            # Ensure shadow root exists
            self.shadow_root.mkdir(parents=True, exist_ok=True)

            if (self.shadow_root / '.git').exists():
                # Load existing shadow repository
                self.repo = git.Repo(self.shadow_root)
                logger.info(f"Git shadow repository loaded from {self.shadow_root}")
            else:
                # Initialize new shadow repository
                self.repo = git.Repo.init(self.shadow_root)
                self.repo.config_writer().set_value("user", "name", "HA Vibecode Agent").release()
                self.repo.config_writer().set_value("user", "email", "agent@homeassistant.local").release()
                logger.info(f"Git shadow repository initialized in {self.shadow_root}")
        except Exception as e:
            logger.error(f"Failed to initialize Git: {e}")
    
    def _create_gitignore(self):
        """(Legacy) Create .gitignore file in config directory to exclude large files.
        
        NOTE: In the new shadow-repo implementation we no longer rely on
        .gitignore in /config and we don't touch user's .git at all. This
        method is kept for backwards compatibility only and is not used.
        """
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

    def _should_include_path(self, rel_path: str, is_dir: bool) -> bool:
        """Return True if a path (relative to /config) should be tracked in Git.
        
        This replaces the previous .gitignore-in-/config approach. We now
        explicitly filter which files we copy into the shadow repository:
        - Exclude known large / internal dirs: .storage, www, media, storage, tmp, etc.
        - Exclude DB, log and backup files
        - Exclude secrets and key/cert files
        - Exclude the agent's own shadow repo and any Git metadata
        """
        # Normalize to forward-slash style for matching
        rel_path = rel_path.replace(os.sep, '/')

        # Skip our own shadow repository and any .git directories
        parts = rel_path.split('/')
        if parts[0] in ('.git', 'ha_vibecode_git'):
            return False

        # Exclude well-known heavy / internal directories at top-level
        if is_dir:
            if parts[0] in ('.storage', '.cloud', '.homeassistant',
                            'www', 'media', 'storage', 'tmp',
                            'node_modules', '__pycache__'):
                return False
            return True

        # File-level patterns
        import fnmatch
        filename = parts[-1]

        # Secrets / keys
        if filename in ('secrets.yaml', '.secrets.yaml'):
            return False
        if fnmatch.fnmatch(filename, '*.pem') or fnmatch.fnmatch(filename, '*.key') or fnmatch.fnmatch(filename, '*.crt'):
            return False

        # DB-like files
        db_patterns = [
            '*.db', '*.db-shm', '*.db-wal', '*.db-journal',
            '*.sqlite', '*.sqlite3', 'home-assistant_v2.db*',
        ]
        for pattern in db_patterns:
            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(rel_path, pattern):
                return False

        # Logs
        log_patterns = ['*.log', '*.log.*', 'home-assistant.log']
        for pattern in log_patterns:
            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(rel_path, pattern):
                return False

        # Backup-like files
        backup_patterns = ['*.bak', '*.backup', '*.old', '*.tmp', '*.temp', '*~']
        for pattern in backup_patterns:
            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(rel_path, pattern):
                return False

        # Exclude files inside heavy/internal dirs (in case they weren't pruned as dirs)
        dir_prefix_patterns = [
            '.storage/', '.cloud/', '.homeassistant/',
            'www/', 'media/', 'storage/', 'tmp/',
        ]
        for prefix in dir_prefix_patterns:
            if rel_path.startswith(prefix):
                return False

        return True

    def _sync_config_to_shadow(self):
        """Synchronize filtered files from /config into the shadow repo worktree.
        
        This copies only the files we want to version (respecting _should_include_path)
        and removes files from the shadow worktree that are no longer present in /config.
        """

        source_root = self.config_path
        shadow_root = self.shadow_root
        shadow_root.mkdir(parents=True, exist_ok=True)

        included_paths = set()

        # Copy files from /config → shadow_root
        for root, dirs, files in os.walk(source_root):
            rel_root = os.path.relpath(root, source_root)
            if rel_root == '.':
                rel_root = ''

            # Prune directories we don't want to walk into
            pruned_dirs = []
            for d in list(dirs):
                rel_dir = os.path.join(rel_root, d) if rel_root else d
                if not self._should_include_path(rel_dir, is_dir=True):
                    dirs.remove(d)
                    pruned_dirs.append(d)
            if pruned_dirs:
                logger.debug(f"Pruned dirs from sync: {pruned_dirs}")

            for filename in files:
                rel_path = os.path.join(rel_root, filename) if rel_root else filename
                rel_path_norm = os.path.normpath(rel_path)
                if not self._should_include_path(rel_path_norm, is_dir=False):
                    continue

                src = source_root / rel_path_norm
                dst = shadow_root / rel_path_norm
                dst.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(src, dst)
                    included_paths.add(rel_path_norm.replace(os.sep, '/'))
                except Exception as e:
                    logger.warning(f"Failed to copy {src} to shadow repo: {e}")

        # Remove files from shadow_root that are no longer present in /config
        # BUT preserve export/ directory (created by agent, not synced from /config)
        for root, dirs, files in os.walk(shadow_root):
            # Never touch .git inside the shadow repo
            if '.git' in dirs:
                dirs.remove('.git')
            
            # Skip export/ directory - it's managed by agent, not synced from /config
            if 'export' in dirs:
                dirs.remove('export')

            rel_root = os.path.relpath(root, shadow_root)
            if rel_root == '.':
                rel_root = ''

            # Skip export/ directory entirely
            if rel_root.startswith('export'):
                continue

            for filename in files:
                rel_path = os.path.join(rel_root, filename) if rel_root else filename
                rel_path_norm = os.path.normpath(rel_path).replace(os.sep, '/')
                if rel_path_norm not in included_paths:
                    try:
                        os.remove(os.path.join(root, filename))
                    except Exception as e:
                        logger.warning(f"Failed to remove obsolete file from shadow repo: {rel_path_norm}: {e}")

    def _sync_shadow_to_config(self, only_paths: Optional[List[str]] = None, delete_missing: bool = False):
        """Synchronize files from shadow repo worktree back into /config.
        
        - If only_paths is provided: sync only those relative paths (no deletion by default).
        - If delete_missing is True: remove files from /config that are tracked in the
          shadow repo but are missing in its current worktree.
        """

        shadow_root = self.shadow_root
        source_root = shadow_root
        target_root = self.config_path

        def _copy_single(rel_path: str):
            rel_path_norm = os.path.normpath(rel_path)
            src = source_root / rel_path_norm
            dst = target_root / rel_path_norm
            if not src.exists():
                return
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(src, dst)
            except Exception as e:
                logger.warning(f"Failed to restore {rel_path_norm} to /config: {e}")

        if only_paths:
            for p in only_paths:
                _copy_single(p)
        else:
            # Copy all files from shadow_root (except .git, ha_vibecode_git, export) into /config
            for root, dirs, files in os.walk(source_root):
                if '.git' in dirs:
                    dirs.remove('.git')
                if 'export' in dirs:
                    dirs.remove('export')
                rel_root = os.path.relpath(root, source_root)
                if rel_root == '.':
                    rel_root = ''
                # Skip export/ directory - it's agent-managed, not user config
                if rel_root.startswith('export'):
                    continue
                for filename in files:
                    rel_path = os.path.join(rel_root, filename) if rel_root else filename
                    _copy_single(rel_path)

        if delete_missing:
            # Build sets of tracked paths in shadow and in /config (filtered)
            shadow_paths = set()
            for root, dirs, files in os.walk(source_root):
                if '.git' in dirs:
                    dirs.remove('.git')
                if 'export' in dirs:
                    dirs.remove('export')
                rel_root = os.path.relpath(root, source_root)
                if rel_root == '.':
                    rel_root = ''
                # Skip export/ directory
                if rel_root.startswith('export'):
                    continue
                for filename in files:
                    rel_path = os.path.join(rel_root, filename) if rel_root else filename
                    rel_path_norm = os.path.normpath(rel_path).replace(os.sep, '/')
                    shadow_paths.add(rel_path_norm)

            config_paths = set()
            for root, dirs, files in os.walk(target_root):
                # Never touch .git or our own shadow dir in /config
                for skip_dir in ('.git', 'ha_vibecode_git'):
                    if skip_dir in dirs:
                        dirs.remove(skip_dir)
                rel_root = os.path.relpath(root, target_root)
                if rel_root == '.':
                    rel_root = ''
                for filename in files:
                    rel_path = os.path.join(rel_root, filename) if rel_root else filename
                    rel_path_norm = os.path.normpath(rel_path)
                    # Apply same include filter so we don't delete ignored/large files
                    if not self._should_include_path(rel_path_norm, is_dir=False):
                        continue
                    config_paths.add(rel_path_norm.replace(os.sep, '/'))

            for rel_path in config_paths:
                if rel_path not in shadow_paths:
                    try:
                        os.remove(target_root / rel_path)
                        logger.info(f"Removed file from /config during rollback: {rel_path}")
                    except Exception as e:
                        logger.warning(f"Failed to remove {rel_path} from /config during rollback: {e}")
    
    async def commit_changes(self, message: str = None, skip_if_processing: bool = False, force: bool = False) -> Optional[str]:
        """Commit current changes
        
        Args:
            message: Commit message (if None, will be auto-generated)
            skip_if_processing: Skip if request processing in progress
            force: Force commit even if git_versioning_auto is False (for rollback/cleanup)
        """
        if not self.repo:
            return None
        
        # Skip auto-commits if processing a request (unless explicitly requested)
        if skip_if_processing and self.processing_request:
            logger.debug("Skipping auto-commit - request processing in progress")
            return None
        
        try:
            # First, synchronize filtered files from /config into the shadow repo
            self._sync_config_to_shadow()

            # Check if there are changes (only for tracked files and config files)
            if not self.repo.is_dirty(untracked_files=True):
                logger.debug("No changes to commit")
                return None
            
            # If auto-commit is disabled and this is not a forced commit, only sync but don't commit
            if not self.git_versioning_auto and not force:
                logger.debug("Auto-commit disabled, changes synced to shadow repo but not committed")
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
        if not self.repo:
            return {
                "success": False,
                "message": "Git versioning not enabled",
                "commit_hash": None,
                "tag": None
            }
        
        try:
            # Commit current state first (if there are changes)
            # force=True to always commit before checkpoint, regardless of auto mode
            commit_hash = await self.commit_changes(
                f"Checkpoint before: {user_request}",
                skip_if_processing=False,
                force=True
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
                    # force=True to always commit before cleanup, regardless of auto mode
                    if self.repo.is_dirty(untracked_files=True):
                        await self.commit_changes("Pre-cleanup commit: save current state", force=True)
                    
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
            
            # CRITICAL SAFETY CHECK: Verify repo_path matches shadow_root
            # This ensures we're working on the correct directory and won't accidentally touch /config directly
            if str(repo_path) != str(self.shadow_root):
                raise Exception(f"SAFETY CHECK FAILED: repo_path ({repo_path}) does not match shadow_root ({self.shadow_root}). This could cause data loss!")
            
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
        if not self.repo:
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
            # force=True to always commit before cleanup, regardless of auto mode
            if self.repo.is_dirty(untracked_files=True):
                await self.commit_changes("Pre-cleanup commit: save current state", force=True)
            
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
        if not self.repo:
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
    
    async def get_pending_changes(self) -> Dict:
        """Get information about uncommitted changes in shadow repository
        
        Returns:
            Dict with:
            - has_changes: bool - whether there are uncommitted changes
            - files_modified: List[str] - list of modified file paths
            - files_added: List[str] - list of newly added file paths
            - files_deleted: List[str] - list of deleted file paths
            - summary: Dict with counts
            - diff: str - full diff (optional, can be large)
        """
        if not self.repo:
            return {
                "has_changes": False,
                "files_modified": [],
                "files_added": [],
                "files_deleted": [],
                "summary": {
                    "modified": 0,
                    "added": 0,
                    "deleted": 0,
                    "total": 0
                }
            }
        
        try:
            # Sync current state from /config to shadow repo
            self._sync_config_to_shadow()
            
            # Get status of changes
            status_output = self.repo.git.status('--porcelain')
            
            files_modified = []
            files_added = []
            files_deleted = []
            
            for line in status_output.strip().split('\n'):
                if not line.strip():
                    continue
                
                # Git status format: XY filename
                # X = status of index, Y = status of work tree
                # M = modified, A = added, D = deleted, ?? = untracked
                status_code = line[:2]
                file_path = line[3:].strip()
                
                if status_code.startswith('??'):
                    # Untracked file (new file)
                    files_added.append(file_path)
                elif 'D' in status_code:
                    # Deleted file
                    files_deleted.append(file_path)
                elif 'M' in status_code or 'A' in status_code:
                    # Modified or added
                    if status_code[0] == 'A' or status_code[1] == 'A':
                        files_added.append(file_path)
                    else:
                        files_modified.append(file_path)
            
            has_changes = len(files_modified) > 0 or len(files_added) > 0 or len(files_deleted) > 0
            
            # Get diff (can be large, so make it optional)
            diff = ""
            if has_changes:
                try:
                    diff = await self.get_diff()
                except Exception as diff_error:
                    logger.warning(f"Failed to get diff for pending changes: {diff_error}")
                    diff = ""
            
            return {
                "has_changes": has_changes,
                "files_modified": files_modified,
                "files_added": files_added,
                "files_deleted": files_deleted,
                "summary": {
                    "modified": len(files_modified),
                    "added": len(files_added),
                    "deleted": len(files_deleted),
                    "total": len(files_modified) + len(files_added) + len(files_deleted)
                },
                "diff": diff
            }
        except Exception as e:
            logger.error(f"Failed to get pending changes: {e}")
            return {
                "has_changes": False,
                "files_modified": [],
                "files_added": [],
                "files_deleted": [],
                "summary": {
                    "modified": 0,
                    "added": 0,
                    "deleted": 0,
                    "total": 0
                },
                "error": str(e)
            }
    
    def _generate_commit_message_from_changes(self, pending_info: Dict) -> str:
        """Generate a suggested commit message based on pending changes
        
        This is a simple heuristic-based generator. AI in IDE can improve it.
        """
        if not pending_info.get("has_changes"):
            return "No changes to commit"
        
        summary = pending_info.get("summary", {})
        files_modified = pending_info.get("files_modified", [])
        files_added = pending_info.get("files_added", [])
        files_deleted = pending_info.get("files_deleted", [])
        
        # Analyze file types and generate description
        actions = []
        
        # Check for common patterns
        if any('automation' in f.lower() for f in files_modified + files_added):
            actions.append("Update automations")
        if any('script' in f.lower() for f in files_modified + files_added):
            actions.append("Update scripts")
        if any('dashboard' in f.lower() or 'lovelace' in f.lower() for f in files_modified + files_added):
            actions.append("Update dashboard")
        if any('theme' in f.lower() for f in files_modified + files_added):
            actions.append("Update theme")
        if any('configuration' in f.lower() or 'config' in f.lower() for f in files_modified + files_added):
            actions.append("Update configuration")
        
        # If we have specific file names, use them
        if files_added:
            for f in files_added[:3]:  # Limit to first 3
                if 'automation' in f.lower():
                    actions.append(f"Add automation: {f}")
                elif 'script' in f.lower():
                    actions.append(f"Add script: {f}")
                elif 'dashboard' in f.lower():
                    actions.append(f"Add dashboard: {f}")
        
        if files_deleted:
            actions.append(f"Remove {len(files_deleted)} file(s)")
        
        # Generate message
        if actions:
            # Combine actions, limit length
            message = ", ".join(actions[:5])  # Max 5 actions
            if len(actions) > 5:
                message += f" and {len(actions) - 5} more"
        else:
            # Fallback: generic message with counts
            total = summary.get("total", 0)
            if total == 1:
                message = "Update configuration"
            else:
                message = f"Update {total} file(s)"
        
        return message
    
    async def rollback(self, commit_hash: str) -> Dict:
        """Rollback to specific commit"""
        if not self.repo:
            raise Exception("Git versioning not enabled")
        
        try:
            # Commit current state before rollback (force=True to always commit before rollback)
            await self.commit_changes(f"Before rollback to {commit_hash}", force=True)
            
            # Reset shadow repo worktree to the specified commit
            self.repo.git.reset('--hard', commit_hash)
            
            # Sync full state from shadow repo back into /config, removing
            # files that are no longer present in the selected commit.
            self._sync_shadow_to_config(only_paths=None, delete_missing=True)
            
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
        if not self.repo:
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
        if not self.repo or not self.repo.working_dir:
            raise Exception("Git repository not available or working directory missing")
        
        # All Git operations happen in the shadow repo
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
                                logger.info(f"Restored file in shadow repo: {file_path}")
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
                    
                logger.info(f"Restored {len(restored_files)} files in shadow repo from commit {commit_hash}")
            
            # Sync restored files from shadow repo back into /config
            self._sync_shadow_to_config(
                only_paths=restored_files if file_patterns else None,
                delete_missing=False
            )
            
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

