"""
Cache handler for storing and retrieving commit analyses.

This module provides persistent caching of LLM-generated commit explanations
to avoid redundant API calls and enable session resumption.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class CacheHandler:
    """Handles caching of commit analyses and session state."""

    def __init__(self, cache_dir: str = "data"):
        """
        Initialize the cache handler.

        Args:
            cache_dir: Directory where cache files will be stored
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file: Optional[Path] = None
        self.cache_data: dict = {}
        self.repo_name: str = ""
        logger.info(f"Initialized CacheHandler with directory: {cache_dir}")

    def load_cache(self, repo_name: str, repo_url: str = "") -> bool:
        """
        Load existing cache for a repository or create a new one.

        Args:
            repo_name: Name of the repository
            repo_url: URL of the repository (for metadata)

        Returns:
            True if existing cache was loaded, False if new cache created
        """
        self.repo_name = repo_name
        self.cache_file = self.cache_dir / f"{repo_name}.cache.json"

        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.cache_data = json.load(f)
                logger.info(f"Loaded existing cache from {self.cache_file}")
                logger.info(
                    f"Cache contains {len(self.cache_data.get('commits', {}))} cached commits"
                )
                return True
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(
                    f"Failed to load cache file {self.cache_file}: {e}. Starting fresh."
                )
                self._initialize_cache(repo_name, repo_url)
                return False
        else:
            logger.info(f"No existing cache found. Creating new cache for {repo_name}")
            self._initialize_cache(repo_name, repo_url)
            return False

    def _initialize_cache(self, repo_name: str, repo_url: str) -> None:
        """Initialize a new cache structure."""
        self.cache_data = {
            "repo_name": repo_name,
            "repo_url": repo_url,
            "last_commit_index": -1,
            "total_commits": 0,
            "cache_version": "1.0",
            "created_at": datetime.now().isoformat(),
            "commits": {},
        }
        logger.debug(f"Initialized new cache structure for {repo_name}")

    def save_commit_analysis(
        self,
        commit_sha: str,
        explanation: str,
        architecture_version: Optional[str] = None,
    ) -> None:
        """
        Save a commit analysis to the cache.

        Args:
            commit_sha: The commit SHA (short or full)
            explanation: The AI-generated explanation markdown
            architecture_version: Optional snapshot or hash of architecture at this point
        """
        if "commits" not in self.cache_data:
            self.cache_data["commits"] = {}

        self.cache_data["commits"][commit_sha] = {
            "sha": commit_sha,
            "explanation": explanation,
            "architecture_version": architecture_version,
            "analyzed_at": datetime.now().isoformat(),
            "cached": True,
        }

        self._save_to_disk()
        logger.info(f"Cached analysis for commit {commit_sha}")

    def get_commit_analysis(self, commit_sha: str) -> Optional[str]:
        """
        Retrieve a cached commit analysis.

        Args:
            commit_sha: The commit SHA to look up

        Returns:
            The cached explanation markdown, or None if not found
        """
        commits = self.cache_data.get("commits", {})
        if commit_sha in commits:
            logger.info(f"Cache hit for commit {commit_sha}")
            return commits[commit_sha]["explanation"]

        logger.debug(f"Cache miss for commit {commit_sha}")
        return None

    def save_last_position(self, commit_index: int, total_commits: int) -> None:
        """
        Save the user's last position in the commit history.

        Args:
            commit_index: The index of the last viewed commit (0-based)
            total_commits: Total number of commits in the repository
        """
        self.cache_data["last_commit_index"] = commit_index
        self.cache_data["total_commits"] = total_commits
        self._save_to_disk()
        logger.debug(f"Saved position: {commit_index + 1} of {total_commits}")

    def get_last_position(self) -> tuple[int, int]:
        """
        Get the user's last position in the commit history.

        Returns:
            Tuple of (last_commit_index, total_commits)
        """
        index = self.cache_data.get("last_commit_index", -1)
        total = self.cache_data.get("total_commits", 0)
        return index, total

    def get_cache_stats(self) -> dict:
        """
        Get statistics about the cache.

        Returns:
            Dictionary with cache statistics
        """
        commits_cached = len(self.cache_data.get("commits", {}))
        total_commits = self.cache_data.get("total_commits", 0)
        coverage = (
            (commits_cached / total_commits * 100) if total_commits > 0 else 0
        )

        return {
            "commits_cached": commits_cached,
            "total_commits": total_commits,
            "coverage_percent": round(coverage, 1),
            "last_position": self.cache_data.get("last_commit_index", -1) + 1,
            "repo_name": self.cache_data.get("repo_name", ""),
        }

    def has_cache_for_repo(self) -> bool:
        """Check if there's meaningful cached data for the current repository."""
        return len(self.cache_data.get("commits", {})) > 0

    def _save_to_disk(self) -> None:
        """Persist the cache data to disk."""
        if not self.cache_file:
            logger.warning("No cache file path set, cannot save")
            return

        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache_data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved cache to {self.cache_file}")
        except IOError as e:
            logger.error(f"Failed to save cache to {self.cache_file}: {e}")

    def update_total_commits(self, total_commits: int) -> dict:
        """
        Update the total commit count and check for new commits.

        Args:
            total_commits: The current total number of commits in the repository

        Returns:
            Dictionary with information about new commits
        """
        old_total = self.cache_data.get("total_commits", 0)
        self.cache_data["total_commits"] = total_commits

        new_commits_count = max(0, total_commits - old_total)

        if new_commits_count > 0:
            logger.info(f"Found {new_commits_count} new commits since last session")

        self._save_to_disk()

        return {
            "new_commits": new_commits_count,
            "old_total": old_total,
            "new_total": total_commits,
        }
