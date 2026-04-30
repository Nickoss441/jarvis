"""Spotify playback control via Spotipy (Spotify Web API)."""
from __future__ import annotations

import os
from typing import Any

from . import Tool

_VALID_ACTIONS = {"play", "pause", "skip", "previous", "volume", "search", "current", "liked"}


def _get_spotify() -> tuple[Any | None, str]:
    try:
        import spotipy  # type: ignore[import]
        from spotipy.oauth2 import SpotifyOAuth  # type: ignore[import]
    except ImportError:
        return None, "spotipy not installed — run: pip install spotipy"

    client_id = os.environ.get("SPOTIFY_CLIENT_ID", "")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
    redirect_uri = os.environ.get("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")

    if not client_id or not client_secret:
        return None, "SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in .env"

    try:
        sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scope="user-modify-playback-state user-read-playback-state user-read-currently-playing user-library-read",
                open_browser=False,
                cache_path="D:/jarvis-data/spotify_cache",
            )
        )
        return sp, ""
    except Exception as exc:  # noqa: BLE001
        return None, f"Spotify auth failed: {exc}"


def _get_active_device_id(sp: Any) -> str | None:
    try:
        devices = sp.devices()
        active = next((d for d in devices.get("devices", []) if d.get("is_active")), None)
        if active:
            return active["id"]
        if devices.get("devices"):
            return devices["devices"][0]["id"]
    except Exception:  # noqa: BLE001
        pass
    return None


def make_spotify_tool() -> Tool:

    def _handle(
        action: str,
        query: str = "",
        volume_percent: int | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        act = (action or "").strip().lower()
        if act not in _VALID_ACTIONS:
            return {"ok": False, "error": f"unsupported action '{action}'. choose: {', '.join(sorted(_VALID_ACTIONS))}"}

        sp, err = _get_spotify()
        if not sp:
            return {"ok": False, "error": err}

        device_id = _get_active_device_id(sp)

        try:
            if act == "current":
                track = sp.current_playback()
                if not track or not track.get("item"):
                    return {"ok": True, "playing": False}
                item = track["item"]
                artists = ", ".join(a["name"] for a in item.get("artists", []))
                return {
                    "ok": True,
                    "playing": track.get("is_playing", False),
                    "track": item["name"],
                    "artist": artists,
                    "album": item.get("album", {}).get("name", ""),
                    "progress_ms": track.get("progress_ms", 0),
                    "duration_ms": item.get("duration_ms", 0),
                }

            if act == "pause":
                sp.pause_playback(device_id=device_id)
                return {"ok": True, "action": "pause"}

            if act == "skip":
                sp.next_track(device_id=device_id)
                return {"ok": True, "action": "skip"}

            if act == "previous":
                sp.previous_track(device_id=device_id)
                return {"ok": True, "action": "previous"}

            if act == "volume":
                pct = max(0, min(100, int(volume_percent or 50)))
                sp.volume(pct, device_id=device_id)
                return {"ok": True, "action": "volume", "volume_percent": pct}

            if act == "play":
                if not query:
                    # Resume current playback
                    sp.start_playback(device_id=device_id)
                    return {"ok": True, "action": "play", "detail": "resumed"}

                # Search for track/artist and play first match
                results = sp.search(q=query, type="track", limit=1)
                tracks = results.get("tracks", {}).get("items", [])
                if not tracks:
                    return {"ok": False, "error": f"no track found for: {query}"}
                track = tracks[0]
                uri = track["uri"]
                artists = ", ".join(a["name"] for a in track.get("artists", []))
                sp.start_playback(device_id=device_id, uris=[uri])
                return {
                    "ok": True,
                    "action": "play",
                    "track": track["name"],
                    "artist": artists,
                    "uri": uri,
                }

            if act == "liked":
                saved = sp.current_user_saved_tracks(limit=50)
                items = saved.get("items", []) if isinstance(saved, dict) else []
                uris = []
                first_track = ""
                first_artist = ""
                for item in items:
                    track = item.get("track") if isinstance(item, dict) else None
                    if not isinstance(track, dict):
                        continue
                    uri = str(track.get("uri") or "").strip()
                    if not uri:
                        continue
                    uris.append(uri)
                    if not first_track:
                        first_track = str(track.get("name") or "").strip()
                        artists = track.get("artists", [])
                        if isinstance(artists, list):
                            first_artist = ", ".join(
                                str(a.get("name") or "").strip() for a in artists if isinstance(a, dict) and str(a.get("name") or "").strip()
                            )

                if not uris:
                    return {"ok": False, "error": "no liked songs found"}

                sp.start_playback(device_id=device_id, uris=uris)
                return {
                    "ok": True,
                    "action": "liked",
                    "count": len(uris),
                    "track": first_track,
                    "artist": first_artist,
                }

        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"Spotify error: {exc}"}

        return {"ok": False, "error": "unhandled action"}

    return Tool(
        name="spotify",
        description=(
            "Control Spotify playback. Actions: play (optionally with a search query), "
            "pause, skip, previous, volume (set volume_percent 0-100), current (now playing), liked (play liked songs)."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "One of: play, pause, skip, previous, volume, current, liked",
                },
                "query": {
                    "type": "string",
                    "description": "Song or artist to search and play (for 'play' action only)",
                },
                "volume_percent": {
                    "type": "integer",
                    "description": "Volume level 0-100 (for 'volume' action only)",
                    "minimum": 0,
                    "maximum": 100,
                },
            },
            "required": ["action"],
        },
        handler=_handle,
        tier="open",
    )
