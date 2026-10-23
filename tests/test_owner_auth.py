from pathlib import Path

import pytest

from jarvis.security.owner_auth import OwnerAuthError, OwnerAuthenticator


def test_owner_pin_setup_and_verification(tmp_path: Path):
    auth_file = tmp_path / "owner_auth.json"
    auth = OwnerAuthenticator(auth_file)

    auth.setup("correct horse battery", "correct horse battery")

    assert auth.is_configured
    assert auth.verify("correct horse battery")
    assert not auth.verify("wrong pin")
    assert "correct horse battery" not in auth_file.read_text(encoding="utf-8")


def test_owner_pin_setup_rejects_mismatch(tmp_path: Path):
    auth = OwnerAuthenticator(tmp_path / "owner_auth.json")
    with pytest.raises(OwnerAuthError):
        auth.setup("123456", "654321")
    assert not auth.is_configured


def test_owner_pin_cannot_be_replaced_silently(tmp_path: Path):
    auth = OwnerAuthenticator(tmp_path / "owner_auth.json")
    auth.setup("123456", "123456")
    with pytest.raises(OwnerAuthError):
        auth.setup("abcdef", "abcdef")


def test_missing_auth_file_never_authenticates(tmp_path: Path):
    assert not OwnerAuthenticator(tmp_path / "missing.json").verify("anything")
