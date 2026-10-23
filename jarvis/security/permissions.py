"""Centralized permission checks. Dangerous tools remain denied by default."""
from enum import StrEnum
from dataclasses import dataclass
from ..config import Settings


class Capability(StrEnum):
    APP_LAUNCH = "app_launch"
    FILESYSTEM_READ = "filesystem_read"
    FILESYSTEM_WRITE = "filesystem_write"
    TERMINAL = "terminal"
    CAMERA = "camera"


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    reason: str


class PermissionManager:
    def __init__(self, settings: Settings):
        self.settings = settings

    def check(self, capability: Capability, *, authenticated_owner: bool = False) -> PermissionDecision:
        if capability in {Capability.APP_LAUNCH, Capability.FILESYSTEM_WRITE, Capability.TERMINAL} and not authenticated_owner:
            return PermissionDecision(False, "This action requires verified owner authentication.")
        if capability == Capability.APP_LAUNCH and not self.settings.allow_app_launch:
            return PermissionDecision(False, "Application launching is disabled in configuration.")
        if capability == Capability.FILESYSTEM_WRITE and not self.settings.allow_filesystem_writes:
            return PermissionDecision(False, "Filesystem writes are disabled in configuration.")
        if capability == Capability.TERMINAL and not self.settings.allow_terminal:
            return PermissionDecision(False, "Terminal execution is disabled in configuration.")
        if capability == Capability.CAMERA and not self.settings.camera_enabled:
            return PermissionDecision(False, "Camera access is disabled in configuration.")
        return PermissionDecision(True, "Permission granted by current configuration.")
