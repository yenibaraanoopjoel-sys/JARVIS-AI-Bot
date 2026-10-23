"""Permission-controlled JARVIS desktop tools."""
import os
import subprocess
from pathlib import Path
from ..config import Settings
from ..security.permissions import Capability, PermissionManager
from ..models import ToolResult


class DesktopTools:
    def __init__(self, settings: Settings, permissions: PermissionManager):
        self.settings = settings
        self.permissions = permissions

    def open_application(self, name: str, *, authenticated_owner: bool = False) -> ToolResult:
        decision = self.permissions.check(Capability.APP_LAUNCH, authenticated_owner=authenticated_owner)
        if not decision.allowed:
            return ToolResult(tool_name="open_application", success=False, message=decision.reason)
        allowlist = {"notepad": ["notepad.exe"], "calculator": ["calc.exe"], "explorer": ["explorer.exe"], "powershell": ["powershell.exe"]}
        key = name.strip().lower()
        if key not in allowlist:
            return ToolResult(tool_name="open_application", success=False, message="Application is not in the built-in allowlist.", data={"allowed": sorted(allowlist)})
        try:
            if os.name != "nt":
                return ToolResult(tool_name="open_application", success=False, message="This tool currently supports Windows only.")
            process = subprocess.Popen(allowlist[key], close_fds=True, shell=False)
            return ToolResult(tool_name="open_application", success=True, message=f"Launch request sent for {key}.", data={"pid": process.pid, "application": key})
        except OSError as exc:
            return ToolResult(tool_name="open_application", success=False, message=f"Application launch failed: {exc.__class__.__name__}.")

    def read_text_file(self, path: str, *, approved_root: str) -> ToolResult:
        root = Path(approved_root).expanduser().resolve()
        target = Path(path).expanduser().resolve()
        try:
            target.relative_to(root)
        except ValueError:
            return ToolResult(tool_name="read_text_file", success=False, message="Path is outside the approved directory.")
        if not target.is_file():
            return ToolResult(tool_name="read_text_file", success=False, message="File does not exist or is not a regular file.")
        if target.stat().st_size > 1_000_000:
            return ToolResult(tool_name="read_text_file", success=False, message="File exceeds the 1 MB text-reading limit.")
        try:
            content = target.read_text(encoding="utf-8")
            return ToolResult(tool_name="read_text_file", success=True, message="Text file read successfully.", data={"path": str(target), "content": content})
        except (OSError, UnicodeError) as exc:
            return ToolResult(tool_name="read_text_file", success=False, message=f"Could not read text file: {exc.__class__.__name__}.")
