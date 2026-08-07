"""Regression test for the launcher's interactive key dispatch.

Bug fixed by this test:
- The launcher rendered the catalog correctly but every key press was a no-op,
  because key events flow through ``App.root.dispatch_key`` (the gadget tree),
  not through the ``App`` instance itself. ``GalleryApp.on_key`` was therefore
  dead code, and the focused ``GameCard`` had no ``on_key`` override that
  routed keys upward.

These tests construct the ``GalleryApp``, run ``on_start`` via asyncio to
materialize the gadget tree, then dispatch synthetic ``KeyEvent``s to
``app.root.dispatch_key`` and assert the launcher responds correctly.
"""
from __future__ import annotations

import asyncio
import os
import sys

import pytest

# Force the venv python so the Cython extension is importable when the test
# runner is system python.
VENV_PYTHON = "/Users/mac/work/batgrl-gallery/.venv/bin/python"
if os.path.realpath(sys.executable) != os.path.realpath(VENV_PYTHON):
    pytest.skip(
        "These tests require the project venv (.venv/bin/python) so the "
        "Cython-compiled batgrl extension is importable.",
        allow_module_level=True,
    )

# Isolate launcher state.json to a per-session tmp path so tests never
# touch the user's real ~/.config/batgrl-gallery/state.json.
import tempfile

_TEST_STATE_DIR = tempfile.mkdtemp(prefix="ulw-launcher-tests-")
os.environ.setdefault("BATGRL_GALLERY_STATE", os.path.join(_TEST_STATE_DIR, "state.json"))

from batgrl.terminal.events import KeyEvent  # noqa: E402

from examples.demos.launcher import (  # noqa: E402
    GalleryApp,
    _LANG,
    GameCard,
    labels,
    launch_game,
)


@pytest.fixture(autouse=True)
def _reset_locale():
    _LANG["current"] = "ko"
    yield
    _LANG["current"] = "ko"


@pytest.fixture(autouse=True)
def _reset_module_state(tmp_path, monkeypatch):
    """Reset module-level mutable state and isolate storage to a tmp path."""
    monkeypatch.setenv("BATGRL_GALLERY_STATE", str(tmp_path / "state.json"))
    from examples.demos import launcher as L
    L._SEARCH_STATE.update(active=False, query="")
    L._FAVORITES.clear()
    L._FAVORITES_ONLY["on"] = False
    L._RECENT["history"] = []
    L._FILTER_STATE["current"] = None
    yield
    L._SEARCH_STATE.update(active=False, query="")
    L._FAVORITES.clear()
    L._FAVORITES_ONLY["on"] = False
    L._RECENT["history"] = []
    L._FILTER_STATE["current"] = None


def test_catalog_module_paths_resolve_to_a_package():
    """Every catalog module path must resolve to an importable package so that
    ``python -m <module>`` does not fail with ``is a package and cannot be
    directly executed``.

    Optional dependency failures (e.g. ``networkx`` for labyrinth, ``scipy`` for
    stable_fluid, ``moderngl`` for plasma_shader) are runtime concerns that
    ``launch_game`` reports to the user; they are not catalog bugs.
    """
    import importlib

    from examples.demos.catalog import GAMES

    bad_paths = []
    for game in GAMES:
        try:
            importlib.import_module(game.module)
        except ModuleNotFoundError as exc:
            # Only fail if the module itself (not an optional dep) is missing.
            if exc.name == game.module:
                bad_paths.append((game.id, game.module))
        except ImportError as exc:
            msg = str(exc)
            if "cannot be directly executed" in msg or "No module named" in msg and game.module.split(".")[-1] in msg:
                bad_paths.append((game.id, game.module))
    assert not bad_paths, (
        "These catalog module paths do not resolve to a runnable module:\n"
        + "\n".join(f"  {gid:30s} {mod}" for gid, mod in bad_paths)
    )


@pytest.fixture
def app_with_cards():
    """Build a GalleryApp with a real root gadget tree, run on_start."""
    from batgrl.geometry import Size
    from batgrl.gadgets._root import _Root

    app = GalleryApp(title="test")
    app.root = _Root(app=app, size=Size(40, 120))
    asyncio.run(app.on_start())
    return app


def test_escape_key_exits_app(app_with_cards):
    """Pressing Escape must terminate the app."""
    app = app_with_cards
    handled = app.root.dispatch_key(KeyEvent("escape"))
    assert handled is True
    assert app.is_running is False  # app.exit() sets root to None


def test_l_key_toggles_language(app_with_cards):
    """Pressing L must flip the active locale and re-render footer text."""
    app = app_with_cards
    assert labels()["app_title"] == "batgrl 갤러리"
    handled = app.root.dispatch_key(KeyEvent("l"))
    assert handled is True
    assert _LANG["current"] == "en"
    assert labels()["app_title"] == "batgrl Gallery"

    # Toggle back
    app.root.dispatch_key(KeyEvent("l"))
    assert _LANG["current"] == "ko"


def test_down_arrow_moves_focus(app_with_cards):
    """Pressing Down must move focus to the next focusable (card)."""
    app = app_with_cards
    initial_focused = next(
        c for c in app.cards if c.is_focused
    ), "at least one card must be focused after on_start"
    initial_idx = app.cards.index(initial_focused[0])

    handled = app.root.dispatch_key(KeyEvent("down"))
    assert handled is True

    new_focused = next(c for c in app.cards if c.is_focused)
    new_idx = app.cards.index(new_focused)
    assert new_idx == (initial_idx + 1) % len(app.cards)


def test_up_arrow_moves_focus_back(app_with_cards):
    """Up from the first card must wrap to the last."""
    app = app_with_cards
    app.cards[0].focus()
    handled = app.root.dispatch_key(KeyEvent("up"))
    assert handled is True
    focused_idx = app.cards.index(next(c for c in app.cards if c.is_focused))
    assert focused_idx == len(app.cards) - 1


def test_enter_signals_main_to_spawn_child(app_with_cards, monkeypatch):
    """Enter must NOT block the parent on waitpid. Instead it records the
    focused game id in ``_PENDING_GAME`` and exits the App so ``main()`` can
    spawn the child with inherited stdio (which works because the launcher
    has already restored the terminal)."""
    from examples.demos import launcher as launcher_mod

    app = app_with_cards
    # Reset pending-game cell and patch it for the duration of the test.
    monkeypatch.setattr(launcher_mod, "_PENDING_GAME", {"value": None})

    app.cards[2].focus()
    handled = app.root.dispatch_key(KeyEvent("enter"))
    assert handled is True
    assert launcher_mod._PENDING_GAME["value"] == app.cards[2].game.id
    assert app.is_running is False, (
        "App must exit on Enter so main() can spawn the child with inherited stdio"
    )


def test_focused_card_has_visible_focus_state(app_with_cards):
    """A focused card must have a bg color that contrasts with the unfocused state."""
    app = app_with_cards
    card = app.cards[1]
    card.focus()
    focused_bg = card.default_bg_color
    card.blur()
    blurred_bg = card.default_bg_color
    assert focused_bg != blurred_bg, (
        "focused and blurred default_bg_color must differ so the focused "
        "card is visually distinct."
    )


def test_l_or_escape_keys_do_not_silently_swallow():
    """Sanity: every key must dispatch as handled (return True)."""
    from batgrl.geometry import Size
    from batgrl.gadgets._root import _Root

    for key in ("escape", "l", "up", "down", "enter"):
        app = GalleryApp(title="test")
        app.root = _Root(app=app, size=Size(40, 120))
        asyncio.run(app.on_start())
        handled = app.root.dispatch_key(KeyEvent(key))
        assert handled is True, f"dispatch_key({key!r}) returned falsy"


# ---------------------------------------------------------------------------
# Tier 1 improvements
# ---------------------------------------------------------------------------


def test_catalog_has_controls_and_deps_status():
    """Every GameInfo must carry non-empty ``controls`` and a sensible
    ``deps_status`` (either ``"ok"`` or starting with ``"missing:"``)."""
    from examples.demos.catalog import GAMES

    missing_controls = [g.id for g in GAMES if not getattr(g, "controls", "").strip()]
    assert not missing_controls, (
        f"These games have empty/missing controls: {missing_controls}"
    )

    bad_status = []
    for g in GAMES:
        status = getattr(g, "deps_status", None)
        if status is None:
            bad_status.append((g.id, "no deps_status attribute"))
        elif not (status == "ok" or status.startswith("missing:")):
            bad_status.append((g.id, status))
    assert not bad_status, f"Bad deps_status values: {bad_status}"


def test_filter_key_hides_non_matching_cards(app_with_cards):
    """Pressing ``1`` must hide every non-puzzle card and leave puzzle cards visible."""
    from examples.demos.catalog import GAMES

    app = app_with_cards
    puzzle_ids = {g.id for g in GAMES if g.category == "puzzle"}

    handled = app.root.dispatch_key(KeyEvent("1"))
    assert handled is True

    visible = {c.game.id for c in app.cards if c.is_visible}
    hidden = {c.game.id for c in app.cards if not c.is_visible}
    assert visible == puzzle_ids, (
        f"Expected only puzzle cards visible, got visible={visible}, hidden={hidden}"
    )


def test_filter_zero_restores_all_cards(app_with_cards):
    """Pressing ``0`` after a filter must restore every card to visible."""
    app = app_with_cards
    app.root.dispatch_key(KeyEvent("2"))  # filter to arcade
    assert sum(1 for c in app.cards if c.is_visible) < len(app.cards)

    app.root.dispatch_key(KeyEvent("0"))
    visible = sum(1 for c in app.cards if c.is_visible)
    assert visible == len(app.cards)


def test_focused_card_uses_category_color(app_with_cards):
    """A focused card's ``default_bg_color`` must match its category's focused color."""
    from examples.demos.launcher import CATEGORY_FOCUSED_BG

    app = app_with_cards
    card = app.cards[0]
    card.focus()
    expected = CATEGORY_FOCUSED_BG[card.game.category]
    assert card.default_bg_color == expected, (
        f"card category={card.game.category!r} expected {expected} got {card.default_bg_color}"
    )


def test_focused_card_renders_arrow_indicator(app_with_cards):
    """A focused card's first line must include a selection arrow (``▶``)."""
    app = app_with_cards
    card = app.cards[0]
    card.focus()
    ords = card.canvas["ord"][0]
    first_line = "".join(chr(o) for o in ords.tolist())
    assert "\u25b6" in first_line, (
        f"Focused card first line should contain the arrow indicator, got: {first_line!r}"
    )


def test_header_reflects_current_filter(app_with_cards):
    """The header must report the current filter (e.g., ``전체`` vs ``퍼즐만``)."""
    from examples.demos.locales import ko

    def header_text() -> str:
        ords = app.header.canvas["ord"][0]  # header is size (1, 80)
        # Drop padding zeros (continuation cells of multi-cell glyphs) and join.
        return "".join(chr(o) for o in ords.tolist() if o).strip()

    app = app_with_cards
    # Initial state: "전체" (all) filter is the default.
    initial = header_text()
    assert ko.LABELS["filter_all"] in initial, (
        f"Header should show default filter_all label, got: {initial!r}"
    )

    # After pressing 1 (puzzle filter) the header should mention puzzle-only.
    app.root.dispatch_key(KeyEvent("1"))
    after = header_text()
    expected = ko.LABELS["filter_only"].format(cat=ko.LABELS["category_puzzle"])
    assert expected in after, (
        f"Header after filter=1 should contain {expected!r}, got: {after!r}"
    )

    # After pressing 0 (all), the header should be back to filter_all.
    app.root.dispatch_key(KeyEvent("0"))
    final = header_text()
    assert ko.LABELS["filter_all"] in final, (
        f"Header after filter=0 should show filter_all again, got: {final!r}"
    )


# ---------------------------------------------------------------------------
# Tier 2 improvements
# ---------------------------------------------------------------------------


def _card_text(card) -> str:
    """Read every row of a Text card as a string (skipping padding zeros)."""
    rows = []
    for row in card.canvas["ord"]:
        rows.append("".join(chr(o) for o in row.tolist() if o))
    return "\n".join(rows)


def test_search_slash_then_letter_filters_live(app_with_cards):
    """``/`` enters search mode; subsequent letter keys filter cards live.

    The fixture has at least one card whose Korean title contains ``테``
    (tetris: 테스트리스, sliding_puzzle: 슬라이딩 퍼즐, etc.); the search
    query ``테`` must leave only those cards visible.
    """
    from examples.demos import launcher as launcher_mod

    app = app_with_cards
    # Reset search state in case prior tests touched it.
    if hasattr(launcher_mod, "_SEARCH_STATE"):
        launcher_mod._SEARCH_STATE.update(active=False, query="")

    handled = app.root.dispatch_key(KeyEvent("/"))
    assert handled is True
    assert launcher_mod._SEARCH_STATE["active"] is True

    # Type '테' (two keystrokes) into the search.
    for ch in ("테",):
        # Each Korean character is a single CharKey. Send as a KeyEvent with
        # the raw key character. batgrl accepts the unicode codepoint as key.
        app.root.dispatch_key(KeyEvent(ch))
    query = launcher_mod._SEARCH_STATE["query"]
    assert "테" in query

    visible_titles = [
        c.game.title_ko for c in app.cards if c.is_visible
    ]
    assert len(visible_titles) > 0
    for t in visible_titles:
        assert "테" in t, f"Card {t!r} visible despite search query '테'"

    # Cards without '테' in their title_ko must be hidden.
    hidden_titles = [
        c.game.title_ko for c in app.cards if not c.is_visible
    ]
    for t in hidden_titles:
        assert "테" not in t


def test_search_escape_clears_filter(app_with_cards):
    """Esc while in search mode exits search and restores every card to visible."""
    from examples.demos import launcher as launcher_mod

    app = app_with_cards
    launcher_mod._SEARCH_STATE.update(active=False, query="")
    app.root.dispatch_key(KeyEvent("/"))
    app.root.dispatch_key(KeyEvent("t"))
    assert sum(1 for c in app.cards if c.is_visible) < len(app.cards)

    handled = app.root.dispatch_key(KeyEvent("escape"))
    assert handled is True
    assert launcher_mod._SEARCH_STATE["active"] is False
    assert launcher_mod._SEARCH_STATE["query"] == ""


def test_favorite_toggle_marks_card_with_star(app_with_cards):
    """Pressing ``f`` on a focused card must toggle its favorite status and
    render a star marker on the card."""
    from examples.demos import launcher as launcher_mod

    app = app_with_cards
    card = app.cards[0]
    card.focus()
    assert card.game.id not in launcher_mod._FAVORITES

    handled = app.root.dispatch_key(KeyEvent("f"))
    assert handled is True
    assert card.game.id in launcher_mod._FAVORITES
    text = _card_text(card)
    assert "\u2605" in text or "★" in text, (
        f"Favorited card should show a star, got: {text!r}"
    )

    # Toggle again — favorite must be removed.
    app.root.dispatch_key(KeyEvent("f"))
    assert card.game.id not in launcher_mod._FAVORITES


def test_favorite_filter_key_shows_only_favorites(app_with_cards):
    """Pressing ``5`` must show only favorited cards; pressing ``0`` restores all."""
    from examples.demos import launcher as launcher_mod

    app = app_with_cards
    # Favorite the first 3 cards.
    launcher_mod._FAVORITES.clear()
    for c in app.cards[:3]:
        c.focus()
        app.root.dispatch_key(KeyEvent("f"))

    handled = app.root.dispatch_key(KeyEvent("5"))
    assert handled is True
    visible_ids = {c.game.id for c in app.cards if c.is_visible}
    assert visible_ids == {c.game.id for c in app.cards[:3]}, (
        f"Filter 5 should show only the 3 favorited cards, got: {visible_ids}"
    )

    app.root.dispatch_key(KeyEvent("0"))
    assert sum(1 for c in app.cards if c.is_visible) == len(app.cards)


def test_recent_marker_appears_after_launch():
    """Recording a launch via the main loop must add the id to ``_RECENT`` and
    the corresponding card must render a recent marker (e.g., ``\u25cf``)."""
    from batgrl.geometry import Size
    from batgrl.gadgets._root import _Root
    from examples.demos import launcher as launcher_mod

    # Reset recent BEFORE building the app, so the card renders with the marker.
    launcher_mod._RECENT["history"] = [
        {"id": "tetris", "ts": 9999999999.0}  # far future = always "just now"
    ]

    app = GalleryApp(title="test")
    app.root = _Root(app=app, size=Size(40, 160))
    asyncio.run(app.on_start())

    tetris_card = next(c for c in app.cards if c.game.id == "tetris")
    text = _card_text(tetris_card)
    assert "\u25cf" in text, f"Recent card should show a dot marker, got: {text!r}"

    # Also verify the storage layer round-trips this entry.
    from examples.demos import storage
    state = {"favorites": [], "recent": [{"id": "tetris", "ts": 1.0}]}
    storage.save_state.__globals__  # ensure module loaded
    storage.save_state(state)
    loaded = storage.load_state()
    assert any(e["id"] == "tetris" for e in loaded["recent"])


def test_sidebar_reflects_focused_game(app_with_cards):
    """A sidebar widget on root must show the focused game's title."""
    app = app_with_cards
    sidebar = app.sidebar  # GalleryApp must expose ``sidebar``

    sidebar_text = lambda: "".join(
        chr(o) for o in sidebar.canvas["ord"].flatten().tolist() if o
    ).strip()
    initial = sidebar_text()
    # Default focus is the first card; its title must appear in the sidebar.
    focused_title = app.cards[0].game.title_ko
    assert focused_title in initial, (
        f"Sidebar should mention focused card title {focused_title!r}, got: {initial!r}"
    )

    # Move focus down and the sidebar text must change to the new focused card's title.
    app.root.dispatch_key(KeyEvent("down"))
    new_focused_title = app.cards[1].game.title_ko
    refreshed = sidebar_text()
    assert new_focused_title in refreshed, (
        f"Sidebar should now mention {new_focused_title!r}, got: {refreshed!r}"
    )


def test_sidebar_shows_exit_keys_for_focused_game(app_with_cards):
    """The sidebar must include the focused game's exit-keys hint so the user
    knows how to quit before launching it. Both ``Esc`` and ``Ctrl+C`` must be
    shown in every game's hint because some games ignore Esc but all react to
    Ctrl+C (which batgrl's ``App`` always handles)."""
    from examples.demos.locales import ko

    app = app_with_cards
    sidebar_text = lambda: "".join(
        chr(o) for o in app.sidebar.canvas["ord"].flatten().tolist() if o
    ).strip()

    # Every GameInfo must carry a non-empty exit_keys string that mentions
    # both Esc and Ctrl+C (universal exit contract).
    from examples.demos.catalog import GAMES
    for g in GAMES:
        ek = g.exit_keys
        assert ek, f"{g.id} has empty exit_keys"
        assert "Esc" in ek, f"{g.id} exit_keys missing Esc: {ek!r}"
        assert "Ctrl" in ek or "ctrl" in ek.lower(), (
            f"{g.id} exit_keys missing Ctrl+C: {ek!r}"
        )

    # Sidebar must mention the exit label and the focused game's exit hint.
    tetris_card = next(c for c in app.cards if c.game.id == "tetris")
    tetris_card.focus()
    text = sidebar_text()
    assert ko.LABELS["sidebar_exit"] in text, (
        f"Sidebar should contain exit label {ko.LABELS['sidebar_exit']!r}, got: {text!r}"
    )
    assert tetris_card.game.exit_keys in text, (
        f"Sidebar should contain tetris exit_keys {tetris_card.game.exit_keys!r}, got: {text!r}"
    )
