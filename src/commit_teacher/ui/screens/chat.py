"""Chat screen for Q&A."""

from textual.app import ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Markdown, Static


class ChatScreen(Screen):
    """Screen for chatting about the code."""

    BINDINGS = [
        ("escape", "close_chat", "Back"),
    ]

    CSS = """
    ChatScreen {
        layout: vertical;
    }

    #chat-header {
        height: auto;
        border: solid blue;
        padding: 1;
        text-align: center;
        text-style: bold;
    }

    #chat-history {
        height: 1fr;
        border: solid green;
        padding: 1;
    }

    #chat-input-container {
        height: auto;
        border: solid yellow;
        padding: 1;
    }

    .message {
        margin: 1 0;
        padding: 1;
        border: solid gray;
    }

    .user-message {
        background: #1a1a2e;
    }

    .assistant-message {
        background: #16213e;
    }

    Input {
        width: 100%;
    }

    Button {
        width: 100%;
        margin-top: 1;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.messages = []

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()

        yield Static("💬 Ask Questions About the Code", id="chat-header")

        with VerticalScroll(id="chat-history"):
            yield Container(id="messages-container")

        with Vertical(id="chat-input-container"):
            yield Label("Your question:")
            yield Input(
                placeholder="Ask anything about the code...",
                id="question-input"
            )
            yield Button("Send", variant="primary", id="send-btn")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "send-btn":
            self.send_message()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        if event.input.id == "question-input":
            self.send_message()

    def send_message(self) -> None:
        """Send a chat message."""
        input_widget = self.query_one("#question-input", Input)
        question = input_widget.value.strip()

        if not question:
            return

        # Clear input
        input_widget.value = ""

        # Add user message
        self.add_message("user", question)

        # Request answer from app
        self.app.post_message(AskQuestion(question))

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the chat history."""
        messages_container = self.query_one("#messages-container", Container)

        message_class = "user-message" if role == "user" else "assistant-message"
        prefix = "You" if role == "user" else "Assistant"

        message_widget = Markdown(
            f"**{prefix}:**\n\n{content}",
            classes=f"message {message_class}"
        )

        messages_container.mount(message_widget)

        # Scroll to bottom
        chat_history = self.query_one("#chat-history", VerticalScroll)
        chat_history.scroll_end(animate=False)

    def action_close_chat(self) -> None:
        """Close the chat screen."""
        self.app.pop_screen()


class AskQuestion(Message):
    """Message to request an answer to a question."""

    def __init__(self, question: str):
        super().__init__()
        self.question = question
