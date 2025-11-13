"""Git diff viewing screen."""

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Footer, RichLog, Static


class DiffScreen(ModalScreen):
    """Modal screen for viewing git diff."""

    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("q", "dismiss", "Close"),
    ]

    CSS = """
    DiffScreen {
        align: center middle;
    }

    #diff-container {
        width: 90%;
        height: 90%;
        border: solid green;
        background: #0a0e27;
        padding: 1;
    }

    #diff-title {
        text-style: bold;
        color: green;
        margin-bottom: 1;
    }

    #diff-content {
        height: 100%;
        background: #0a0e27;
    }

    #diff-log {
        height: 100%;
        background: #0a0e27;
    }
    """

    def __init__(self, diff_content: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.diff_content = diff_content

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with VerticalScroll(id="diff-container"):
            yield Static("Git Diff (Press ESC or q to close)", id="diff-title")
            yield RichLog(id="diff-log", wrap=False, highlight=False, markup=False)
        yield Footer()

    def on_mount(self) -> None:
        """Populate the diff log when screen mounts."""
        diff_log = self.query_one("#diff-log", RichLog)

        # Convert ANSI escape codes to Rich text
        text = Text.from_ansi(self.diff_content)
        diff_log.write(text)

    def action_dismiss(self) -> None:
        """Close the diff screen."""
        self.app.pop_screen()
