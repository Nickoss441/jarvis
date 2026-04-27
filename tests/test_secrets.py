import subprocess

import pytest

from jarvis.secrets import (
    BitwardenSecretProvider,
    EnvSecretProvider,
    KeychainSecretProvider,
    OnePasswordSecretProvider,
    build_secret_provider,
)


def _completed(stdout: str, returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


def test_env_secret_provider_reads_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "abc")
    provider = EnvSecretProvider()
    assert provider.get("ANTHROPIC_API_KEY") == "abc"


def test_env_secret_provider_missing_returns_empty(monkeypatch):
    monkeypatch.delenv("MISSING_SECRET", raising=False)
    provider = EnvSecretProvider()
    assert provider.get("MISSING_SECRET") == ""


def test_keychain_secret_provider_uses_service_and_account(monkeypatch):
    calls: list[list[str]] = []

    def _runner(*args, **kwargs):
        calls.append(args[0])
        return _completed("keychain-value\n")

    monkeypatch.setenv("JARVIS_KEYCHAIN_ACCOUNT_ANTHROPIC_API_KEY", "anthropic")
    provider = KeychainSecretProvider(service="jarvis-prod", runner=_runner)

    assert provider.get("ANTHROPIC_API_KEY") == "keychain-value"
    assert calls[0] == [
        "security",
        "find-generic-password",
        "-s",
        "jarvis-prod",
        "-a",
        "anthropic",
        "-w",
    ]


def test_onepassword_provider_reads_ref(monkeypatch):
    def _runner(*args, **kwargs):
        assert args[0] == ["op", "read", "op://Jarvis/Anthropic/api_key"]
        return _completed("op-secret\n")

    monkeypatch.setenv("JARVIS_OP_REF_ANTHROPIC_API_KEY", "op://Jarvis/Anthropic/api_key")
    provider = OnePasswordSecretProvider(runner=_runner)
    assert provider.get("ANTHROPIC_API_KEY") == "op-secret"


def test_bitwarden_provider_reads_item(monkeypatch):
    def _runner(*args, **kwargs):
        assert args[0] == ["bw", "get", "password", "item-id-123"]
        return _completed("bw-secret\n")

    monkeypatch.setenv("JARVIS_BW_ITEM_ANTHROPIC_API_KEY", "item-id-123")
    provider = BitwardenSecretProvider(runner=_runner)
    assert provider.get("ANTHROPIC_API_KEY") == "bw-secret"


def test_build_secret_provider_supports_known_aliases(monkeypatch):
    monkeypatch.setenv("JARVIS_KEYCHAIN_SERVICE", "jarvis")
    assert type(build_secret_provider("env")).__name__ == "EnvSecretProvider"
    assert type(build_secret_provider("keychain")).__name__ == "KeychainSecretProvider"
    assert type(build_secret_provider("1password")).__name__ == "OnePasswordSecretProvider"
    assert type(build_secret_provider("bitwarden")).__name__ == "BitwardenSecretProvider"


def test_build_secret_provider_unknown_raises():
    with pytest.raises(ValueError, match="unsupported secret provider"):
        build_secret_provider("vault")
