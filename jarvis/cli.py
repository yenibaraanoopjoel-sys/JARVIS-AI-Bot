"""JARVIS terminal entry point for PowerShell."""
import logging
from uuid import uuid4
import typer
from rich.console import Console
from rich.panel import Panel
from .config import get_settings
from .logging_config import configure_logging
from .storage import ConversationStore
from .brain.conversation import ConversationEngine
from .brain.provider import ProviderError
from .voice.speech import VoiceEngine, VoiceError

app = typer.Typer(help="JARVIS personal AI assistant")
console = Console()
log = logging.getLogger(__name__)

@app.command()
def chat(voice: bool = typer.Option(False, "--voice", help="Enable microphone input and spoken responses")) -> None:
    """Start persistent text chat or voice-enabled chat in the terminal."""
    settings = get_settings()
    configure_logging(settings)
    store = ConversationStore(settings)
    engine = ConversationEngine(settings, store)
    voice_engine = VoiceEngine(settings) if voice else None
    conversation_id = str(uuid4())
    store.ensure_conversation(conversation_id)
    console.print(Panel.fit(f"{settings.name} online | conversation {conversation_id[:8]}"))
    console.print("Use /help for commands and /exit to quit.")
    try:
        while True:
            try:
                if voice_engine:
                    console.print("Listening...")
                    user_text = voice_engine.listen_once()
                    console.print(f"You: {user_text}")
                else:
                    user_text = console.input("You > ").strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\nJARVIS session ended.")
                break
            except VoiceError as exc:
                console.print(f"Voice input error: {exc}")
                continue
            if not user_text:
                continue
            command = user_text.lower().strip()
            if command in {"/exit", "/quit", "goodbye jarvis", "shutdown jarvis"}:
                console.print("JARVIS shutting down. Goodbye, boss.")
                break
            if command == "/help":
                console.print("Commands: /help, /new, /history, /exit. Voice mode: jarvis chat --voice")
                continue
            if command == "/new":
                conversation_id = engine.new_conversation_id()
                console.print("Started a new conversation.")
                continue
            if command == "/history":
                for conversation in store.list_conversations():
                    console.print(f"{conversation.updated_at} {conversation.id[:8]} {conversation.title}")
                continue
            try:
                with console.status("JARVIS is thinking...", spinner="dots"):
                    response = engine.ask(conversation_id, user_text, source="voice" if voice else "text")
                console.print(Panel(response, title="JARVIS"))
                if voice_engine:
                    try:
                        voice_engine.speak(response)
                    except VoiceError as exc:
                        console.print(f"Speech output unavailable: {exc}")
            except ProviderError as exc:
                console.print(f"AI error: {exc}")
                log.warning("AI provider request failed: %s", exc)
            except Exception:
                log.exception("Unexpected chat error")
                console.print("Unexpected error. Check the local logs.")
    finally:
        store.close()

@app.command()
def doctor() -> None:
    """Check core configuration and optional subsystems."""
    settings = get_settings()
    configure_logging(settings)
    console.print(f"JARVIS name: {settings.name}")
    console.print(f"Database: {settings.database_url}")
    console.print(f"AI API key configured: {bool(settings.openai_api_key)}")
    for name, module in [("AI SDK", "openai"), ("Voice", "speech_recognition"), ("Vision", "cv2")]:
        try:
            __import__(module)
            console.print(f"{name}: installed")
        except ImportError:
            console.print(f"{name}: not installed; install the corresponding optional extra")

if __name__ == "__main__":
    app()
