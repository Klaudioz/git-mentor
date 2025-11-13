"""Commit viewing screen."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Markdown, Static


class CommitScreen(Screen):
    """Screen for viewing commit information and explanations."""

    BINDINGS = [
        ("n", "next_commit", "Next commit"),
        ("p", "previous_commit", "Previous commit"),
        ("d", "show_diff", "Git diff"),
        ("c", "toggle_chat", "Chat"),
        ("q", "quit_app", "Quit"),
    ]

    CSS = """
    CommitScreen {
        layout: grid;
        grid-size: 2 4;
        grid-columns: 1fr 1fr;
        grid-rows: auto 1fr auto auto;
    }

    #header-container {
        column-span: 2;
        height: auto;
        border: solid blue;
        padding: 1;
    }

    #progress {
        text-style: bold;
        color: blue;
    }

    #cache-status {
        color: #888;
        margin-top: 1;
    }

    .cache-hit {
        color: green;
        text-style: bold;
    }

    .cache-miss {
        color: yellow;
        text-style: bold;
    }

    #commit-info-panel {
        border: solid green;
        padding: 1;
        height: 100%;
    }

    #explanation-panel {
        border: solid yellow;
        padding: 1;
        height: 100%;
    }

    #controls {
        column-span: 2;
        height: auto;
        layout: horizontal;
        padding: 1;
    }

    #controls Button {
        margin: 0 1;
    }

    #status-bar {
        column-span: 2;
        height: 1;
        background: #1a1a2e;
        color: #16c9f5;
        padding: 0 1;
    }

    .panel-title {
        text-style: bold;
        margin-bottom: 1;
    }

    VerticalScroll {
        height: 100%;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chat_visible = False

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()

        with Container(id="header-container"):
            yield Static("Loading...", id="progress")
            yield Markdown("", id="commit-summary")
            yield Static("", id="cache-status")

        with VerticalScroll(id="commit-info-panel"):
            yield Static("Commit Information", classes="panel-title")
            yield Markdown("", id="commit-details")

        with VerticalScroll(id="explanation-panel"):
            yield Static("Explanation", classes="panel-title")
            yield Markdown("", id="explanation")

        with Horizontal(id="controls"):
            yield Button("Next Commit", variant="primary", id="next-btn")
            yield Button("Chat", variant="default", id="chat-btn")
            yield Button("Quit", variant="error", id="quit-btn")

        yield Static("Ready", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Handle screen mount."""
        # Request the app to update this screen with current commit info
        self.app.update_commit_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "next-btn":
            self.action_next_commit()
        elif event.button.id == "chat-btn":
            self.action_toggle_chat()
        elif event.button.id == "quit-btn":
            self.action_quit_app()

    def action_next_commit(self) -> None:
        """Navigate to next commit."""
        self.app.post_message(NextCommit())

    def action_previous_commit(self) -> None:
        """Navigate to previous commit."""
        self.app.post_message(PreviousCommit())

    def action_toggle_chat(self) -> None:
        """Toggle chat interface."""
        self.app.push_screen("chat")

    def action_quit_app(self) -> None:
        """Quit the application."""
        self.app.exit()

    def action_show_diff(self) -> None:
        """Show git diff for current commit."""
        self.app.show_diff_screen()

    def update_progress(self, current: int, total: int) -> None:
        """Update progress indicator."""
        progress_widget = self.query_one("#progress", Static)
        progress_widget.update(f"Commit {current} of {total}")

    def update_commit_info(self, stats: dict) -> None:
        """Update commit information display."""
        summary_widget = self.query_one("#commit-summary", Markdown)
        details_widget = self.query_one("#commit-details", Markdown)

        # Create clickable SHA link if URL is available
        full_sha = stats.get('full_sha', stats.get('sha', 'unknown'))
        commit_url = stats.get('commit_url')

        if commit_url:
            sha_display = f"[{full_sha}]({commit_url})"
        else:
            sha_display = full_sha

        summary_widget.update(f"**SHA:** {sha_display} | **Date:** {stats.get('date', 'unknown')}")

        details_md = f"""
**Author:** {stats.get('author', 'unknown')}

**Message:**
{stats.get('message', 'No message')}

**Files Changed:**
"""
        for file in stats.get('files_changed', []):
            details_md += f"\n- `{file['path']}` ({file['type']})"

        details_widget.update(details_md)

    def update_explanation(self, explanation: str) -> None:
        """Update explanation display."""
        explanation_widget = self.query_one("#explanation", Markdown)
        explanation_widget.update(explanation)

    def update_status(self, status: str) -> None:
        """Update status bar."""
        status_widget = self.query_one("#status-bar", Static)
        status_widget.update(status)

    def update_cache_status(self, is_cached: bool, stats: dict = None) -> None:
        """Update cache status display."""
        cache_widget = self.query_one("#cache-status", Static)

        if stats:
            coverage = stats.get("coverage_percent", 0)
            cached_count = stats.get("commits_cached", 0)
            total = stats.get("total_commits", 0)

            status_text = f"Cache: {cached_count}/{total} ({coverage}%)"
            if is_cached:
                status_text += " | [CACHED]"
                cache_widget.remove_class("cache-miss")
                cache_widget.add_class("cache-hit")
            else:
                status_text += " | [ANALYZED]"
                cache_widget.remove_class("cache-hit")
                cache_widget.add_class("cache-miss")

            cache_widget.update(status_text)
        else:
            cache_widget.update("")



class NextCommit(Message):
    """Message to request next commit."""
    pass


class PreviousCommit(Message):
    """Message to request previous commit."""
    pass
