"""Git repository handler for cloning and navigating commits."""

import os
import shutil
from pathlib import Path
from typing import Optional

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

from .logger import setup_logger

logger = setup_logger()


class GitHandler:
    """Handles Git operations for repository cloning and commit navigation."""

    def __init__(self, workspace_dir: str = "repos"):
        """Initialize Git handler with workspace directory.

        Args:
            workspace_dir: Directory to store cloned repositories
        """
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(exist_ok=True)
        self.repo: Optional[Repo] = None
        self.repo_path: Optional[Path] = None
        self.repo_url: Optional[str] = None
        self.commits: list = []
        self.current_commit_index: int = -1
        logger.info(f"Initialized GitHandler with workspace: {workspace_dir}")

    def clone_repository(self, repo_url: str) -> tuple[bool, str]:
        """Clone a GitHub repository or use existing if up-to-date.

        Args:
            repo_url: GitHub repository URL (with or without .git extension)

        Returns:
            Tuple of (success, message)
        """
        logger.info(f"Attempting to clone repository: {repo_url}")
        try:
            # Normalize URL - ensure it ends with .git for consistency
            if not repo_url.endswith(".git"):
                normalized_url = repo_url.rstrip("/") + ".git"
            else:
                normalized_url = repo_url

            # Extract repository name from URL
            repo_name = normalized_url.rstrip("/").split("/")[-1]
            if repo_name.endswith(".git"):
                repo_name = repo_name[:-4]

            self.repo_path = self.workspace_dir / repo_name
            logger.debug(f"Repository path: {self.repo_path}")

            # Check if repository already exists
            if self.repo_path.exists():
                logger.info(f"Repository already exists at {self.repo_path}, checking if up-to-date")
                try:
                    # Try to load existing repository
                    existing_repo = Repo(self.repo_path)

                    # Fetch latest changes from remote
                    logger.debug("Fetching latest changes from remote")
                    origin = existing_repo.remotes.origin
                    origin.fetch()

                    # Get the default branch (usually main or master)
                    try:
                        default_branch = origin.refs.HEAD.reference.name
                    except:
                        # Fallback to common branch names
                        default_branch = 'origin/main' if 'origin/main' in [str(ref) for ref in origin.refs] else 'origin/master'

                    logger.debug(f"Default branch: {default_branch}")

                    # Get the latest commit from the default branch (not current HEAD)
                    # This gets the actual latest commit in the repo, regardless of what's checked out
                    local_latest = list(existing_repo.iter_commits(default_branch, max_count=1))[0].hexsha
                    remote_latest = origin.refs[default_branch.replace('origin/', '')].commit.hexsha

                    logger.debug(f"Local latest commit: {local_latest[:7]}, Remote latest commit: {remote_latest[:7]}")

                    if local_latest == remote_latest:
                        # Repository is up-to-date, reuse it
                        logger.info("Repository is up-to-date, reusing existing clone")
                        self.repo = existing_repo
                        self.repo_url = repo_url  # Store original URL
                        # Get all commits from the default branch (not just HEAD)
                        self.commits = list(reversed(list(self.repo.iter_commits(default_branch))))
                        self.current_commit_index = -1
                        logger.info(f"Loaded {len(self.commits)} commits from {default_branch}")
                        return True, f"Using existing {repo_name} (up-to-date, {len(self.commits)} commits)"
                    else:
                        # Repository is outdated, remove and re-clone
                        logger.warning(f"Repository is outdated (local: {local_latest[:7]}, remote: {remote_latest[:7]}), removing and re-cloning")
                        shutil.rmtree(self.repo_path)

                except Exception as e:
                    # If we can't check, just remove and re-clone to be safe
                    logger.warning(f"Could not verify existing repository: {e}, re-cloning")
                    shutil.rmtree(self.repo_path)

            # Clone the repository
            logger.info(f"Cloning repository from {normalized_url}")
            self.repo = Repo.clone_from(normalized_url, self.repo_path)
            self.repo_url = repo_url  # Store original URL (without .git)
            logger.info(f"Successfully cloned repository to {self.repo_path}")

            # Get the default branch to ensure we load all commits
            try:
                default_branch = self.repo.active_branch.name
                logger.debug(f"Active branch: {default_branch}")
            except:
                # If detached HEAD or no active branch, use 'main' or 'master'
                default_branch = 'main' if 'main' in [ref.name for ref in self.repo.refs] else 'master'
                logger.debug(f"Using default branch: {default_branch}")

            # Get all commits in chronological order (oldest first) from the default branch
            self.commits = list(reversed(list(self.repo.iter_commits(default_branch))))
            self.current_commit_index = -1
            logger.info(f"Found {len(self.commits)} commits in repository from branch {default_branch}")

            return True, f"Successfully cloned {repo_name} with {len(self.commits)} commits"

        except GitCommandError as e:
            logger.error(f"Git command error while cloning {repo_url}: {str(e)}")
            return False, f"Git error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error while cloning {repo_url}: {str(e)}", exc_info=True)
            return False, f"Error: {str(e)}"

    def load_repository(self, repo_path: str) -> tuple[bool, str]:
        """Load an existing repository.

        Args:
            repo_path: Path to existing repository

        Returns:
            Tuple of (success, message)
        """
        try:
            self.repo_path = Path(repo_path)
            self.repo = Repo(self.repo_path)

            # Get the default branch to ensure we load all commits
            try:
                default_branch = self.repo.active_branch.name
                logger.debug(f"Active branch: {default_branch}")
            except:
                # If detached HEAD or no active branch, use 'main' or 'master'
                default_branch = 'main' if 'main' in [ref.name for ref in self.repo.refs] else 'master'
                logger.debug(f"Using default branch: {default_branch}")

            # Get all commits in chronological order (oldest first) from the default branch
            self.commits = list(reversed(list(self.repo.iter_commits(default_branch))))
            self.current_commit_index = -1
            logger.info(f"Loaded {len(self.commits)} commits from branch {default_branch}")

            return True, f"Loaded repository with {len(self.commits)} commits"

        except InvalidGitRepositoryError:
            return False, f"Not a valid git repository: {repo_path}"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def go_to_first_commit(self) -> tuple[bool, str]:
        """Navigate to the first (oldest) commit.

        Returns:
            Tuple of (success, message)
        """
        if not self.repo or not self.commits:
            logger.error("Cannot navigate to first commit: no repository loaded")
            return False, "No repository loaded"

        try:
            first_commit = self.commits[0]
            logger.info(f"Checking out first commit: {first_commit.hexsha[:7]}")
            self.repo.git.checkout(first_commit.hexsha, force=True)
            self.current_commit_index = 0
            logger.debug(f"Current commit index: {self.current_commit_index}")
            return True, f"Checked out first commit: {first_commit.hexsha[:7]}"
        except GitCommandError as e:
            logger.error(f"Git error while checking out first commit: {str(e)}")
            return False, f"Git error: {str(e)}"

    def go_to_next_commit(self) -> tuple[bool, str]:
        """Navigate to the next commit.

        Returns:
            Tuple of (success, message)
        """
        if not self.repo or not self.commits:
            logger.error("Cannot navigate to next commit: no repository loaded")
            return False, "No repository loaded"

        if self.current_commit_index >= len(self.commits) - 1:
            logger.info("Already at the latest commit")
            return False, "Already at the latest commit"

        try:
            next_index = self.current_commit_index + 1
            next_commit = self.commits[next_index]
            logger.info(f"Navigating to commit {next_index + 1}/{len(self.commits)}: {next_commit.hexsha[:7]}")
            self.repo.git.checkout(next_commit.hexsha, force=True)
            self.current_commit_index = next_index
            logger.debug(f"Successfully checked out commit: {next_commit.hexsha[:7]}")
            return True, f"Checked out commit {next_index + 1}/{len(self.commits)}: {next_commit.hexsha[:7]}"
        except GitCommandError as e:
            logger.error(f"Git error while navigating to next commit: {str(e)}")
            return False, f"Git error: {str(e)}"

    def go_to_previous_commit(self) -> tuple[bool, str]:
        """Navigate to the previous commit.

        Returns:
            Tuple of (success, message)
        """
        if not self.repo or not self.commits:
            logger.error("Cannot navigate to previous commit: no repository loaded")
            return False, "No repository loaded"

        if self.current_commit_index <= 0:
            logger.info("Already at the first commit")
            return False, "Already at the first commit"

        try:
            prev_index = self.current_commit_index - 1
            prev_commit = self.commits[prev_index]
            logger.info(f"Navigating to commit {prev_index + 1}/{len(self.commits)}: {prev_commit.hexsha[:7]}")
            self.repo.git.checkout(prev_commit.hexsha, force=True)
            self.current_commit_index = prev_index
            logger.debug(f"Successfully checked out commit: {prev_commit.hexsha[:7]}")
            return True, f"Checked out commit {prev_index + 1}/{len(self.commits)}: {prev_commit.hexsha[:7]}"
        except GitCommandError as e:
            logger.error(f"Git error while navigating to previous commit: {str(e)}")
            return False, f"Git error: {str(e)}"

    def get_current_commit(self):
        """Get the current commit object.

        Returns:
            Current commit object or None
        """
        if self.current_commit_index < 0 or self.current_commit_index >= len(self.commits):
            return None
        return self.commits[self.current_commit_index]

    def get_previous_commit(self):
        """Get the previous commit object.

        Returns:
            Previous commit object or None
        """
        if self.current_commit_index <= 0:
            return None
        return self.commits[self.current_commit_index - 1]

    def get_commit_diff(self) -> Optional[str]:
        """Get the diff between current and previous commit.

        Returns:
            Diff string or None if no previous commit
        """
        if not self.repo or self.current_commit_index <= 0:
            return None

        current = self.commits[self.current_commit_index]
        previous = self.commits[self.current_commit_index - 1]

        try:
            diff = self.repo.git.diff(previous.hexsha, current.hexsha)
            return diff
        except GitCommandError:
            return None

    def get_commit_diff_formatted(self) -> Optional[str]:
        """Get the diff between current and previous commit, formatted with colors.

        Formats diff with ANSI colors for better readability in terminal.

        Returns:
            Formatted diff string with ANSI colors or None if no previous commit
        """
        raw_diff = self.get_commit_diff()
        if not raw_diff:
            return None

        # Format diff with colors using ANSI escape codes
        formatted_lines = []
        for line in raw_diff.split('\n'):
            if line.startswith('diff --git'):
                # File header in cyan bold
                formatted_lines.append(f'\033[1;36m{line}\033[0m')
            elif line.startswith('index'):
                # Index line in cyan
                formatted_lines.append(f'\033[36m{line}\033[0m')
            elif line.startswith('---') or line.startswith('+++'):
                # File markers in white bold
                formatted_lines.append(f'\033[1;37m{line}\033[0m')
            elif line.startswith('@@'):
                # Hunk header in blue bold
                formatted_lines.append(f'\033[1;34m{line}\033[0m')
            elif line.startswith('+'):
                # Additions in green
                formatted_lines.append(f'\033[32m{line}\033[0m')
            elif line.startswith('-'):
                # Deletions in red
                formatted_lines.append(f'\033[31m{line}\033[0m')
            else:
                # Context lines unchanged
                formatted_lines.append(line)

        return '\n'.join(formatted_lines)

    def get_commit_stats(self) -> dict:
        """Get statistics about the current commit.

        Returns:
            Dictionary with commit statistics
        """
        current_commit = self.get_current_commit()
        if not current_commit:
            return {}

        full_sha = current_commit.hexsha
        stats = {
            "sha": full_sha[:7],
            "full_sha": full_sha,
            "commit_url": self.get_commit_url(full_sha),
            "author": str(current_commit.author),
            "date": current_commit.committed_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            "message": current_commit.message.strip(),
            "files_changed": [],
        }

        # Get file changes
        if self.current_commit_index > 0:
            previous = self.commits[self.current_commit_index - 1]
            diff = previous.diff(current_commit)

            for change in diff:
                change_type = "modified"
                if change.new_file:
                    change_type = "added"
                elif change.deleted_file:
                    change_type = "deleted"
                elif change.renamed:
                    change_type = "renamed"

                stats["files_changed"].append({
                    "path": change.b_path if change.b_path else change.a_path,
                    "type": change_type,
                })

        return stats

    def get_file_tree(self) -> list[str]:
        """Get a list of all files in the current commit.

        Returns:
            List of file paths relative to repo root
        """
        if not self.repo_path:
            return []

        files = []
        for root, _, filenames in os.walk(self.repo_path):
            # Skip .git directory
            if ".git" in root:
                continue

            for filename in filenames:
                file_path = Path(root) / filename
                rel_path = file_path.relative_to(self.repo_path)
                files.append(str(rel_path))

        return sorted(files)

    def read_file(self, file_path: str) -> Optional[str]:
        """Read a file from the current commit.

        Args:
            file_path: Path to file relative to repo root

        Returns:
            File contents or None if file doesn't exist
        """
        if not self.repo_path:
            return None

        full_path = self.repo_path / file_path
        if not full_path.exists():
            return None

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None

    def get_progress(self) -> tuple[int, int]:
        """Get current progress through commits.

        Returns:
            Tuple of (current_index, total_commits)
        """
        return self.current_commit_index + 1, len(self.commits)

    def get_commit_url(self, commit_sha: Optional[str] = None) -> Optional[str]:
        """Get the GitHub URL for a specific commit.

        Args:
            commit_sha: Full commit SHA (if None, uses current commit)

        Returns:
            GitHub URL for the commit or None if not a GitHub repo
        """
        if not self.repo_url:
            return None

        # Get commit SHA
        if commit_sha is None:
            current = self.get_current_commit()
            if not current:
                return None
            commit_sha = current.hexsha

        # Parse GitHub URL
        # Handle formats:
        # - https://github.com/owner/repo
        # - https://github.com/owner/repo.git
        # - git@github.com:owner/repo.git

        url = self.repo_url.rstrip('/')

        # Convert git@ format to https
        if url.startswith('git@github.com:'):
            url = url.replace('git@github.com:', 'https://github.com/')

        # Remove .git extension
        if url.endswith('.git'):
            url = url[:-4]

        # Verify it's a GitHub URL
        if 'github.com' not in url:
            return None

        # Build commit URL
        return f"{url}/tree/{commit_sha}"
