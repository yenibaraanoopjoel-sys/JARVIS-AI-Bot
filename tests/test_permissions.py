from jarvis.config import Settings
from jarvis.security.permissions import Capability, PermissionManager


def test_terminal_denied_by_default():
    manager = PermissionManager(Settings(_env_file=None))
    result = manager.check(Capability.TERMINAL, authenticated_owner=True)
    assert not result.allowed


def test_sensitive_capability_requires_owner():
    settings = Settings(_env_file=None, allow_app_launch=True)
    manager = PermissionManager(settings)
    result = manager.check(Capability.APP_LAUNCH, authenticated_owner=False)
    assert not result.allowed
