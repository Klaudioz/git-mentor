"""Storage handler for architecture documentation."""

from pathlib import Path
from typing import Optional

from .logger import setup_logger

logger = setup_logger()


class StorageHandler:
    """Handles storage of architecture documentation."""

    def __init__(self, repo_name: str, data_dir: str = "data"):
        """Initialize storage handler.

        Args:
            repo_name: Name of the repository
            data_dir: Directory to store data files
        """
        self.repo_name = repo_name
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.storage_file = self.data_dir / f"{repo_name}.architecture.md"
        logger.info(f"Initialized StorageHandler for {repo_name}, file: {self.storage_file}")

    def save_architecture(self, content: str) -> bool:
        """Save architecture documentation.

        Args:
            content: Architecture documentation content

        Returns:
            True if successful
        """
        logger.info(f"Saving architecture to {self.storage_file}")
        try:
            with open(self.storage_file, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Successfully saved architecture ({len(content)} bytes)")
            return True
        except Exception as e:
            logger.error(f"Failed to save architecture: {str(e)}", exc_info=True)
            return False

    def load_architecture(self) -> Optional[str]:
        """Load architecture documentation.

        Returns:
            Architecture documentation or None if file doesn't exist
        """
        if not self.storage_file.exists():
            logger.debug(f"Architecture file does not exist: {self.storage_file}")
            return None

        logger.info(f"Loading architecture from {self.storage_file}")
        try:
            with open(self.storage_file, "r", encoding="utf-8") as f:
                content = f.read()
            logger.info(f"Successfully loaded architecture ({len(content)} bytes)")
            return content
        except Exception as e:
            logger.error(f"Failed to load architecture: {str(e)}", exc_info=True)
            return None

    def architecture_exists(self) -> bool:
        """Check if architecture documentation exists.

        Returns:
            True if architecture file exists
        """
        return self.storage_file.exists()

    def update_architecture(self, new_content: str) -> bool:
        """Update architecture documentation.

        Args:
            new_content: New architecture documentation content

        Returns:
            True if successful
        """
        logger.info("Updating architecture documentation")
        return self.save_architecture(new_content)
