"""Setup screen for repository configuration."""

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Button, Header, Input, Label, Static


class SetupScreen(Screen):
    """Screen for setting up the repository."""

    CSS = """
    SetupScreen {
        align: center middle;
    }

    #setup-container {
        width: 80;
        height: auto;
        border: solid green;
        padding: 2;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: green;
        margin-bottom: 1;
    }

    #description {
        text-align: center;
        margin-bottom: 2;
    }

    Input {
        margin: 1 0;
    }

    Button {
        width: 100%;
        margin-top: 1;
    }

    #status {
        text-align: center;
        margin-top: 1;
        height: 3;
    }

    .error {
        color: red;
    }

    .success {
        color: green;
    }
    """

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        with Container(id="setup-container"):
            with Vertical():
                yield Static("🎓 Commit Teacher", id="title")
                yield Static(
                    "Learn code through commit history\n"
                    "Enter a GitHub repository URL to begin",
                    id="description"
                )
                yield Label("Repository URL:")
                yield Input(
                    placeholder="https://github.com/user/repo",
                    id="repo-input"
                )
                yield Button("Clone Repository", variant="primary", id="clone-btn")
                yield Static("", id="status")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "clone-btn":
            self.clone_repository()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        if event.input.id == "repo-input":
            self.clone_repository()

    def clone_repository(self) -> None:
        """Clone the repository and navigate to main screen."""
        input_widget = self.query_one("#repo-input", Input)
        status_widget = self.query_one("#status", Static)

        repo_url = input_widget.value.strip()

        if not repo_url:
            status_widget.update("Please enter a repository URL")
            status_widget.add_class("error")
            return

        status_widget.update("Cloning repository...")
        status_widget.remove_class("error")
        status_widget.remove_class("success")

        # Send message to app to handle cloning
        self.app.post_message(CloneRepository(repo_url))


class CloneRepository(Message):
    """Message to request repository cloning."""

    def __init__(self, repo_url: str):
        super().__init__()
        self.repo_url = repo_url
