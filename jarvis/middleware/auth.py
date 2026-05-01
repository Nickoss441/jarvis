"""Token-based auth helper for the Jarvis approval API.

If the JARVIS_API_TOKEN environment variable is set, all requests to
AUTH_REQUIRED_PREFIXES must include an ``Authorization: Bearer <token>``
header.  If the env var is not set, auth is skipped (dev mode).
"""
import os
from typing import Any

AUTH_REQUIRED_PREFIXES = [
    "/hud/",
    "/ipc/",
    "/trade/",
    "/local/",
    "/approvals/",
]


def check_auth(headers: dict[str, Any], config: Any = None) -> bool:
    """Return True if the request is authorised, False otherwise.

    Parameters
    ----------
    headers:
        Mapping of HTTP header names to values.  Keys are matched
        case-insensitively.
    config:
        Optional config object (reserved for future use; currently unused).

    Returns
    -------
    bool
        ``True`` when auth passes or is not required, ``False`` when a token
        is configured but the request does not supply a matching bearer token.
    """
    token = os.environ.get("JARVIS_API_TOKEN", "").strip()
    if not token:
        return True

    normalised = {k.lower(): v for k, v in (headers or {}).items()}
    auth_header = normalised.get("authorization", "").strip()

    if not auth_header.lower().startswith("bearer "):
        return False

    supplied = auth_header[len("bearer "):].strip()
    return supplied == token
