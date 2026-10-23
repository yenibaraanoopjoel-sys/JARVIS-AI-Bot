"""Deterministic routing for explicitly supported local voice commands.

Only commands handled by a real application tool are routed here. Other requests
continue to the AI conversation engine; parsing a command never executes it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class LocalCommand:
    action: str
    argument: str | None = None


_APP_ALIASES = {
    "notepad": "notepad",
    "text editor": "notepad",
    "calculator": "calculator",
    "calc": "calculator",
    "explorer": "explorer",
    "file explorer": "explorer",
    "windows explorer": "explorer",
    "powershell": "powershell",
    "power shell": "powershell",
}


def _clean_text(text: str, assistant_name: str) -> str:
    cleaned = " ".join(text.casefold().strip().split()).strip(" .!?")
    name = re.escape(assistant_name.casefold().strip())
    if name:
        cleaned = re.sub(rf"^(?:hey\s+)?{name}[\s,:-]+", "", cleaned, count=1)
    return cleaned.strip(" .!?,:")


def parse_local_command(text: str, assistant_name: str = "JARVIS") -> LocalCommand | None:
    """Recognize a small allowlisted set of deterministic local commands."""
    cleaned = _clean_text(text, assistant_name)
    if not cleaned:
        return None

    if cleaned in {"what time is it", "tell me the time", "current time", "time now"}:
        return LocalCommand("current_time")
    if cleaned in {"what is the date", "what is today's date", "what date is it", "today's date", "current date"}:
        return LocalCommand("current_date")
    if cleaned in {
        "identify who is in front of me",
        "who is in front of me",
        "who's in front of me",
        "identify the face",
        "recognize the face",
        "who is that",
        "who's that",
    }:
        return LocalCommand("identify_face")

    match = re.fullmatch(r"(?:please\s+)?(?:open|launch|start|run)\s+([a-z0-9][a-z0-9 _-]*)", cleaned)
    if match:
        requested_app = " ".join(match.group(1).split()).strip()
        app = _APP_ALIASES.get(requested_app)
        if app:
            return LocalCommand("open_application", app)

    return None


def current_time_response() -> str:
    now = datetime.now().astimezone()
    return f"It is {now.strftime('%I:%M %p').lstrip('0')}."


def current_date_response() -> str:
    now = datetime.now().astimezone()
    return f"Today is {now.strftime('%A, %B')} {now.day}, {now.year}."
