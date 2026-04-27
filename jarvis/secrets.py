"""Secret provider abstraction for runtime configuration.

Providers are lightweight adapters so production deployments can fetch
credentials from env vars, macOS keychain, 1Password CLI, or Bitwarden CLI
without changing business logic.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import Callable, Protocol


class SecretProvider(Protocol):
    def get(self, key: str) -> str:
        """Return secret value for *key* or empty string if unavailable."""


@dataclass(frozen=True)
class EnvSecretProvider:
    def get(self, key: str) -> str:
        return os.environ.get(key, "")


@dataclass(frozen=True)
class KeychainSecretProvider:
    """macOS Keychain adapter via `security` CLI.

    Looks up generic-password entries under a service/account tuple.
    Service defaults to ``jarvis``; account defaults to the requested key.
    """

    service: str = "jarvis"
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run

    def get(self, key: str) -> str:
        account = os.environ.get(f"JARVIS_KEYCHAIN_ACCOUNT_{key}", key)
        try:
            completed = self.runner(
                [
                    "security",
                    "find-generic-password",
                    "-s",
                    self.service,
                    "-a",
                    account,
                    "-w",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return ""

        if completed.returncode != 0:
            return ""
        return (completed.stdout or "").strip()


@dataclass(frozen=True)
class OnePasswordSecretProvider:
    """1Password adapter using `op read` references from env."""

    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run

    def get(self, key: str) -> str:
        ref = os.environ.get(f"JARVIS_OP_REF_{key}", "").strip()
        if not ref:
            return ""
        try:
            completed = self.runner(
                ["op", "read", ref],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return ""

        if completed.returncode != 0:
            return ""
        return (completed.stdout or "").strip()


@dataclass(frozen=True)
class BitwardenSecretProvider:
    """Bitwarden adapter using `bw get password` item IDs from env."""

    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run

    def get(self, key: str) -> str:
        item = os.environ.get(f"JARVIS_BW_ITEM_{key}", "").strip()
        if not item:
            return ""
        try:
            completed = self.runner(
                ["bw", "get", "password", item],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return ""

        if completed.returncode != 0:
            return ""
        return (completed.stdout or "").strip()


def build_secret_provider(name: str) -> SecretProvider:
    normalized = (name or "env").strip().lower()
    if normalized in {"env", "environment"}:
        return EnvSecretProvider()
    if normalized in {"keychain", "macos-keychain"}:
        service = (os.environ.get("JARVIS_KEYCHAIN_SERVICE", "jarvis").strip() or "jarvis")
        return KeychainSecretProvider(service=service)
    if normalized in {"1password", "op"}:
        return OnePasswordSecretProvider()
    if normalized in {"bitwarden", "bw"}:
        return BitwardenSecretProvider()
    raise ValueError(
        "unsupported secret provider: "
        f"{name}. expected one of env, keychain, 1password, bitwarden"
    )
