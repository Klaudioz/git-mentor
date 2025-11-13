"""Main TUI application."""

from textual.app import App
from textual.message import Message

from ..analyzer import CodeAnalyzer
from ..cache import CacheHandler
from ..git_handler import GitHandler
from ..logger import setup_logger
from ..storage import StorageHandler
from ..token_counter import should_warn_about_size
from .screens.chat import AskQuestion, ChatScreen
from .screens.commit import CommitScreen, NextCommit, PreviousCommit
from .screens.diff import DiffScreen
from .screens.setup import CloneRepository, SetupScreen

logger = setup_logger()


class CommitTeacherApp(App):
    """Main application for Commit Teacher."""

    CSS = """
    Screen {
        background: #0a0e27;
    }
    """

    SCREENS = {
        "setup": SetupScreen,
        "commit": CommitScreen,
        "chat": ChatScreen,
    }

    def __init__(self, initial_repo=None, is_local=False, use_cache=True, auto_resume=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.info("Initializing CommitTeacherApp")
        self.git_handler = GitHandler()
        self.analyzer = None
        self.storage = None
        self.cache = CacheHandler()
        self.architecture = None
        self.last_explanation = None
        self.initial_repo = initial_repo
        self.is_local = is_local
        self.use_cache = use_cache
        self.auto_resume = auto_resume

    def on_mount(self) -> None:
        """Handle app mount."""
        logger.info("Application mounted")

        # If initial repo is provided, skip setup and load directly
        if self.initial_repo:
            logger.info(f"Initial repository provided: {self.initial_repo}")
            # Push commit screen first (it will show loading state)
            self.push_screen("commit")
            # Clone and analyze repository
            self.call_later(self._load_initial_repo)
        else:
            logger.info("No initial repository, showing setup screen")
            self.push_screen("setup")

    async def _load_initial_repo(self):
        """Load the initial repository provided via CLI."""
        from .screens.setup import CloneRepository

        # Simulate the CloneRepository message
        message = CloneRepository(self.initial_repo, is_local=self.is_local)
        await self.on_clone_repository(message)

    async def on_clone_repository(self, message: CloneRepository) -> None:
        """Handle repository cloning or loading."""
        action = "load" if message.is_local else "clone"
        logger.info(f"User requested to {action} repository: {message.repo_url}")

        # Check if we're on setup screen or commit screen
        current_screen = self.screen
        is_setup_screen = hasattr(current_screen, 'query') and len(current_screen.query("#status")) > 0

        if is_setup_screen:
            status_widget = current_screen.query_one("#status")
        else:
            # We're loading from CLI on commit screen
            status_widget = None

        def update_status(msg: str):
            """Update status on appropriate screen."""
            if status_widget:
                status_widget.update(msg)
            else:
                # Update commit screen status bar
                try:
                    commit_screen = self.get_screen("commit")
                    commit_screen.update_status(msg)
                except:
                    logger.info(msg)

        # Load or clone repository
        if message.is_local:
            update_status("Loading local repository...")
            success, msg = self.git_handler.load_repository(message.repo_url)
            # For local repos, set the repo_url to the path for cache purposes
            if success:
                self.git_handler.repo_url = message.repo_url
        else:
            update_status("Cloning repository...")
            success, msg = self.git_handler.clone_repository(message.repo_url)

        if not success:
            logger.error(f"Failed to clone repository: {msg}")
            update_status(f"Error: {msg}")
            if status_widget:
                status_widget.add_class("error")
            return

        update_status("Repository cloned! Checking size...")
        if status_widget:
            status_widget.add_class("success")

        # Check repository size
        should_warn, warning_message = should_warn_about_size(self.git_handler.repo_path)
        if should_warn:
            logger.warning("Repository exceeds size threshold")
            update_status(warning_message.split('\n')[0])
            if status_widget:
                status_widget.add_class("error")
            # In a real implementation, you might want to show a modal dialog
            # For now, we just log and continue
            update_status("⚠️  Large repository detected - continuing anyway...")

        update_status("Going to first commit...")

        # Initialize analyzer and storage
        try:
            logger.info("Initializing analyzer and storage")
            self.analyzer = CodeAnalyzer()

            # Extract repository name differently for local vs remote
            if message.is_local:
                from pathlib import Path
                repo_name = Path(message.repo_url).expanduser().resolve().name
            else:
                repo_name = message.repo_url.rstrip("/").split("/")[-1]
                if repo_name.endswith(".git"):
                    repo_name = repo_name[:-4]

            self.storage = StorageHandler(repo_name)

            # Load cache for this repository (if enabled)
            if self.use_cache:
                cache_exists = self.cache.load_cache(repo_name, message.repo_url)
                if cache_exists:
                    logger.info("Existing cache found for repository")
            else:
                logger.info("Cache disabled via --no-cache flag")
        except Exception as e:
            logger.error(f"Failed to initialize analyzer/storage: {str(e)}", exc_info=True)
            update_status(f"Error initializing: {str(e)}")
            if status_widget:
                status_widget.add_class("error")
            return

        # Go to first commit
        success, msg = self.git_handler.go_to_first_commit()
        if not success:
            logger.error(f"Failed to go to first commit: {msg}")
            update_status(f"Error: {msg}")
            if status_widget:
                status_widget.add_class("error")
            return

        # Update cache with total commit count and check for resume
        total_commits = len(self.git_handler.commits)
        commit_info = self.cache.update_total_commits(total_commits)

        # Check if we should resume from a previous position
        last_index, cached_total = self.cache.get_last_position()
        should_resume = (
            self.use_cache  # Cache must be enabled
            and (self.auto_resume or (last_index >= 0))  # Explicit resume or has previous position
            and self.cache.has_cache_for_repo()
            and last_index < total_commits
        )

        if should_resume:
            logger.info(f"Resuming from commit {last_index + 1} of {total_commits}")
            update_status(f"Resuming from commit {last_index + 1} of {total_commits}...")

            # Navigate to the last viewed commit
            for _ in range(last_index):
                success, msg = self.git_handler.go_to_next_commit()
                if not success:
                    logger.warning(f"Failed to resume to commit {last_index + 1}: {msg}")
                    break

            # Load cached architecture if available
            first_commit_sha = self.git_handler.commits[0].hexsha[:7]
            cached_explanation = self.cache.get_commit_analysis(first_commit_sha)
            if cached_explanation:
                # Extract architecture from cached first commit
                if "## Architecture Overview" in cached_explanation or "# Architecture" in cached_explanation:
                    self.architecture = cached_explanation.split("# Initial Commit")[1].strip() if "# Initial Commit" in cached_explanation else cached_explanation
                else:
                    # Fallback to stored architecture file
                    self.architecture = self.storage.load_architecture()
            else:
                self.architecture = self.storage.load_architecture()

            # Get current commit explanation from cache
            current_commit_sha = self.git_handler.commits[last_index].hexsha[:7]
            cached_current = self.cache.get_commit_analysis(current_commit_sha)
            if cached_current:
                self.last_explanation = cached_current
            else:
                self.last_explanation = "No cached explanation available for this commit."
        else:
            update_status("Analyzing initial architecture...")
            # Analyze initial architecture only if not resuming
            await self.analyze_first_commit()

        # Save initial position to cache (if enabled)
        if self.use_cache:
            current, total = self.git_handler.get_progress()
            self.cache.save_last_position(current - 1, total)

        # Switch to commit screen or update if already on it
        if is_setup_screen:
            # Coming from setup screen - switch to commit screen
            logger.info("Switching to commit screen")
            self.push_screen("commit")
        else:
            # Already on commit screen (CLI mode) - just update it
            logger.info("Updating commit screen")
            self.update_commit_screen()

    async def analyze_first_commit(self) -> None:
        """Analyze the first commit and create architecture document."""
        logger.info("Analyzing first commit")

        # Check cache first
        first_commit_sha = self.git_handler.commits[0].hexsha[:7]
        cached_explanation = self.cache.get_commit_analysis(first_commit_sha)

        if cached_explanation:
            logger.info("Using cached analysis for first commit")
            self.last_explanation = cached_explanation

            # Extract architecture from cached explanation
            if "# Initial Commit" in cached_explanation:
                self.architecture = cached_explanation.split("# Initial Commit")[1].strip()
            else:
                self.architecture = self.storage.load_architecture()
            return

        # No cache - perform analysis
        file_tree = self.git_handler.get_file_tree()

        # Read important files (limit to avoid token overload)
        important_extensions = ['.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c', '.h', '.md', '.txt', '.json', '.yaml', '.yml', '.toml']
        file_contents = {}

        for file_path in file_tree[:20]:  # Limit to first 20 files
            if any(file_path.endswith(ext) for ext in important_extensions):
                content = self.git_handler.read_file(file_path)
                if content and len(content) < 10000:  # Skip very large files
                    file_contents[file_path] = content

        logger.info(f"Analyzing {len(file_contents)} files from first commit")

        # Analyze architecture
        self.architecture = self.analyzer.analyze_initial_architecture(file_tree, file_contents)

        # Save architecture
        self.storage.save_architecture(self.architecture)

        # Set explanation
        self.last_explanation = f"""# Initial Commit

This is the first commit of the project. The architecture has been analyzed and documented.

{self.architecture}
"""

        # Cache the analysis (if enabled)
        if self.use_cache:
            self.cache.save_commit_analysis(first_commit_sha, self.last_explanation)
            logger.info("First commit analysis complete and cached")
        else:
            logger.info("First commit analysis complete (caching disabled)")

    async def on_next_commit(self, message: NextCommit) -> None:
        """Handle next commit navigation."""
        logger.info("User requested next commit")
        commit_screen = self.get_screen("commit")

        # Update status
        commit_screen.update_status("Navigating to next commit...")

        # Go to next commit
        success, msg = self.git_handler.go_to_next_commit()

        if not success:
            logger.warning(f"Cannot go to next commit: {msg}")
            # Show message in explanation
            commit_screen.update_explanation(f"**Notice:** {msg}")
            commit_screen.update_status("Ready")
            return

        # Update status
        commit_screen.update_status("Analyzing commit with AI...")

        # Analyze commit
        await self.analyze_current_commit()

        # Update screen
        self.update_commit_screen()

        # Save current position to cache (if enabled)
        if self.use_cache:
            current, total = self.git_handler.get_progress()
            self.cache.save_last_position(current - 1, total)  # current is 1-based, index is 0-based

        # Update status
        commit_screen.update_status("Ready")

    async def on_previous_commit(self, message: PreviousCommit) -> None:
        """Handle previous commit navigation."""
        logger.info("User requested previous commit")
        commit_screen = self.get_screen("commit")

        # Update status
        commit_screen.update_status("Navigating to previous commit...")

        # Go to previous commit
        success, msg = self.git_handler.go_to_previous_commit()

        if not success:
            logger.warning(f"Cannot go to previous commit: {msg}")
            # Show message in explanation
            commit_screen.update_explanation(f"**Notice:** {msg}")
            commit_screen.update_status("Ready")
            return

        # Update status
        commit_screen.update_status("Loading commit (checking cache)...")

        # Analyze commit (cache will be checked automatically)
        await self.analyze_current_commit()

        # Update screen
        self.update_commit_screen()

        # Save current position to cache (if enabled)
        if self.use_cache:
            current, total = self.git_handler.get_progress()
            self.cache.save_last_position(current - 1, total)  # current is 1-based, index is 0-based

        # Update status
        commit_screen.update_status("Ready")

    async def analyze_current_commit(self) -> None:
        """Analyze the current commit."""
        commit_stats = self.git_handler.get_commit_stats()
        commit_sha = commit_stats.get("sha", "")

        # Check cache first (if enabled)
        if self.use_cache:
            cached_explanation = self.cache.get_commit_analysis(commit_sha)
            if cached_explanation:
                logger.info(f"Using cached analysis for commit {commit_sha}")
                self.last_explanation = cached_explanation

                # Check if cached explanation has architecture update
                if "## Updated Architecture" in cached_explanation:
                    arch_section = cached_explanation.split("## Updated Architecture")[1].strip()
                    if "NO ARCHITECTURE UPDATE NEEDED" not in arch_section:
                        self.architecture = arch_section
                        self.storage.update_architecture(self.architecture)
                return

        # No cache - perform AI analysis
        diff = self.git_handler.get_commit_diff()

        # Get explanation and potential architecture update
        explanation, updated_arch = self.analyzer.analyze_commit_changes(
            commit_stats,
            diff,
            self.architecture
        )

        self.last_explanation = explanation

        # Update architecture if needed
        if updated_arch:
            self.architecture = updated_arch
            self.storage.update_architecture(self.architecture)

        # Cache the analysis (if enabled)
        if self.use_cache:
            self.cache.save_commit_analysis(commit_sha, explanation)
            logger.info(f"Commit {commit_sha} analysis complete and cached")
        else:
            logger.info(f"Commit {commit_sha} analysis complete (caching disabled)")

    def update_commit_screen(self) -> None:
        """Update the commit screen with current information."""
        try:
            commit_screen = self.get_screen("commit")

            # Update progress
            current, total = self.git_handler.get_progress()
            commit_screen.update_progress(current, total)

            # Update commit info
            commit_stats = self.git_handler.get_commit_stats()
            commit_screen.update_commit_info(commit_stats)

            # Update explanation
            commit_screen.update_explanation(self.last_explanation or "No explanation available")

            # Update cache status
            commit_sha = commit_stats.get("sha", "")
            is_cached = self.cache.get_commit_analysis(commit_sha) is not None
            cache_stats = self.cache.get_cache_stats()
            commit_screen.update_cache_status(is_cached, cache_stats)
        except Exception as e:
            logger.debug(f"Could not update commit screen (probably not mounted yet): {e}")

    async def on_ask_question(self, message: AskQuestion) -> None:
        """Handle question from chat."""
        chat_screen = self.get_screen("chat")

        # Show thinking message
        chat_screen.add_message("assistant", "Thinking...")

        # Prepare context
        commit_stats = self.git_handler.get_commit_stats()
        context = {
            "architecture": self.architecture,
            "commit_sha": commit_stats.get("sha", "unknown"),
            "commit_message": commit_stats.get("message", "unknown"),
            "files_changed": commit_stats.get("files_changed", []),
            "last_explanation": self.last_explanation,
        }

        # Get answer
        answer = self.analyzer.answer_question(message.question, context)

        # Remove thinking message and add real answer
        messages_container = chat_screen.query_one("#messages-container")
        messages_container.remove_children()

        # Re-add all messages with the new answer
        chat_screen.add_message("user", message.question)
        chat_screen.add_message("assistant", answer)

    def show_diff_screen(self) -> None:
        """Show the git diff in a modal screen."""
        try:
            # Use formatted diff with dunk for rich, colored output
            diff_content = self.git_handler.get_commit_diff_formatted()
            if not diff_content or diff_content.strip() == "":
                diff_content = "No diff available for this commit."
            diff_screen = DiffScreen(diff_content)
            self.push_screen(diff_screen)
        except Exception as e:
            logger.error(f"Failed to show diff: {str(e)}", exc_info=True)
            # Show error in a simple diff screen
            diff_screen = DiffScreen(f"Error loading diff: {str(e)}")
            self.push_screen(diff_screen)
