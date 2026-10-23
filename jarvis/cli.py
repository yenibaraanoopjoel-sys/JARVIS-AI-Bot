"""JARVIS terminal entry point for PowerShell."""
from __future__ import annotations

import getpass
import logging
from uuid import uuid4

import typer
from rich.console import Console
from rich.panel import Panel

from .brain.conversation import ConversationEngine
from .brain.provider import ProviderError
from .config import get_settings
from .logging_config import configure_logging
from .security.face_profiles import FaceProfileStore
from .security.owner_auth import OwnerAuthError, OwnerAuthenticator
from .security.permissions import PermissionManager
from .storage import ConversationStore
from .tools.desktop import DesktopTools
from .vision.recognition import FaceRecognitionService, VisionError
from .voice.commands import (
    LocalCommand,
    current_date_response,
    current_time_response,
    parse_local_command,
)
from .voice.speech import VoiceEngine, VoiceError

app = typer.Typer(help="JARVIS personal AI assistant", no_args_is_help=True)
auth_app = typer.Typer(help="Configure local owner authentication", no_args_is_help=True)
face_app = typer.Typer(help="Consent-based local face identification", no_args_is_help=True)
app.add_typer(auth_app, name="auth")
app.add_typer(face_app, name="face")
console = Console()
log = logging.getLogger(__name__)


def _owner_authenticator(settings) -> OwnerAuthenticator:
    return OwnerAuthenticator(settings.data_dir / "owner_auth.json")


def _speak_response(voice_engine: VoiceEngine | None, response: str) -> None:
    if voice_engine is None:
        return
    try:
        voice_engine.speak(response)
    except VoiceError as exc:
        console.print(f"[yellow]Speech output unavailable:[/yellow] {exc}")


def _handle_local_command(
    parsed: LocalCommand,
    settings,
    store: ConversationStore,
    desktop: DesktopTools,
    authenticator: OwnerAuthenticator,
    owner_authenticated: bool,
    voice_engine: VoiceEngine | None,
) -> tuple[str, bool]:
    """Execute only deterministic, explicitly supported local actions."""
    if parsed.action == "current_time":
        return current_time_response(), owner_authenticated
    if parsed.action == "current_date":
        return current_date_response(), owner_authenticated

    if parsed.action == "identify_face":
        try:
            face_store = FaceProfileStore(store)
            match = FaceRecognitionService(settings, face_store).identify_from_camera(seconds=15)
            if match is None:
                return (
                    "I couldn't match a face to an active enrolled profile. No identity was verified.",
                    owner_authenticated,
                )
            return (
                f"I recognize {match.display_name}. Face matching is only an identification signal, "
                "not proof of owner authentication.",
                owner_authenticated,
            )
        except (VisionError, PermissionError, ValueError) as exc:
            return f"Face identification could not complete: {exc}", owner_authenticated

    if parsed.action == "open_application":
        if not settings.allow_app_launch:
            return (
                "Application launching is disabled. Set JARVIS_ALLOW_APP_LAUNCH=true in your local .env "
                "file and restart JARVIS to enable the allowlisted applications.",
                owner_authenticated,
            )
        if not owner_authenticated:
            if not authenticator.is_configured:
                return (
                    "Owner actions are locked. Run 'jarvis auth setup' in PowerShell to configure an owner "
                    "PIN, then restart JARVIS.",
                    owner_authenticated,
                )
            try:
                pin = getpass.getpass("Owner PIN required for this action: ")
            except (EOFError, KeyboardInterrupt):
                return "Owner authentication was cancelled. No application was opened.", owner_authenticated
            if not authenticator.verify(pin):
                return "Owner authentication failed. No application was opened.", owner_authenticated
            owner_authenticated = True

        result = desktop.open_application(parsed.argument or "", authenticated_owner=owner_authenticated)
        return result.message, owner_authenticated

    # The parser currently emits only implemented actions. Keep this fail-closed guard
    # so a future parser addition cannot accidentally execute an unknown action.
    return "That local command is not implemented; no action was executed.", owner_authenticated


@app.command()
def chat(
    voice: bool = typer.Option(False, "--voice", help="Enable microphone input and spoken responses"),
) -> None:
    """Start persistent text chat or voice-enabled chat in the terminal."""
    settings = get_settings()
    configure_logging(settings)
    store = ConversationStore(settings)
    engine = ConversationEngine(settings, store)
    voice_engine = VoiceEngine(settings) if voice else None
    desktop = DesktopTools(settings, PermissionManager(settings))
    authenticator = _owner_authenticator(settings)
    owner_authenticated = False
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
                console.print(
                    "Commands: /help, /new, /history, /login, /logout, /exit. "
                    "Voice mode: jarvis chat --voice. Local actions support time/date, "
                    "allowlisted app launching, and consent-enabled face identification."
                )
                continue
            if command == "/new":
                conversation_id = engine.new_conversation_id()
                console.print("Started a new conversation.")
                continue
            if command == "/history":
                for conversation in store.list_conversations():
                    console.print(f"{conversation.updated_at} {conversation.id[:8]} {conversation.title}")
                continue
            if command == "/logout":
                owner_authenticated = False
                console.print("Owner action session locked.")
                continue
            if command == "/login":
                if not authenticator.is_configured:
                    console.print("Run 'jarvis auth setup' in PowerShell first.")
                    continue
                try:
                    pin = getpass.getpass("Owner PIN: ")
                except (EOFError, KeyboardInterrupt):
                    console.print("Owner authentication cancelled.")
                    continue
                owner_authenticated = authenticator.verify(pin)
                console.print("Owner action session unlocked." if owner_authenticated else "Owner PIN was not accepted.")
                continue

            local_command = parse_local_command(user_text, settings.name)
            if local_command is not None:
                response, owner_authenticated = _handle_local_command(
                    local_command,
                    settings,
                    store,
                    desktop,
                    authenticator,
                    owner_authenticated,
                    voice_engine,
                )
                console.print(Panel(response, title=settings.name))
                _speak_response(voice_engine, response)
                continue

            try:
                with console.status("JARVIS is thinking...", spinner="dots"):
                    response = engine.ask(conversation_id, user_text, source="voice" if voice else "text")
                console.print(Panel(response, title=settings.name))
                _speak_response(voice_engine, response)
            except ProviderError as exc:
                console.print(f"AI error: {exc}")
                log.warning("AI provider request failed: %s", exc)
                _speak_response(voice_engine, f"I couldn't reach the AI provider. {exc}")
            except Exception:
                log.exception("Unexpected chat error")
                console.print("Unexpected error. Check the local logs.")
    finally:
        store.close()


@auth_app.command("setup")
def auth_setup() -> None:
    """Set a local owner PIN used before permission-gated application actions."""
    settings = get_settings()
    authenticator = _owner_authenticator(settings)
    if authenticator.is_configured:
        console.print("Owner authentication is already configured.")
        raise typer.Exit(code=1)
    try:
        pin = getpass.getpass("Create owner PIN (at least 6 characters): ")
        confirmation = getpass.getpass("Confirm owner PIN: ")
        authenticator.setup(pin, confirmation)
    except (OwnerAuthError, EOFError, KeyboardInterrupt) as exc:
        console.print(f"Owner PIN setup failed: {exc or 'cancelled'}")
        raise typer.Exit(code=1) from exc
    console.print("Owner PIN configured. The PIN is stored as a salted hash, not plaintext.")


@auth_app.command("status")
def auth_status() -> None:
    """Show whether the local owner PIN is configured."""
    settings = get_settings()
    console.print(
        "Owner PIN: configured" if _owner_authenticator(settings).is_configured
        else "Owner PIN: not configured (run 'jarvis auth setup')"
    )


@face_app.command("enroll")
def face_enroll(
    profile_id: str = typer.Option(..., "--profile-id", help="Unique local profile ID"),
    name: str = typer.Option(..., "--name", help="Display name for the person being enrolled"),
    samples: int | None = typer.Option(None, "--samples", min=5, max=30, help="Number of samples to capture"),
) -> None:
    """Enroll a consenting person using multiple camera samples."""
    settings = get_settings()
    configure_logging(settings)
    if not settings.camera_enabled:
        console.print("Camera is disabled. Set JARVIS_CAMERA_ENABLED=true in .env and restart.")
        raise typer.Exit(code=1)
    if not typer.confirm(
        f"Has {name!r} been informed and explicitly consented to local face enrollment?",
        default=False,
    ):
        console.print("Enrollment cancelled; no samples were captured.")
        raise typer.Exit(code=1)

    store = ConversationStore(settings)
    try:
        profile_store = FaceProfileStore(store)
        service = FaceRecognitionService(settings, profile_store)
        directory = service.enroll_from_camera(
            profile_id,
            name,
            consent=True,
            target_samples=samples,
        )
        console.print(
            f"Enrolled {name} with consent. {settings.face_enrollment_samples if samples is None else samples} "
            f"samples stored locally in {directory}."
        )
        console.print("Note: face matching is identification only and does not unlock owner actions.")
    except (VisionError, OwnerAuthError, PermissionError, ValueError, OSError) as exc:
        console.print(f"Face enrollment failed: {exc}")
        raise typer.Exit(code=1) from exc
    finally:
        store.close()


@face_app.command("identify")
def face_identify(
    seconds: int = typer.Option(15, "--seconds", min=1, max=120, help="Maximum camera identification time"),
) -> None:
    """Run live local face identification against active consented profiles."""
    settings = get_settings()
    configure_logging(settings)
    store = ConversationStore(settings)
    try:
        service = FaceRecognitionService(settings, FaceProfileStore(store))
        match = service.identify_from_camera(seconds=seconds)
        if match is None:
            console.print("No active enrolled profile matched. Identity remains unknown.")
        else:
            console.print(
                f"Recognized {match.display_name} (LBPH distance {match.distance:.1f}; "
                f"configured threshold {match.threshold:.1f}). This is not owner authentication."
            )
    except VisionError as exc:
        console.print(f"Face identification failed: {exc}")
        raise typer.Exit(code=1) from exc
    finally:
        store.close()


@face_app.command("list")
def face_list() -> None:
    """List active enrolled face profiles without displaying biometric samples."""
    settings = get_settings()
    store = ConversationStore(settings)
    try:
        profiles = FaceProfileStore(store).list_active()
        if not profiles:
            console.print("No active face profiles are enrolled.")
            return
        for profile in profiles:
            console.print(f"{profile['profile_id']}: {profile['display_name']}")
    finally:
        store.close()


@face_app.command("revoke")
def face_revoke(
    profile_id: str = typer.Option(..., "--profile-id", help="Profile whose consent is being revoked"),
) -> None:
    """Revoke a profile and delete its local biometric samples."""
    settings = get_settings()
    store = ConversationStore(settings)
    try:
        profile_store = FaceProfileStore(store)
        profile = profile_store.get_profile(profile_id)
        if profile is None:
            console.print("No such face profile exists.")
            raise typer.Exit(code=1)
        if not typer.confirm(
            f"Revoke {profile['display_name']!r} and delete its local biometric samples?",
            default=False,
        ):
            console.print("Revocation cancelled.")
            raise typer.Exit(code=1)
        profile_store.revoke(profile_id)
        removed = FaceRecognitionService(settings, profile_store).delete_local_samples(profile_id)
        console.print(
            f"Profile {profile_id} revoked. "
            + ("Local biometric samples deleted." if removed else "No local sample folder remained.")
        )
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
    console.print(f"Owner PIN configured: {_owner_authenticator(settings).is_configured}")
    for name, module in [("AI SDK", "openai"), ("Voice", "speech_recognition"), ("Vision", "cv2")]:
        try:
            loaded = __import__(module)
            if name == "Vision":
                has_lbph = hasattr(loaded, "face") and hasattr(loaded.face, "LBPHFaceRecognizer_create")
                console.print(f"{name}: installed" + (", LBPH recognition available" if has_lbph else ", contrib face API missing"))
            else:
                console.print(f"{name}: installed")
        except ImportError:
            console.print(f"{name}: not installed; install the corresponding optional extra")
    try:
        store = ConversationStore(settings)
        store.close()
        console.print("Database connectivity: OK")
    except Exception as exc:
        console.print(f"Database connectivity: FAILED ({type(exc).__name__})")
        raise typer.Exit(code=1) from exc


if __name__ == "__main__":
    app()
