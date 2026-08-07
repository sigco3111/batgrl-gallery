"""Persistent state for the launcher (favorites, recent-played).

State lives at ``~/.config/batgrl-gallery/state.json`` (overridable via the
``BATGRL_GALLERY_STATE`` environment variable). Writes are atomic: the JSON
goes to a sibling temp file first and is then renamed over the real path, so
a crash mid-write cannot corrupt the existing state.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any


_DEFAULT_PATH = Path.home() / ".config" / "batgrl-gallery" / "state.json"
_MAX_RECENT = 16


def state_path() -> Path:
    """Return the path to the launcher state file."""
    override = os.environ.get("BATGRL_GALLERY_STATE")
    if override:
        return Path(override).expanduser()
    return _DEFAULT_PATH


def load_state() -> dict[str, Any]:
    """Load the launcher state from disk.

    Returns ``{"favorites": [], "recent": []}`` if the file does not exist or
    is corrupt. Recent entries are returned sorted by timestamp descending.
    """
    path = state_path()
    if not path.exists():
        return {"favorites": [], "recent": []}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"favorites": [], "recent": []}
    favorites = list(data.get("favorites") or [])
    recent = list(data.get("recent") or [])
    recent.sort(key=lambda e: e.get("ts", 0.0), reverse=True)
    return {"favorites": favorites, "recent": recent}


def save_state(state: dict[str, Any]) -> None:
    """Persist state atomically (tmp + rename)."""
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "favorites": sorted(set(state.get("favorites", []))),
        "recent": sorted(
            state.get("recent", []),
            key=lambda e: e.get("ts", 0.0),
            reverse=True,
        )[:_MAX_RECENT],
    }
    # NamedTemporaryFile on the same dir is required so the rename is atomic.
    fd, tmp_name = tempfile.mkstemp(
        prefix=".state.", suffix=".json.tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def add_recent(state: dict[str, Any], game_id: str) -> dict[str, Any]:
    """Return a new state dict with ``game_id`` appended to ``recent``."""
    recent = [e for e in state.get("recent", []) if e.get("id") != game_id]
    recent.insert(0, {"id": game_id, "ts": time.time()})
    return {
        "favorites": state.get("favorites", []),
        "recent": recent[:_MAX_RECENT],
    }


def toggle_favorite(state: dict[str, Any], game_id: str) -> dict[str, Any]:
    """Return a new state dict with ``game_id`` toggled in favorites."""
    favs = set(state.get("favorites", []))
    if game_id in favs:
        favs.discard(game_id)
    else:
        favs.add(game_id)
    return {
        "favorites": sorted(favs),
        "recent": state.get("recent", []),
    }
