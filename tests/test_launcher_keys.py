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
    """Up from the first card must wrap to the last card in the same column."""
    app = app_with_cards
    app.cards[0].focus()  # col 0 row 0
    handled = app.root.dispatch_key(KeyEvent("up"))
    assert handled is True
    focused_idx = app.cards.index(next(c for c in app.cards if c.is_focused))
    # col 0 has 11 cards (rows 0..10), so wrap goes to row 10 = idx 10.
    assert focused_idx == 10, (
        f"Up from idx 0 should wrap to idx 10 (col 0 row 10), got {focused_idx}"
    )


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
    """A focused card's row 1 must include a selection arrow (``▶``)."""
    app = app_with_cards
    card = app.cards[0]
    card.focus()
    ords = card.canvas["ord"][1]
    first_line = "".join(chr(o) for o in ords.tolist())
    assert "\u25b6" in first_line, (
        f"Focused card row 1 should contain the arrow indicator, got: {first_line!r}"
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


# ---------------------------------------------------------------------------
# Card box border tests (Round 12)
# ---------------------------------------------------------------------------


_SINGLE_V = "\u2502"
_DOUBLE_V = "\u2551"
_BOX_CHARS = set("─━┌┐└┘╭╮╰╯├┤┬┴┼═║╔╗╚╝╠╣╦╩╬")


def test_every_card_bottom_row_is_a_box_border(app_with_cards):
    """The last row of each card must consist of box-drawing characters
    forming a horizontal border (─, ━, etc.) plus optional corners."""
    app = app_with_cards
    bad = []
    for c in app.cards:
        bottom_row = c.canvas["ord"][c.size.height - 1]  # last row is the bottom border
        text = "".join(chr(o) for o in bottom_row.tolist())
        # Strip padding zeros so we can find non-padding chars.
        visible = text.rstrip("\x00")
        if not visible:
            bad.append((c.game.id, "empty border row"))
            continue
        if not all((ch in _BOX_CHARS) or ch == "\x00" for ch in text):
            bad.append((c.game.id, f"non-border chars: {visible[:40]!r}"))
    assert not bad, f"Cards without proper border row: {bad}"


def test_focused_card_border_visually_distinct(app_with_cards):
    """The focused card's border must be visually distinct from the blurred
    cards' borders. We compare the foreground color of the border row's
    first non-empty cell."""
    app = app_with_cards

    def border_color(card) -> tuple:
        # Pick the first cell of the border row whose fg_color is not the
        # default (255, 255, 255).
        fg = card.canvas["fg_color"][2]
        for cell in fg:
            t = tuple(int(x) for x in cell.tolist())
            if t != (255, 255, 255):
                return t
        return tuple(int(x) for x in fg[0].tolist())

    card = app.cards[0]
    card.blur()
    blurred_color = border_color(card)
    card.focus()
    focused_color = border_color(card)
    assert focused_color != blurred_color, (
        f"Focused card border color {focused_color!r} matches blurred "
        f"{blurred_color!r}; focus state must be visually distinct."
    )


def test_card_text_does_not_overlap_border_row(app_with_cards):
    """Top (row 0) and bottom (row 3) rows must be ONLY border chars + spaces;
    the title row (row 1) and meta row (row 2) must start with a vertical edge char."""
    app = app_with_cards
    bad = []
    for c in app.cards:
        for r in (0, 3):
            text = "".join(chr(o) for o in c.canvas["ord"][r].tolist() if o).rstrip()
            non_box = [ch for ch in text if ch not in _BOX_CHARS]
            if non_box:
                bad.append((c.game.id, r, "non-border chars", non_box[:5]))
                break
        else:
            for r in (1, 2):
                row = "".join(chr(o) for o in c.canvas["ord"][r].tolist() if o)
                if not (row.startswith(_SINGLE_V) or row.startswith(_DOUBLE_V)):
                    bad.append((c.game.id, f"row{r} missing left edge", row[:30]))
                    break
    assert not bad, f"Text/border rows out of spec: {bad}"


# ---------------------------------------------------------------------------
# 3-column grid + full box border (Round 13)
# ---------------------------------------------------------------------------


def test_cards_are_arranged_in_three_columns(app_with_cards):
    """Cards must occupy exactly 3 distinct x-positions (3 columns)."""
    app = app_with_cards
    xs = sorted({c.pos.x for c in app.cards})
    assert len(xs) == 3, f"Expected 3 distinct x positions, got: {xs}"
    # All 32 cards should have one of those x values.
    for c in app.cards:
        assert c.pos.x in xs, f"Card {c.game.id} at unexpected x={c.pos.x}"


def test_every_card_has_full_box_border_on_all_four_sides(app_with_cards):
    """Each card must have box-drawing characters on its left column (col 0)
    and right column (col width-1) as well as its top row (row 0) and bottom
    row (row height-1)."""
    app = app_with_cards
    bad = []
    for c in app.cards:
        h, w = c.size
        # Left edge (col 0) and right edge (col w-1) should contain box chars.
        left_col = "".join(chr(o) for o in c.canvas["ord"][:, 0].tolist() if o)
        right_col = "".join(chr(o) for o in c.canvas["ord"][:, w - 1].tolist() if o)
        top_row = "".join(chr(o) for o in c.canvas["ord"][0].tolist() if o)
        bot_row = "".join(chr(o) for o in c.canvas["ord"][h - 1].tolist() if o)
        for label, text in (
            ("left", left_col),
            ("right", right_col),
            ("top", top_row),
            ("bottom", bot_row),
        ):
            if not any(ch in _BOX_CHARS for ch in text):
                bad.append((c.game.id, label, text[:40]))
                break
    assert not bad, f"Cards without full 4-sided box border: {bad}"


_DOUBLE_LINE = set("═║╔╗╚╝╠╣╦╩")


def test_focused_card_border_uses_double_line_chars(app_with_cards):
    """The focused card's border must use double-line box-drawing characters
    (═, ║, etc.) so it stands out from the blurred cards' single-line border."""
    app = app_with_cards
    card = app.cards[0]
    card.focus()
    # Sample 4 corners + middle of each edge.
    samples = []
    h, w = card.size
    for y, x in (
        (0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1),
        (0, w // 2), (h // 2, 0),
    ):
        ch = chr(int(card.canvas["ord"][y][x]))
        samples.append(ch)
    assert any(ch in _DOUBLE_LINE for ch in samples), (
        f"Focused card should have at least one double-line border char "
        f"(═, ║, ╔, etc.); samples were {samples!r}"
    )


# ---------------------------------------------------------------------------
# 4-row card + 4-direction navigation (Round 14)
# ---------------------------------------------------------------------------


def test_every_card_is_four_rows_tall(app_with_cards):
    """Each GameCard must be 4 rows tall so title and meta each get a row."""
    app = app_with_cards
    bad = []
    for c in app.cards:
        if c.size.height != 4:
            bad.append((c.game.id, c.size))
    assert not bad, f"Cards not 4 rows tall: {bad}"


def test_card_text_fits_within_width(app_with_cards):
    """Row 1 (title) and row 2 (meta) must not contain content past col
    ``width-1`` — every non-trailing-space char must be within the box.
    """
    app = app_with_cards
    bad = []
    for c in app.cards:
        h, w = c.size
        for r in (1, 2):
            ords = c.canvas["ord"][r]
            # The very last column must be a vertical edge char (│ or ║).
            last_ch = chr(int(ords[w - 1]))
            if last_ch not in (_SINGLE_V, _DOUBLE_V):
                bad.append((c.game.id, r, f"col {w - 1} = {last_ch!r}"))
    assert not bad, f"Cards whose row text overflows the box: {bad}"


def test_title_row_contains_only_title_text(app_with_cards):
    """Row 1 must not contain the controls hint ``[click]`` or dependency
    marker ``⚠ ...`` — those belong to the meta row (row 2)."""
    app = app_with_cards
    bad = []
    for c in app.cards:
        row1 = "".join(chr(o) for o in c.canvas["ord"][1].tolist() if o)
        # Strip the left/right edge + arrow + fav/recent stars and check no
        # ``[`` or ``⚠`` survived (controls/deps).
        stripped = row1.lstrip("│║ \u25b6\u2605\u25cf\u25cb").rstrip()
        if "[" in stripped or "\u26a0" in stripped:
            bad.append((c.game.id, row1[:60]))
    assert not bad, f"Title row contains meta markers: {bad}"


def test_left_key_navigates_to_left_card_with_wrap(app_with_cards):
    """Pressing Left from col c row r focuses col c-1 row r, wrapping to col
    max when at col 0."""
    app = app_with_cards
    # Move focus to a middle card first (card 13 is in col 1 row 1 with 11-per-col).
    target_idx = 13
    app.cards[target_idx].focus()
    assert app.cards[target_idx].is_focused

    handled = app.root.dispatch_key(KeyEvent("left"))
    assert handled is True
    focused = next(c for c in app.cards if c.is_focused)
    expected_idx = target_idx - 11  # one col left = 11 cards earlier (column-major)
    assert app.cards.index(focused) == expected_idx, (
        f"Left from idx {target_idx} should focus idx {expected_idx}, "
        f"got idx {app.cards.index(focused)}"
    )

    # From col 0 (idx 0 = col 0 row 0), Left should wrap to col max row 0 = idx 22.
    app.cards[0].focus()
    app.root.dispatch_key(KeyEvent("left"))
    focused = next(c for c in app.cards if c.is_focused)
    assert app.cards.index(focused) == 22, (
        f"Left from idx 0 should wrap to idx 22, got {app.cards.index(focused)}"
    )


def test_right_key_navigates_to_right_card_with_wrap(app_with_cards):
    """Pressing Right mirrors the Left test."""
    from examples.demos import launcher as launcher_mod

    app = app_with_cards
    launcher_mod._PENDING_GAME["value"] = None  # guard against accidental exit

    # From a middle card (idx 13, col 1 row 1), Right should go to idx 24 (col 2 row 1).
    app.cards[13].focus()
    handled = app.root.dispatch_key(KeyEvent("right"))
    assert handled is True
    focused = next(c for c in app.cards if c.is_focused)
    assert app.cards.index(focused) == 24, (
        f"Right from idx 13 should focus idx 24, got {app.cards.index(focused)}"
    )

    # From col max (idx 22 = col 2 row 0), Right should wrap to col 0 row 0 = idx 0.
    app.cards[22].focus()
    app.root.dispatch_key(KeyEvent("right"))
    focused = next(c for c in app.cards if c.is_focused)
    assert app.cards.index(focused) == 0, (
        f"Right from idx 22 should wrap to idx 0, got {app.cards.index(focused)}"
    )
