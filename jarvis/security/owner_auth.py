"""Local owner PIN authentication for permission-gated JARVIS actions.

The PIN is never stored in plaintext. This is local application authentication, not
a replacement for Windows account security or multi-factor authentication.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path
from typing import Any


_ITERATIONS = 600_000
_SALT_BYTES = 16
_DIGEST_BYTES = 32


class OwnerAuthError(RuntimeError):
    """Raised when owner authentication cannot be configured safely."""


class OwnerAuthenticator:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (Path("data") / "owner_auth.json")

    @property
    def is_configured(self) -> bool:
        return self.path.is_file()

    def setup(self, pin: str, confirmation: str) -> None:
        if self.is_configured:
            raise OwnerAuthError(
                "Owner authentication is already configured. Use the documented local reset procedure "
                "if you need to replace it."
            )
        if not pin or len(pin) < 6:
            raise OwnerAuthError("Choose a PIN or passphrase containing at least 6 characters.")
        if pin != confirmation:
            raise OwnerAuthError("The PIN entries do not match.")
        if "\n" in pin or "\r" in pin:
            raise OwnerAuthError("The PIN cannot contain newline characters.")

        salt = secrets.token_bytes(_SALT_BYTES)
        digest = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, _ITERATIONS, _DIGEST_BYTES)
        payload = {
            "version": 1,
            "algorithm": "pbkdf2_hmac_sha256",
            "iterations": _ITERATIONS,
            "salt": base64.b64encode(salt).decode("ascii"),
            "digest": base64.b64encode(digest).decode("ascii"),
        }

        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            try:
                os.chmod(temporary, 0o600)
            except OSError:
                # Windows ACLs are the primary protection on Windows.
                pass
            os.replace(temporary, self.path)
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                pass
        finally:
            if temporary.exists():
                temporary.unlink(missing_ok=True)

    def verify(self, pin: str) -> bool:
        if not self.is_configured or not isinstance(pin, str):
            return False
        try:
            payload: dict[str, Any] = json.loads(self.path.read_text(encoding="utf-8"))
            if payload.get("version") != 1 or payload.get("algorithm") != "pbkdf2_hmac_sha256":
                return False
            iterations = payload.get("iterations")
            if not isinstance(iterations, int) or not 100_000 <= iterations <= 2_000_000:
                return False
            salt = base64.b64decode(payload["salt"], validate=True)
            expected = base64.b64decode(payload["digest"], validate=True)
            if len(salt) != _SALT_BYTES or len(expected) != _DIGEST_BYTES:
                return False
            candidate = hashlib.pbkdf2_hmac(
                "sha256", pin.encode("utf-8"), salt, iterations, len(expected)
            )
            return hmac.compare_digest(candidate, expected)
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            return False
