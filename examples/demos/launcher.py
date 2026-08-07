"""batgrl Gallery Launcher - browse and launch every mini-game from one screen.

Usage::

    python -m examples.demos.launcher            # full TUI launcher (needs TTY)
    python -m examples.demos.launcher --dry-run  # list catalog and exit
    python -m examples.demos.launcher tetris     # launch one game directly

The interactive launcher renders a vertical list of ``GameCard`` gadgets,
lets the user navigate with Up/Down, toggles Korean <-> English with ``L``,
launches the highlighted game into a new PTY with Enter, and quits with Esc.

Key dispatch notes
------------------
batgrl routes key events through ``App.root.dispatch_key`` - the gadget tree
itself, not the ``App`` instance. Only the focused gadget receives key events,
so each ``GameCard`` handles its own ``Up``/``Down``/``Enter``/``L``/``Esc``.
Cards know their 4 neighbors (``left_card``/``right_card``/
``up_card``/``down_card``) computed from the grid coordinates. Navigation wraps
around at row and column edges.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from typing import Any

from batgrl.app import App
from batgrl.colors import BLACK, Color, WHITE
from batgrl.gadgets.behaviors.focusable import Focusable
from batgrl.gadgets.gadget import Gadget
from batgrl.gadgets.grid_layout import GridLayout
from batgrl.gadgets.text import Text

from examples.demos import storage
from examples.demos.catalog import GAMES, GameInfo, find_game, games_by_category
from examples.demos.locales import en, ko


_LANG = {"current": "ko"}
"""Mutable cell tracking the active locale code (``"ko"`` or ``"en"``)."""

_PENDING_GAME: dict[str, str | None] = {"value": None}
"""Mutable cell: when Enter is pressed, the focused game id is recorded here
so the ``main()`` loop can spawn it after the App has exited and the terminal
has been restored. Blocking on the child inside the event loop would freeze
the launcher because the child would write to a private PTY invisible to
the user; exiting first lets us spawn with inherited stdio instead.
"""

_FOCUSED_BG: Color = Color(40, 60, 130)
_FOCUSED_FG: Color = Color(255, 255, 255)
_UNFOCUSED_BG: Color = Color(0, 0, 0)
_UNFOCUSED_FG: Color = WHITE

# Per-category colors. Each tuple is (focused_bg, focused_fg, blurred_bg).
# Slightly desaturated so the foreground text remains readable.
CATEGORY_FOCUSED_BG: dict[str, Color] = {
    "puzzle":     Color(30,  70, 130),  # deep blue
    "arcade":     Color(130, 30,  30),  # deep red
    "simulation": Color(20, 100,  90),  # teal
    "visual":     Color(90,  30, 110),  # purple
}
CATEGORY_FOCUSED_FG: dict[str, Color] = {
    "puzzle":     Color(255, 255, 255),
    "arcade":     Color(255, 255, 255),
    "simulation": Color(255, 255, 255),
    "visual":     Color(255, 255, 255),
}
CATEGORY_BLURRED_BG: dict[str, Color] = {
    "puzzle":     Color(10, 20,  35),
    "arcade":     Color(35, 10,  10),
    "simulation": Color(8,  25,  22),
    "visual":     Color(22, 10,  28),
}

_ARROW = "\u25b6"  # selection arrow rendered on the focused card

_FILTER_STATE: dict[str, str | None] = {"current": None}
"""Mutable cell: ``None`` means show all categories, otherwise the category
name (e.g. ``"puzzle"``) when filtered. The GalleryApp reads this on filter
key presses and refreshes the card visibility + header text."""

_SEARCH_STATE: dict[str, Any] = {"active": False, "query": ""}
"""Mutable cell: when ``active`` is True the user is typing a search query;
``query`` accumulates characters and is applied as a live title-substring
filter on the card list. Esc clears both fields."""

_FAVORITES: set[str] = set()
"""Mutable set of favorited game ids. Mirrored to disk by ``_save_state``.
The fixture's ``_reset_locale`` and explicit test setup control this set."""

_FAVORITES_ONLY: dict[str, bool] = {"on": False}
"""Mutable cell: when True only favorited games are visible. Toggled by ``5``."""

# Initial state populated from disk on module import; tests may overwrite.
_INITIAL_STATE = storage.load_state()
_FAVORITES.update(_INITIAL_STATE["favorites"])
_RECENT: dict[str, list[dict[str, Any]]] = {"history": _INITIAL_STATE["recent"]}


def _save_state() -> None:
    """Persist current favorites + recent to disk."""
    try:
        storage.save_state(
            {"favorites": sorted(_FAVORITES), "recent": _RECENT["history"]}
        )
    except OSError:
        # Non-fatal: in-memory state is still correct for this session.
        pass


def labels() -> dict[str, str]:
    """Return the label dict for the currently active locale."""
    return ko.LABELS if _LANG["current"] == "ko" else en.LABELS


def category_label(cat: str) -> str:
    return labels()[f"category_{cat}"]


def _matches_filters(game: GameInfo) -> bool:
    """Return True if ``game`` passes all active filters (category + search + favorites-only)."""
    cat = _FILTER_STATE["current"]
    if cat is not None and game.category != cat:
        return False
    query = _SEARCH_STATE["query"]
    if query:
        hay = (game.title_ko + " " + game.title + " " + game.description_ko + " " + game.description).lower()
        if query.lower() not in hay:
            return False
    if _FAVORITES_ONLY["on"] and game.id not in _FAVORITES:
        return False
    return True


def _recent_marker(game_id: str) -> str:
    """Return a bullet ``\u25cf`` if the game was played in the last 24h, else ``\u25cb`` for the last week, else empty."""
    import time as _time
    now = _time.time()
    for entry in _RECENT["history"]:
        if entry.get("id") == game_id:
            age = now - entry.get("ts", 0.0)
            if age < 86400:  # 24h
                return "\u25cf"
            if age < 86400 * 7:
                return "\u25cb"
            return ""
    return ""


# Box-drawing characters for a single-line card border (blurred cards).
_SINGLE_H = "\u2500"             # ─
_SINGLE_V = "\u2502"             # │
_SINGLE_TL = "\u250c"            # ┌
_SINGLE_TR = "\u2510"            # ┐
_SINGLE_BL = "\u2514"            # └
_SINGLE_BR = "\u2518"            # ┘

# Box-drawing characters for a double-line card border (focused cards).
_DOUBLE_H = "\u2550"             # ═
_DOUBLE_V = "\u2551"             # ║
_DOUBLE_TL = "\u2554"            # ╔
_DOUBLE_TR = "\u2557"            # ╗
_DOUBLE_BL = "\u255a"            # ╚
_DOUBLE_BR = "\u255d"            # ╝


def _format_card_box(width: int, height: int, focused: bool = False) -> tuple[list[str], Color]:
    """Return (rows, border_color) for a full 4-sided box of (height, width).

    Each row is exactly ``width`` cells. Border chars are on all 4 edges:
    corners on rows 0 and ``height - 1``, vertical strokes on the leftmost and
    rightmost columns of every intermediate row. Focused cards use the double
    line; blurred cards use the single line. Inside the box is filled with
    spaces so the rest of the card's content can be written over it.
    """
    if focused:
        h, v, tl, tr, bl, br = (_DOUBLE_H, _DOUBLE_V, _DOUBLE_TL, _DOUBLE_TR, _DOUBLE_BL, _DOUBLE_BR)
        color = WHITE
    else:
        h, v, tl, tr, bl, br = (_SINGLE_H, _SINGLE_V, _SINGLE_TL, _SINGLE_TR, _SINGLE_BL, _SINGLE_BR)
        color = Color(140, 140, 160)
    top = tl + (h * (width - 2)) + tr
    bot = bl + (h * (width - 2)) + br
    middle = v + (" " * (width - 2)) + v
    rows = [top] + [middle] * (height - 2) + [bot]
    return rows, color


def _format_card_lines(
    game: GameInfo,
    focused: bool = False,
    width: int = 80,
    height: int = 4,
) -> tuple[list[str], Color, Color]:
    """Render the card's rows with full 4-sided box border.

    Returns ``(rows, text_color, border_color)``. For a 4-row card:
      row 0: top border
      row 1: title (▶ title + ★ + ● markers)
      row 2: meta line ([controls] + ⚠ missing)
      row 3: bottom border

    The card width is 26 cols; with 2 vertical edges + arrow/markers, the
    title row fits ~20 chars, the meta row fits ~22 chars. Anything longer is
    truncated by ljust+[:width].
    """
    if _LANG["current"] == "ko":
        title = game.title_ko
    else:
        title = game.title
    arrow = f"{_ARROW} " if focused else "  "
    fav = " ★" if game.id in _FAVORITES else ""
    recent = f" {_recent_marker(game.id)}" if _recent_marker(game.id) else ""
    meta = f"[{game.controls}]"
    if game.deps_status != "ok":
        missing = game.deps_status.split(":", 1)[-1].strip()
        meta += f" ⚠ {missing}"
    text_color = WHITE
    border_rows, border_color = _format_card_box(width, height, focused=focused)
    v_edge = _DOUBLE_V if focused else _SINGLE_V
    rows = list(border_rows)
    # Build title/meta rows. Each row uses left edge + content + right edge,
    # but the Korean character shifts the display width by 1, so the right
    # edge is added as a separate string so batgrl doesn't truncate it.
    title_content = f" {arrow}{title}{fav}{recent} "
    rows[1] = v_edge + title_content
    meta_content = f" {meta} "
    rows[2] = v_edge + meta_content
    # For taller cards (height >= 5), blank rows between row 2 and bottom.
    if height >= 5:
        for r in range(3, height - 1):
            rows[r] = v_edge + (" " * (width - 2)) + v_edge
    return rows, text_color, border_color
    """Render the card's rows with full 4-sided box border.

    Returns ``(rows, text_color, border_color)``. Rows: top border, title row,
    bottom border (height=3). For taller cards, description goes in row 2.
    """
    if _LANG["current"] == "ko":
        title = game.title_ko
        desc = game.description_ko
    else:
        title = game.title
        desc = game.description
    arrow = f"{_ARROW} " if focused else "  "
    fav = "  \u2605" if game.id in _FAVORITES else ""
    recent = f"  {_recent_marker(game.id)}" if _recent_marker(game.id) else ""
    controls = f"  [{game.controls}]"
    if game.deps_status != "ok":
        missing = game.deps_status.split(":", 1)[-1].strip()
        controls += f"  \u26a0 {missing}"
    text_color = WHITE
    border_rows, border_color = _format_card_box(width, height, focused=focused)
    # Vertical edge character depends on focus state for the inside rows.
    v_edge = _DOUBLE_V if focused else _SINGLE_V
    rows = list(border_rows)
    # For taller cards (height >= 5), blank rows between row 2 and bottom.
    if height >= 5:
        for r in range(3, height - 1):
            rows[r] = v_edge + (" " * (width - 2)) + v_edge
    return rows, text_color, border_color


class GameCard(Focusable, Text):
    """One cell in the 3-column catalog grid. Handles its own navigation keys.

    Layout (4 rows, width 26):
      row 0: top border (┌──...──┐ / ╔══...══╗)
      row 1: title (▶ title  ★ ●)
      row 2: meta line ([controls]  ⚠ missing)
      row 3: bottom border (└──...──┘ / �══...══╝)

    Four-direction neighbors (left_card/right_card/up_card/down_card) are set
    by GalleryApp.on_start so Up/Down/Left/Right wrap around grid edges.
    """

    def __init__(
        self,
        game: GameInfo,
        left_card: "GameCard | None" = None,
        right_card: "GameCard | None" = None,
        up_card: "GameCard | None" = None,
        down_card: "GameCard | None" = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.game = game
        self.left_card = left_card
        self.right_card = right_card
        self.up_card = up_card
        self.down_card = down_card
        self._apply_text()

    def _apply_text(self) -> None:
        self.clear()
        rows, text_color, border_color = _format_card_lines(
            self.game,
            focused=self.is_focused,
            width=self.size.width,
            height=self.size.height,
        )
        v_edge = _DOUBLE_V if self.is_focused else _SINGLE_V
        for r, row_text in enumerate(rows):
            # Add the row text. For non-border rows the trailing v_edge
            # would be truncated when content contains wide (Korean) chars,
            # so we explicitly set canvas col (width-1) to the edge char.
            self.add_str(
                row_text, pos=(r, 0), fg_color=border_color, truncate_str=True
            )
            if 0 < r < self.size.height - 1:
                self.canvas["ord"][r][self.size.width - 1] = ord(v_edge)
                self.canvas["fg_color"][r][self.size.width - 1] = border_color

    def on_focus(self) -> None:
        cat = self.game.category
        self.default_bg_color = CATEGORY_FOCUSED_BG.get(cat, _FOCUSED_BG)
        self.default_fg_color = CATEGORY_FOCUSED_FG.get(cat, _FOCUSED_FG)
        self._apply_text()
        # Refresh sidebar whenever focus changes (best-effort: app may not
        # be wired yet during the first focus() inside on_start).
        app = getattr(self, "app", None)
        if app is not None and getattr(app, "_refresh_sidebar", None):
            app._refresh_sidebar()

    def on_blur(self) -> None:
        cat = self.game.category
        self.default_bg_color = CATEGORY_BLURRED_BG.get(cat, _UNFOCUSED_BG)
        self.default_fg_color = _UNFOCUSED_FG
        self._apply_text()

    def _toggle_language(self) -> None:
        _LANG["current"] = "en" if _LANG["current"] == "ko" else "ko"
        # Re-render every card by iterating the app's cards list directly.
        for card in self.app.cards:
            card._apply_text()
        # Refresh header + footer in the new locale.
        self.app._refresh_header(self.app.header)
        self.app._refresh_footer(self.app.footer)

    def on_key(self, key_event) -> bool | None:
        key = key_event.key

        # Search-mode intercept: every printable key (including backspace) edits the
        # live filter; only Esc and Enter exit the mode.
        if _SEARCH_STATE["active"]:
            if key == "escape":
                _SEARCH_STATE["active"] = False
                _SEARCH_STATE["query"] = ""
                self.app._apply_visibility()
                self.app._refresh_header(self.app.header)
                return True
            if key == "enter":
                _SEARCH_STATE["active"] = False
                _PENDING_GAME["value"] = self.game.id
                self.app.exit()
                return True
            if key == "backspace":
                _SEARCH_STATE["query"] = _SEARCH_STATE["query"][:-1]
                self.app._apply_visibility()
                self.app._refresh_header(self.app.header)
                return True
            if isinstance(key, str) and len(key) == 1 and key.isprintable():
                _SEARCH_STATE["query"] += key
                self.app._apply_visibility()
                self.app._refresh_header(self.app.header)
                return True
            return False

        if key == "escape":
            self.app.exit()
            return True
        if key == "l":
            self._toggle_language()
            return True
        if key == "/":
            _SEARCH_STATE["active"] = True
            _SEARCH_STATE["query"] = ""
            self.app._refresh_header(self.app.header)
            return True
        if key == "f":
            if self.game.id in _FAVORITES:
                _FAVORITES.discard(self.game.id)
            else:
                _FAVORITES.add(self.game.id)
            _save_state()
            self._apply_text()
            self.app._apply_visibility()
            self.app._refresh_sidebar()
            return True
        if key == "5":
            _FAVORITES_ONLY["on"] = not _FAVORITES_ONLY["on"]
            self.app._apply_visibility()
            self.app._refresh_header(self.app.header)
            return True
        if key == "0":
            # "0" resets every filter to defaults: show all categories, exit
            # favorites-only mode, and cancel any active search.
            _FILTER_STATE["current"] = None
            _FAVORITES_ONLY["on"] = False
            _SEARCH_STATE["active"] = False
            _SEARCH_STATE["query"] = ""
            self.app._apply_visibility()
            self.app._refresh_header(self.app.header)
            return True
        if key in ("1", "2", "3", "4"):
            self.app._apply_filter(_FILTER_FROM_KEY.get(key))
            return True
        if key == "enter":
            _PENDING_GAME["value"] = self.game.id
            self.app.exit()
            return True
        if key == "up":
            if self.up_card is not None:
                self.up_card.focus()
            return True
        if key == "down":
            if self.down_card is not None:
                self.down_card.focus()
            return True
        if key == "left":
            if self.left_card is not None:
                self.left_card.focus()
            return True
        if key == "right":
            if self.right_card is not None:
                self.right_card.focus()
            return True
        return None


_FILTER_FROM_KEY: dict[str, str | None] = {
    "0": None,         # all categories
    "1": "puzzle",
    "2": "arcade",
    "3": "simulation",
    "4": "visual",
}


class GalleryApp(App):
    """Main launcher screen."""

    async def on_start(self) -> None:
        self.title = labels()["app_title"]

        self.cards: list[GameCard] = []
        # Layout constants: 3-column grid, each card is (CARD_H, CARD_W).
        # CARD_H = 4 to fit top border / title row / meta row / bottom border.
        self.num_columns = 3
        self.card_rows = (len(GAMES) + self.num_columns - 1) // self.num_columns  # ceil
        CARD_W = 80 // self.num_columns  # 26
        CARD_H = 4

        for i, game in enumerate(GAMES):
            card = GameCard(game, size=(CARD_H, CARD_W))
            self.cards.append(card)
        # Wire 4-direction neighbors from grid coordinates (column-major fill
        # matching the GridLayout orientation).
        n = len(self.cards)
        rows = self.card_rows
        cols = self.num_columns
        for i, card in enumerate(self.cards):
            # GridLayout is column-major: cards 0..rows-1 fill col 0,
            # cards rows..2*rows-1 fill col 1, etc.
            col = i // rows
            row = i % rows
            # left: prev col in same row (wrap to last col if col == 0)
            left_col = (col - 1) % cols
            left_idx = left_col * rows + row
            card.left_card = self.cards[left_idx] if left_idx < n else None
            # right
            right_col = (col + 1) % cols
            right_idx = right_col * rows + row
            card.right_card = self.cards[right_idx] if right_idx < n else None
            # up
            up_row = (row - 1) % rows
            up_idx = col * rows + up_row
            card.up_card = self.cards[up_idx] if up_idx < n else None
            # down
            down_row = (row + 1) % rows
            down_idx = col * rows + down_row
            card.down_card = self.cards[down_idx] if down_idx < n else None

        self.header = Text(size=(1, 80), pos=(0, 0))
        self._refresh_header(self.header)

        stack = GridLayout(
            grid_rows=self.card_rows,
            grid_columns=self.num_columns,
            orientation="tb-lr",
            size=(CARD_H * self.card_rows, 80),
            pos=(2, 0),
            is_transparent=True,
        )
        for card in self.cards:
            stack.add_gadget(card)
        self.stack = stack

        # Sidebar on the right (cols 80..160).
        self.sidebar = Text(size=(40, 40), pos=(2, 82))

        self.footer = Text(size=(1, 80), pos=(-1, 0))
        self._refresh_footer(self.footer)

        self.add_gadgets(self.header, stack, self.footer, self.sidebar)
        self._apply_visibility()
        self._refresh_sidebar()
        self.cards[0].focus()

    def _refresh_header(self, widget: Text) -> None:
        widget.clear()
        l = labels()
        if _SEARCH_STATE["active"]:
            widget.add_str(l["search_prompt"].format(q=_SEARCH_STATE["query"] + "_"))
            return
        parts = [l["app_title"]]
        if _FAVORITES_ONLY["on"]:
            parts.append(l["favorite_filter"])
        elif _FILTER_STATE["current"] is None:
            parts.append(l["filter_all"])
        else:
            parts.append(l["filter_only"].format(
                cat=category_label(_FILTER_STATE["current"])
            ))
        visible_count = sum(1 for c in self.cards if c.is_visible)
        widget.add_str(
            f"=== {' | '.join(parts)} === ({visible_count}/{len(GAMES)})"
        )

    def _refresh_footer(self, widget: Text) -> None:
        widget.clear()
        l = labels()
        line = (
            f"{l['press_up_down']}  |  {l['press_enter']}  |  "
            f"{l['press_esc']}  |  {l['press_l']}  |  {l['filter_hint']}  |  /: search  |  f: fav  |  5: fav-only"
        )
        widget.add_str(line, truncate_str=True)

    def _apply_filter(self, category: str | None) -> None:
        """Show only cards matching ``category`` (or all when ``None``)."""
        _FILTER_STATE["current"] = category
        self._apply_visibility()
        self._refresh_header(self.header)

    def _apply_visibility(self) -> None:
        """Recompute every card's visibility against the composite filter."""
        for card in self.cards:
            card.is_visible = _matches_filters(card.game)

    def _refresh_sidebar(self) -> None:
        """Re-render the right-hand sidebar for the currently focused game."""
        self.sidebar.clear()
        l = labels()
        focused = next(
            (c.game for c in self.cards if c.is_focused),
            self.cards[0].game,
        )
        title = focused.title_ko if _LANG["current"] == "ko" else focused.title
        desc = (
            focused.description_ko if _LANG["current"] == "ko" else focused.description
        )
        rows = [
            f"=== {l['sidebar_title']} ===",
            "",
            title,
            f"[{focused.category}]",
            "",
            desc,
            "",
            f"{l['sidebar_controls']}: {focused.controls}",
            f"[{l['sidebar_exit']}: {focused.exit_keys}]",
        ]
        if focused.deps_status == "ok":
            rows.append(f"{l['sidebar_deps']}: {l['sidebar_deps_ok']}")
        else:
            missing = focused.deps_status.split(":", 1)[-1].strip()
            rows.append(f"{l['sidebar_deps']}: ⚠ {missing}")
        # Recent / favorite status.
        last_played = next(
            (e for e in _RECENT["history"] if e.get("id") == focused.id), None
        )
        if last_played is None:
            rows.append(f"{l['sidebar_recent']}: {l['sidebar_never']}")
        else:
            import time as _time
            age = _time.time() - last_played.get("ts", 0.0)
            if age < 60:
                rows.append(f"{l['sidebar_recent']}: {l['recent_just_now']}")
            elif age < 86400:
                rows.append(f"{l['sidebar_recent']}: {l['recent_today']}")
            elif age < 86400 * 7:
                rows.append(f"{l['sidebar_recent']}: {l['recent_this_week']}")
            else:
                rows.append(f"{l['sidebar_recent']}: {int(age // 86400)}d ago")
        if focused.id in _FAVORITES:
            rows.append(f"★ {l['favorited']}")
        for i, row in enumerate(rows):
            self.sidebar.add_str(row, pos=(i, 0), truncate_str=True)


def _restore_screen() -> None:
    """Best-effort cleanup of alt-screen state after a child exits."""
    sys.stdout.write("\033[?1049l")
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def launch_game(game: GameInfo) -> None:
    """Spawn ``game.module`` with inherited stdio and block until it exits.

    Called from the CLI ``main()`` path after the launcher App has exited and
    the terminal has been restored. Inheriting stdio means the child takes over
    the user's real terminal (alt-screen, raw mode, key echo) directly, which
    is what batgrl games require.

    If the module import fails (missing optional dependency such as ``networkx``,
    ``scipy``, or ``moderngl``), the child exits non-zero with a clear error and
    we return to the launcher so the user can pick another game.
    """
    proc = subprocess.run([sys.executable, "-m", game.module], check=False)
    if proc.returncode != 0:
        sys.stderr.write(
            f"\n[launcher] {game.title_ko} ({game.module}) exited "
            f"with code {proc.returncode}. Press Enter to return to the launcher...\n"
        )
        try:
            input()
        except EOFError:
            pass


def _print_catalog() -> None:
    print(f"=== {labels()['app_title']} === ({len(GAMES)} games)")
    for category, games in games_by_category().items():
        print(f"\n[{category_label(category)}]")
        for g in games:
            print(f"  - {g.title_ko} ({g.title})  ->  python -m {g.module}")
    print(f"\n{labels()['goodbye']}")


def _has_real_tty() -> bool:
    """Return True if stdin/stdout are real terminals supporting termios raw mode.

    batgrl's interactive mode requires more than just an isatty()-true stream:
    the underlying file descriptor must allow ``tcgetattr`` AND ``tcsetattr``.
    Some PTY sandboxes pass ``isatty()`` but reject termios calls, so we
    round-trip the attributes before trusting the environment.
    """
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return False
    try:
        import termios

        fd = sys.stdin.fileno()
        saved = termios.tcgetattr(fd)
        try:
            termios.tcsetattr(fd, termios.TCSANOW, saved)
        except termios.error:
            return False
        return True
    except (termios.error, OSError, ImportError):
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m examples.demos.launcher",
        description="batgrl Gallery launcher - browse and run every mini-game.",
    )
    parser.add_argument(
        "game_id",
        nargs="?",
        default=None,
        help="Launch a single game by id (e.g. tetris). Skip to open the launcher UI.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the catalog and exit. Does not require a TTY.",
    )
    parser.add_argument(
        "--lang",
        choices=("ko", "en"),
        default=None,
        help="Override the default Korean locale for this run.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="(Deprecated; ignored in interactive mode.)",
    )
    args = parser.parse_args(argv)

    if args.lang is not None:
        _LANG["current"] = args.lang

    if args.dry_run:
        _print_catalog()
        return 0

    # One-shot CLI launch: run a single game immediately with inherited stdio
    # (the user invoked us directly with a game id, so no launcher UI).
    if args.game_id is not None:
        game = find_game(args.game_id)
        if game is None:
            print(labels()["unknown_game"].format(id=args.game_id), file=sys.stderr)
            return 2
        print(f"{labels()['launching']} {game.title_ko if _LANG['current'] == 'ko' else game.title}")
        launch_game(game)
        return 0

    if not _has_real_tty():
        print(labels()["tty_required"], file=sys.stderr)
        return 1

    # Interactive launcher loop: run the App, check if a game was selected,
    # spawn it with inherited stdio, then re-enter the launcher. Repeat until
    # the user presses Esc (no pending game) or runs out of games.
    while True:
        _PENDING_GAME["value"] = None
        GalleryApp(title=labels()["app_title"]).run()
        game_id = _PENDING_GAME["value"]
        if game_id is None:
            return 0
        game = find_game(game_id)
        if game is None:
            print(labels()["unknown_game"].format(id=game_id), file=sys.stderr)
            return 2
        print(
            f"{labels()['launching']} "
            f"{game.title_ko if _LANG['current'] == 'ko' else game.title}"
        )
        launch_game(game)
        # Record this launch in the recent history and persist state.
        new_state = storage.add_recent(
            {"favorites": sorted(_FAVORITES), "recent": _RECENT["history"]},
            game_id,
        )
        _RECENT["history"] = new_state["recent"]
        _save_state()


if __name__ == "__main__":
    raise SystemExit(main())
