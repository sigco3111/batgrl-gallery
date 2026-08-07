"""Mini-game catalog — single source of truth for the launcher.

Every entry corresponds to a real package or module under ``examples/advanced``.
The list below is intentionally ordered by category then alphabetical so the
launcher renders groups in a predictable order.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass


@dataclass(frozen=True)
class GameInfo:
    """Immutable description of one mini-game."""

    id: str
    title: str
    title_ko: str
    description: str
    description_ko: str
    module: str
    category: str  # 'puzzle' | 'arcade' | 'simulation' | 'visual'
    controls: str
    deps_status: str  # 'ok' or 'missing: <module>'
    exit_keys: str  # how to quit the game once it is running



def _probe_deps(module: str) -> str:
    """Return 'ok' or 'missing: <modname>' for the game's module."""
    try:
        importlib.import_module(module)
        return "ok"
    except ModuleNotFoundError as exc:
        return f"missing: {exc.name}"
    except ImportError:
        return "ok"

GAMES: list[GameInfo] = [
    GameInfo(
        id="connect4",
        title="Connect Four",
        title_ko="4목",
        description="Drop discs. Get four in a row.",
        description_ko="디스크를 떨어뜨려 4개를 먼저 이어보세요.",
        module="examples.advanced.connect4.connect4",
        category="puzzle",
        controls="",
        deps_status=_probe_deps("examples.advanced.connect4.connect4"),
        exit_keys="",
    ),
    GameInfo(
        id="infinite_tictactoe",
        title="Infinite Tic-Tac-Toe",
        title_ko="무한 틱택토",
        description="Tic-tac-toe without draws.",
        description_ko="무승부 없는 틱택토.",
        module="examples.advanced.infinite_tictactoe",
        category="puzzle",
        controls="",
        deps_status=_probe_deps("examples.advanced.infinite_tictactoe"),
        exit_keys="",
    ),
    GameInfo(
        id="labyrinth",
        title="Labyrinth",
        title_ko="미로",
        description="Navigate a maze.",
        description_ko="미로를 탐험하세요.",
        module="examples.advanced.labyrinth",
        category="puzzle",
        controls="",
        deps_status=_probe_deps("examples.advanced.labyrinth"),
        exit_keys="",
    ),
    GameInfo(
        id="minesweeper",
        title="Minesweeper",
        title_ko="지뢰찾기",
        description="Find mines without detonating.",
        description_ko="지뢰를 피해서 모든 칸을 열어보세요.",
        module="examples.advanced.minesweeper.minesweeper",
        category="puzzle",
        controls="",
        deps_status=_probe_deps("examples.advanced.minesweeper.minesweeper"),
        exit_keys="",
    ),
    GameInfo(
        id="rubiks",
        title="Rubik's Cube",
        title_ko="루빅스 큐브",
        description="Solve the cube.",
        description_ko="큐브를 풀어보세요.",
        module="examples.advanced.rubiks.rubiks",
        category="puzzle",
        controls="",
        deps_status=_probe_deps("examples.advanced.rubiks.rubiks"),
        exit_keys="",
    ),
    GameInfo(
        id="sliding_puzzle",
        title="Sliding Puzzle",
        title_ko="슬라이딩 퍼즐",
        description="Slide tiles into order.",
        description_ko="타일을 밀어서 순서대로 정렬하세요.",
        module="examples.advanced.sliding_puzzle",
        category="puzzle",
        controls="",
        deps_status=_probe_deps("examples.advanced.sliding_puzzle"),
        exit_keys="",
    ),
    GameInfo(
        id="hack",
        title="Hack (Roguelike)",
        title_ko="핵 (로그라이크)",
        description="Explore dungeons.",
        description_ko="던전을 탐험하세요.",
        module="examples.advanced.hack.hack",
        category="arcade",
        controls="",
        deps_status=_probe_deps("examples.advanced.hack.hack"),
        exit_keys="",
    ),
    GameInfo(
        id="pong",
        title="Pong",
        title_ko="퐁",
        description="Classic paddle game.",
        description_ko="클래식 패들 게임.",
        module="examples.advanced.pong",
        category="arcade",
        controls="",
        deps_status=_probe_deps("examples.advanced.pong"),
        exit_keys="",
    ),
    GameInfo(
        id="sandbox",
        title="Sandbox",
        title_ko="샌드박스",
        description="Free-form sandbox.",
        description_ko="자유형 샌드박스.",
        module="examples.advanced.sandbox.sandbox",
        category="arcade",
        controls="",
        deps_status=_probe_deps("examples.advanced.sandbox.sandbox"),
        exit_keys="",
    ),
    GameInfo(
        id="snake",
        title="Snake",
        title_ko="스네이크",
        description="Grow without biting yourself.",
        description_ko="몸을 키우되 자기 자신을 물지 마세요.",
        module="examples.advanced.snake",
        category="arcade",
        controls="",
        deps_status=_probe_deps("examples.advanced.snake"),
        exit_keys="",
    ),
    GameInfo(
        id="tetris",
        title="Tetris",
        title_ko="테트리스",
        description="Stack blocks, clear lines.",
        description_ko="블록을 쌓고 줄 없애기.",
        module="examples.advanced.tetris.tetris",
        category="arcade",
        controls="",
        deps_status=_probe_deps("examples.advanced.tetris.tetris"),
        exit_keys="",
    ),
    GameInfo(
        id="cloth",
        title="Cloth",
        title_ko="천 시뮬레이션",
        description="Cloth physics.",
        description_ko="천 물리 시뮬레이션.",
        module="examples.advanced.cloth",
        category="simulation",
        controls="",
        deps_status=_probe_deps("examples.advanced.cloth"),
        exit_keys="",
    ),
    GameInfo(
        id="game_of_life",
        title="Game of Life",
        title_ko="생명의 게임",
        description="Cellular automaton.",
        description_ko="셀룰러 오토마타.",
        module="examples.advanced.game_of_life",
        category="simulation",
        controls="",
        deps_status=_probe_deps("examples.advanced.game_of_life"),
        exit_keys="",
    ),
    GameInfo(
        id="navier_stokes",
        title="Navier-Stokes",
        title_ko="나비에-스토크스",
        description="Fluid simulation.",
        description_ko="유체 시뮬레이션.",
        module="examples.advanced.navier_stokes",
        category="simulation",
        controls="",
        deps_status=_probe_deps("examples.advanced.navier_stokes"),
        exit_keys="",
    ),
    GameInfo(
        id="raycasting",
        title="Raycasting",
        title_ko="레이캐스팅",
        description="Pseudo-3D raycasting.",
        description_ko="의사 3D 레이캐스팅.",
        module="examples.advanced.raycasting",
        category="simulation",
        controls="",
        deps_status=_probe_deps("examples.advanced.raycasting"),
        exit_keys="",
    ),
    GameInfo(
        id="reaction_diffusion",
        title="Reaction-Diffusion",
        title_ko="반응-확산",
        description="Chemical pattern simulation.",
        description_ko="화학 패턴 시뮬레이션.",
        module="examples.advanced.reaction_diffusion",
        category="simulation",
        controls="",
        deps_status=_probe_deps("examples.advanced.reaction_diffusion"),
        exit_keys="",
    ),
    GameInfo(
        id="shadow_casting",
        title="Shadow Casting",
        title_ko="광선 추적",
        description="Ray-traced shadows.",
        description_ko="광선 추적 그림자.",
        module="examples.advanced.shadow_casting",
        category="simulation",
        controls="",
        deps_status=_probe_deps("examples.advanced.shadow_casting"),
        exit_keys="",
    ),
    GameInfo(
        id="slime",
        title="Slime Mold",
        title_ko="점균 시뮬레이션",
        description="Slime mold behavior.",
        description_ko="점균 행동 시뮬레이션.",
        module="examples.advanced.slime",
        category="simulation",
        controls="",
        deps_status=_probe_deps("examples.advanced.slime"),
        exit_keys="",
    ),
    GameInfo(
        id="sph",
        title="SPH Fluid",
        title_ko="SPH 유체",
        description="Smoothed Particle Hydrodynamics.",
        description_ko="스무스드 파티클 유체역학.",
        module="examples.advanced.sph.sph",
        category="simulation",
        controls="",
        deps_status=_probe_deps("examples.advanced.sph.sph"),
        exit_keys="",
    ),
    GameInfo(
        id="stable_fluid",
        title="Stable Fluid",
        title_ko="안정적 유체",
        description="Stable fluid solver.",
        description_ko="안정적 유체 솔버.",
        module="examples.advanced.stable_fluid",
        category="simulation",
        controls="",
        deps_status=_probe_deps("examples.advanced.stable_fluid"),
        exit_keys="",
    ),
    GameInfo(
        id="digital_clock",
        title="Digital Clock",
        title_ko="디지털 시계",
        description="Stylish digital clock.",
        description_ko="스타일리시 디지털 시계.",
        module="examples.advanced.digital_clock",
        category="visual",
        controls="",
        deps_status=_probe_deps("examples.advanced.digital_clock"),
        exit_keys="",
    ),
    GameInfo(
        id="doom_fire",
        title="Doom Fire",
        title_ko="둠 파이어",
        description="Classic fire effect.",
        description_ko="클래식 파이어 이펙트.",
        module="examples.advanced.doom_fire",
        category="visual",
        controls="",
        deps_status=_probe_deps("examples.advanced.doom_fire"),
        exit_keys="",
    ),
    GameInfo(
        id="exploding_logo",
        title="Exploding Logo",
        title_ko="폭발 로고",
        description="Logo explosion effect.",
        description_ko="로고 폭발 이펙트.",
        module="examples.advanced.exploding_logo",
        category="visual",
        controls="",
        deps_status=_probe_deps("examples.advanced.exploding_logo"),
        exit_keys="",
    ),
    GameInfo(
        id="exploding_logo_redux",
        title="Exploding Logo Redux",
        title_ko="폭발 로고 Redux",
        description="Refined logo explosion.",
        description_ko="개선된 로고 폭발.",
        module="examples.advanced.exploding_logo_redux",
        category="visual",
        controls="",
        deps_status=_probe_deps("examples.advanced.exploding_logo_redux"),
        exit_keys="",
    ),
    GameInfo(
        id="figfonts",
        title="FIGlet Fonts",
        title_ko="FIGlet 폰트",
        description="ASCII art fonts.",
        description_ko="ASCII 아트 폰트.",
        module="examples.advanced.figfonts",
        category="visual",
        controls="",
        deps_status=_probe_deps("examples.advanced.figfonts"),
        exit_keys="",
    ),
    GameInfo(
        id="io_events",
        title="I/O Events",
        title_ko="입출력 이벤트",
        description="Event handling demo.",
        description_ko="이벤트 처리 데모.",
        module="examples.advanced.io_events",
        category="visual",
        controls="",
        deps_status=_probe_deps("examples.advanced.io_events"),
        exit_keys="",
    ),
    GameInfo(
        id="isotiles",
        title="Isometric Tiles",
        title_ko="아이소메트릭 타일",
        description="Isometric tile renderer.",
        description_ko="아이소메트릭 타일 렌더러.",
        module="examples.advanced.isotiles",
        category="visual",
        controls="",
        deps_status=_probe_deps("examples.advanced.isotiles"),
        exit_keys="",
    ),
    GameInfo(
        id="moire",
        title="Moiré",
        title_ko="무아레",
        description="Moiré pattern demo.",
        description_ko="무아레 패턴 데모.",
        module="examples.advanced.moire",
        category="visual",
        controls="",
        deps_status=_probe_deps("examples.advanced.moire"),
        exit_keys="",
    ),
    GameInfo(
        id="palettes",
        title="Palettes",
        title_ko="팔레트",
        description="Color palette viewer.",
        description_ko="색상 팔레트 뷰어.",
        module="examples.advanced.palettes",
        category="visual",
        controls="",
        deps_status=_probe_deps("examples.advanced.palettes"),
        exit_keys="",
    ),
    GameInfo(
        id="pipes",
        title="Pipes",
        title_ko="파이프",
        description="Growing pipes.",
        description_ko="자라나는 파이프.",
        module="examples.advanced.pipes",
        category="visual",
        controls="",
        deps_status=_probe_deps("examples.advanced.pipes"),
        exit_keys="",
    ),
    GameInfo(
        id="plasma_shader",
        title="Plasma Shader",
        title_ko="플라즈마 셰이더",
        description="Plasma waves.",
        description_ko="플라즈마 파동.",
        module="examples.advanced.plasma_shader",
        category="visual",
        controls="",
        deps_status=_probe_deps("examples.advanced.plasma_shader"),
        exit_keys="",
    ),
    GameInfo(
        id="spinning_cube",
        title="Spinning Cube",
        title_ko="회전 큐브",
        description="3D cube in terminal.",
        description_ko="터미널 속 3D 큐브.",
        module="examples.advanced.spinning_cube",
        category="visual",
        controls="",
        deps_status=_probe_deps("examples.advanced.spinning_cube"),
        exit_keys="",
    ),
]


def games_by_category() -> dict[str, list[GameInfo]]:
    """Group games by category, preserving catalog ordering within each group."""
    grouped: dict[str, list[GameInfo]] = {}
    for game in GAMES:
        grouped.setdefault(game.category, []).append(game)
    return grouped


def find_game(game_id: str) -> GameInfo | None:
    """Return the GameInfo for ``game_id`` or None."""
    for game in GAMES:
        if game.id == game_id:
            return game
    return None



def _apply_controls() -> None:
    """Fill the ``controls`` field of every game from the curated map.

    Done in a post-import step because frozen dataclasses forbid direct
    attribute assignment; we reconstruct each entry. The GAMES list order is
    preserved.
    """
    global GAMES
    GAMES = [
        g if g.id not in _CONTROLS else GameInfo(
            id=g.id, title=g.title, title_ko=g.title_ko,
            description=g.description, description_ko=g.description_ko,
            module=g.module, category=g.category,
            controls=_CONTROLS[g.id],
            deps_status=g.deps_status,
            exit_keys=_EXIT_KEYS.get(g.id, "Esc / Ctrl+C"),
        )
        for g in GAMES
    ]


_CONTROLS: dict[str, str] = {
    # see Round 5 patch; populated below for readability.
}


_EXIT_KEYS: dict[str, str] = {
    # see Round 8 patch; populated below for readability.
}


_CONTROLS = {'connect4': 'click', 'infinite_tictactoe': 'click', 'labyrinth': 'click', 'minesweeper': 'click', 'rubiks': 'mouse drag', 'sliding_puzzle': 'click', 'hack': '←→↑↓ g: get', 'pong': '↑↓', 'sandbox': 'click', 'snake': '←→↑↓', 'tetris': '←→↑↓ space', 'cloth': 'click drag', 'game_of_life': 'click', 'navier_stokes': 'click', 'raycasting': '←→↑↓', 'reaction_diffusion': 'click', 'shadow_casting': '←→↑↓', 'slime': 'click', 'sph': 'click', 'stable_fluid': 'click drag', 'digital_clock': 'watch', 'doom_fire': 'watch', 'exploding_logo': 'watch', 'exploding_logo_redux': 'watch', 'figfonts': 'watch', 'io_events': 'keys', 'isotiles': 'click', 'moire': 'watch', 'palettes': 'watch', 'pipes': 'watch', 'plasma_shader': 'watch', 'spinning_cube': 'watch'}


_EXIT_KEYS = {'connect4': 'Esc / Ctrl+C', 'infinite_tictactoe': 'Esc / Ctrl+C', 'labyrinth': 'Esc / Ctrl+C', 'minesweeper': 'Esc / Ctrl+C', 'rubiks': 'Esc / Ctrl+C', 'sliding_puzzle': 'Esc / Ctrl+C', 'hack': 'Esc / Ctrl+C', 'pong': 'Esc / Ctrl+C', 'sandbox': 'Esc / Ctrl+C', 'snake': 'Esc / Ctrl+C', 'tetris': 'Esc / Ctrl+C', 'cloth': 'Esc / Ctrl+C', 'game_of_life': 'Esc / Ctrl+C', 'navier_stokes': 'Esc / Ctrl+C', 'raycasting': 'Esc / Ctrl+C', 'reaction_diffusion': 'Esc / Ctrl+C', 'shadow_casting': 'Esc / Ctrl+C', 'slime': 'Esc / Ctrl+C', 'sph': 'Esc / Ctrl+C', 'stable_fluid': 'Esc / Ctrl+C', 'digital_clock': 'Esc / Ctrl+C', 'doom_fire': 'Esc / Ctrl+C', 'exploding_logo': 'Esc / Ctrl+C', 'exploding_logo_redux': 'Esc / Ctrl+C', 'figfonts': 'Esc / Ctrl+C', 'io_events': 'Esc / Ctrl+C', 'isotiles': 'Esc / Ctrl+C', 'moire': 'Esc / Ctrl+C', 'palettes': 'Esc / Ctrl+C', 'pipes': 'Esc / Ctrl+C', 'plasma_shader': 'Esc / Ctrl+C', 'spinning_cube': 'Esc / Ctrl+C'}


_apply_controls()
