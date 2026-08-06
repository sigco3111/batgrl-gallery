# batgrl-gallery 핸드오프 — 미니게임 컬렉션 Launcher 작업 지시서

> 다른 에이전트/세션에서 이 문서만 보고 즉시 작업을 이어갈 수 있도록 작성된 핸드오프.
> 모든 결정·함정·검증 기준이 이 문서 안에 있음.

---

## 1. 한 줄 요약

`salt-die/batgrl` (MIT, Python TUI 그래픽 라이브러리)을 **한국어 라벨 + 미니게임 통합 Launcher**로 확장한 독립 저장소. upstream PR 안 보냄, sigco3111/batgrl-gallery에서 단독 운영.

---

## 2. 저장소 상태

| 항목 | 값 |
|---|---|
| 로컬 경로 | `~/work/batgrl-gallery` |
| GitHub | `sigco3111/batgrl-gallery` (생성 예정, 아직 안 됨) |
| 원본 | `https://github.com/salt-die/batgrl` @ commit `8aa9736f` |
| 라이선스 | MIT (원본 유지) |
| Python | 3.9+ |
| 핵심 의존성 | Cython, numpy, uwcwidth, packaging |
| 빌드 | `pip install -e .` (Cython 컴파일 필요) |

---

## 3. 완료 작업 (이미 됨)

- [x] 원본 클론 (2026-08-08, commit `8aa9736f`)
- [x] 로컬에서 `salt-die/batgrl` 그대로 복사
- [x] HANDOFF.md 작성 (이 문서)
- [ ] `examples/demos/__init__.py` 빈 파일 생성 — **다음 에이전트가 시작점**
- [ ] `examples/demos/launcher.py` 본체 — **다음 에이전트 메인 작업**
- [ ] `examples/demos/locales/ko.py` 한국어 dict — **다음 에이전트 보조 작업**
- [ ] `examples/demos/locales/en.py` 영어 dict — **다음 에이전트 보조 작업**
- [ ] README.md 재작성 (한국어 + 원본 attribution + 빌드 가이드) — **다음 에이전트 마무리**
- [ ] sigco3111/batgrl-gallery GitHub 푸시 — **본 세션이 진행 예정**
- [ ] PR 안 보냄 (독립 fork)

---

## 4. 다음 작업 (구체 지시)

### 4.1 목표

`python -m examples.demos.launcher` 한 줄로 **모든 미니게임을 한 화면에서 둘러보고 즉시 실행**할 수 있는 TUI Launcher를 추가한다. 한국어/영어 토글 지원.

### 4.2 산출물 구조

```
examples/
├── demos/                          # [신규]
│   ├── __init__.py                 # 빈 파일
│   ├── launcher.py                 # 메인 launcher 앱
│   ├── locales/
│   │   ├── __init__.py             # 빈 파일
│   │   ├── en.py                   # 영어 라벨 dict
│   │   └── ko.py                   # 한국어 라벨 dict
│   └── catalog.py                  # 32개 게임 메타데이터
```

### 4.3 검증 기준 (Phase별)

| Phase | 검증 |
|---|---|
| Phase A (catalog) | `python -c "from examples.demos.catalog import GAMES; print(len(GAMES))"` → `32` |
| Phase B (locales) | `python -c "from examples.demos.locales.ko import LABELS; print(LABELS['tetris'])"` → `'테트리스'` |
| Phase C (launcher dry run) | `python -m examples.demos.launcher --dry-run` → 게임 리스트 + 한국어/영어 토글 시연 후 종료 |
| Phase D (launcher 실행) | `python -m examples.demos.launcher` → 좌측 카드 리스트 표시, Enter로 선택한 게임 subprocess 실행, ESC로 launcher 종료 후 게임 PTY 종료 |

### 4.4 핵심 디자인 결정

| 결정 | 선택 | 이유 |
|---|---|---|
| 멀티뷰 vs Launcher | **Launcher (옵션 A)** | 미니게임마다 다른 키 바인딩/사이즈 → 한 화면 동시 렌더 어려움 |
| 게임 실행 방식 | **subprocess + PTY** | batgrl App은 screen takeover라 인앱 멀티플렉싱 불가 |
| 한국어/영어 토글 | **단축키 'L'** | 한 화면 안에서 즉시 전환, dict 2개 swap |
| 카탈로그 데이터 | **catalog.py (단일 SSoT)** | 게임 정보/한국어/영어 한 곳에 집중 |

---

## 5. bite-sized Plan (다른 에이전트용 복붙 코드)

### Task 1 — 디렉토리/스캐폴드

```bash
cd ~/work/batgrl-gallery
mkdir -p examples/demos/locales
touch examples/demos/__init__.py examples/demos/locales/__init__.py
```

### Task 2 — `examples/demos/catalog.py` (32개 게임 메타데이터)

```python
"""미니게임 카탈로그 — Launcher가 표시하는 모든 게임 정보의 SSoT."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GameInfo:
    id: str            # 영문 ID
    title: str         # 영문 제목 (locales/en.py 키)
    title_ko: str      # 한국어 제목
    description: str   # 영문 설명
    description_ko: str  # 한국어 설명
    module: str        # 실행할 모듈 경로 (python -m <module>)
    category: str      # 'puzzle' | 'arcade' | 'simulation' | 'visual'


# 32개 게임 정의 — examples/advanced/ 디렉토리 기준
GAMES: list[GameInfo] = [
    # ── puzzle ──
    GameInfo("connect4", "Connect Four", "4목",
             "Drop discs. Get four in a row.",
             "디스크를 떨어뜨려 4개를 먼저 이어보세요.",
             "examples.advanced.connect4", "puzzle"),
    GameInfo("sliding_puzzle", "Sliding Puzzle", "슬라이딩 퍼즐",
             "Slide tiles into order.",
             "타일을 밀어서 순서대로 정렬하세요.",
             "examples.advanced.sliding_puzzle", "puzzle"),
    GameInfo("rubiks", "Rubik's Cube", "루빅스 큐브",
             "Solve the cube.",
             "큐브를 풀어보세요.",
             "examples.advanced.rubiks", "puzzle"),
    GameInfo("minesweeper", "Minesweeper", "지뢰찾기",
             "Find mines without detonating.",
             "지뢰를 피해서 모든 칸을 열어보세요.",
             "examples.advanced.minesweeper", "puzzle"),
    GameInfo("infinite_tictactoe", "Infinite Tic-Tac-Toe", "무한 틱택토",
             "Tic-tac-toe without draws.",
             "무승부 없는 틱택토.",
             "examples.advanced.infinite_tictactoe", "puzzle"),
    GameInfo("labyrinth", "Labyrinth", "미로",
             "Navigate a maze.",
             "미로를 탐험하세요.",
             "examples.advanced.labyrinth", "puzzle"),

    # ── arcade ──
    GameInfo("tetris", "Tetris", "테트리스",
             "Stack blocks, clear lines.",
             "블록 쌓고 줄 없애기.",
             "examples.advanced.tetris", "arcade"),
    GameInfo("snake", "Snake", "스네이크",
             "Grow without biting yourself.",
             "몸을 키우되 자기 자신을 물지 마세요.",
             "examples.advanced.snake", "arcade"),
    GameInfo("pong", "Pong", "퐁",
             "Classic paddle game.",
             "클래식 패들 게임.",
             "examples.advanced.pong", "arcade"),
    GameInfo("hack", "Hack (Roguelike)", "핵 (로그라이크)",
             "Explore dungeons.",
             "던전을 탐험하세요.",
             "examples.advanced.hack", "arcade"),
    GameInfo("sandbox", "Sandbox", "샌드박스",
             "Free-form sandbox.",
             "자유형 샌드박스.",
             "examples.advanced.sandbox", "arcade"),

    # ── simulation ──
    GameInfo("game_of_life", "Game of Life", "생명의 게임",
             "Cellular automaton.",
             "셀룰러 오토마타.",
             "examples.advanced.game_of_life", "simulation"),
    GameInfo("navier_stokes", "Navier-Stokes", "나비에-스토크스",
             "Fluid simulation.",
             "유체 시뮬레이션.",
             "examples.advanced.navier_stokes", "simulation"),
    GameInfo("stable_fluid", "Stable Fluid", "안정적 유체",
             "Stable fluid solver.",
             "안정적 유체 솔버.",
             "examples.advanced.stable_fluid", "simulation"),
    GameInfo("reaction_diffusion", "Reaction-Diffusion", "반응-확산",
             "Chemical pattern simulation.",
             "화학 패턴 시뮬레이션.",
             "examples.advanced.reaction_diffusion", "simulation"),
    GameInfo("slime", "Slime Mold", "점균 시뮬레이션",
             "Slime mold behavior.",
             "점균 행동 시뮬레이션.",
             "examples.advanced.slime", "simulation"),
    GameInfo("shadow_casting", "Shadow Casting", "광선 추적",
             "Ray-traced shadows.",
             "광선 추적 그림자.",
             "examples.advanced.shadow_casting", "simulation"),
    GameInfo("raycasting", "Raycasting", "레이캐스팅",
             "Pseudo-3D raycasting.",
             "의사 3D 레이캐스팅.",
             "examples.advanced.raycasting", "simulation"),
    GameInfo("cloth", "Cloth", "천 시뮬레이션",
             "Cloth physics.",
             "천 물리 시뮬레이션.",
             "examples.advanced.cloth", "simulation"),
    GameInfo("sph", "SPH Fluid", "SPH 유체",
             "Smoothed Particle Hydrodynamics.",
             "스무스드 파티클 유체역학.",
             "examples.advanced.sph", "simulation"),

    # ── visual ──
    GameInfo("doom_fire", "Doom Fire", "둠 파이어",
             "Classic fire effect.",
             "클래식 파이어 이펙트.",
             "examples.advanced.doom_fire", "visual"),
    GameInfo("plasma_shader", "Plasma Shader", "플라즈마 셰이더",
             "Plasma waves.",
             "플라즈마 파동.",
             "examples.advanced.plasma_shader", "visual"),
    GameInfo("spinning_cube", "Spinning Cube", "회전 큐브",
             "3D cube in terminal.",
             "터미널 속 3D 큐브.",
             "examples.advanced.spinning_cube", "visual"),
    GameInfo("exploding_logo", "Exploding Logo", "폭발 로고",
             "Logo explosion effect.",
             "로고 폭발 이펙트.",
             "examples.advanced.exploding_logo", "visual"),
    GameInfo("exploding_logo_redux", "Exploding Logo Redux", "폭발 로고 Redux",
             "Refined logo explosion.",
             "개선된 로고 폭발.",
             "examples.advanced.exploding_logo_redux", "visual"),
    GameInfo("palettes", "Palettes", "팔레트",
             "Color palette viewer.",
             "색상 팔레트 뷰어.",
             "examples.advanced.palettes", "visual"),
    GameInfo("figfonts", "FIGlet Fonts", "FIGlet 폰트",
             "ASCII art fonts.",
             "ASCII 아트 폰트.",
             "examples.advanced.figfonts", "visual"),
    GameInfo("moire", "Moiré", "무아레",
             "Moiré pattern demo.",
             "무아레 패턴 데모.",
             "examples.advanced.moire", "visual"),
    GameInfo("pipes", "Pipes", "파이프",
             "Growing pipes.",
             "자라나는 파이프.",
             "examples.advanced.pipes", "visual"),
    GameInfo("isotiles", "Isometric Tiles", "아이소메트릭 타일",
             "Isometric tile renderer.",
             "아이소메트릭 타일 렌더러.",
             "examples.advanced.isotiles", "visual"),
    GameInfo("digital_clock", "Digital Clock", "디지털 시계",
             "Stylish digital clock.",
             "스타일리시 디지털 시계.",
             "examples.advanced.digital_clock", "visual"),
    GameInfo("io_events", "I/O Events", "입출력 이벤트",
             "Event handling demo.",
             "이벤트 처리 데모.",
             "examples.advanced.io_events", "visual"),
]
```

**검증**: `python -c "from examples.demos.catalog import GAMES; print(len(GAMES), GAMES[0].title_ko)"` → `32 테트리스`

### Task 3 — `examples/demos/locales/en.py` & `ko.py`

```python
# examples/demos/locales/en.py
LABELS = {
    "app_title": "batgrl Gallery",
    "select": "Select a game",
    "press_enter": "Enter — launch",
    "press_esc": "Esc — quit",
    "press_l": "L — toggle language",
    "press_up_down": "↑/↓ — navigate",
    "category_puzzle": "Puzzle",
    "category_arcade": "Arcade",
    "category_simulation": "Simulation",
    "category_visual": "Visual",
    "launching": "Launching...",
    "goodbye": "Goodbye!",
    "press_any_key": "Press any key...",
}
```

```python
# examples/demos/locales/ko.py
LABELS = {
    "app_title": "batgrl 갤러리",
    "select": "게임을 선택하세요",
    "press_enter": "Enter — 실행",
    "press_esc": "Esc — 종료",
    "press_l": "L — 언어 전환",
    "press_up_down": "↑/↓ — 이동",
    "category_puzzle": "퍼즐",
    "category_arcade": "아케이드",
    "category_simulation": "시뮬레이션",
    "category_visual": "비주얼",
    "launching": "실행 중...",
    "goodbye": "안녕히 가세요!",
    "press_any_key": "아무 키나 누르세요...",
}
```

### Task 4 — `examples/demos/launcher.py` (메인)

```python
"""batgrl Gallery Launcher — 모든 미니게임을 한 화면에서 둘러보기.

Usage:
    python -m examples.demos.launcher
    python -m examples.demos.launcher --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import subprocess
from pathlib import Path

from batgrl.app import App
from batgrl.colors import ABLACK, AWHITE, gradient
from batgrl.gadgets.text import Text
from batgrl.gadgets.behaviors.focus_behavior import FocusBehavior
from batgrl.gadgets.stack_layout import VStack

from examples.demos.catalog import GAMES, GameInfo
from examples.demos.locales import en, ko


CURRENT_LOCALE = {"lang": "ko"}  # 시작은 한국어


def t(key: str) -> str:
    """현재 locale의 라벨 반환."""
    labels = ko.LABELS if CURRENT_LOCALE["lang"] == "ko" else en.LABELS
    return labels.get(key, key)


def category_ko(cat: str) -> str:
    return t(f"category_{cat}")


class GameCard(FocusBehavior, Text):
    """한 게임을 나타내는 카드. 포커스 가능."""

    def __init__(self, game: GameInfo, **kwargs):
        super().__init__(**kwargs)
        self.game = game
        self._update_text()

    def _update_text(self):
        if CURRENT_LOCALE["lang"] == "ko":
            self.add_str(f"  {self.game.title_ko}\n")
            self.add_str(f"  {self.game.description_ko}\n")
        else:
            self.add_str(f"  {self.game.title}\n")
            self.add_str(f"  {self.game.description}\n")

    def on_focus(self):
        super().on_focus()
        self.colors = gradient(AWHITE, ABLACK, n=3)

    def on_blur(self):
        super().on_blur()
        self.colors = [(255, 255, 255, 50)] * len(self.canvas)


class GalleryApp(App):
    async def on_start(self):
        self.title = t("app_title")

        # ── 좌측: 게임 카드 리스트
        cards = [GameCard(game, size=(2, 60)) for game in GAMES]
        self.cards = cards
        card_stack = VStack(children=cards, pos=(2, 0))

        # ── 우측: 헤더 + 푸터
        header = Text(size=(1, 30), pos=(0, 0))
        self._refresh_header(header)

        footer = Text(size=(3, 60), pos=(-3, 0))
        self._refresh_footer(footer)

        self.add_gadgets(header, card_stack, footer)
        self.header = header
        self.footer = footer
        cards[0].focus()

    def _refresh_header(self, text_widget):
        text_widget.add_str(f"=== {t('app_title')} ===\n")
        text_widget.add_str(f"{t('select')} ({len(GAMES)} games)\n")

    def _refresh_footer(self, text_widget):
        text_widget.add_str(f"{t('press_up_down')}  |  {t('press_enter')}  |  {t('press_esc')}  |  {t('press_l')}\n")

    async def on_key(self, key_event):
        if key_event.key == "l":
            CURRENT_LOCALE["lang"] = "en" if CURRENT_LOCALE["lang"] == "ko" else "ko"
            self.title = t("app_title")
            self._refresh_header(self.header)
            self._refresh_footer(self.footer)
            for card in self.cards:
                card._update_text()
            return True
        if key_event.key == "escape":
            self.quit()
            return True
        return False


def launch_game(game: GameInfo) -> None:
    """subprocess + PTY로 게임 실행. 종료 시 launcher 화면 복귀."""
    import pty
    pid, fd = pty.fork()
    if pid == 0:  # 자식 프로세스
        try:
            subprocess.run([sys.executable, "-m", game.module], check=False)
        finally:
            os._exit(0)
    else:  # 부모 프로세스
        os.waitpid(pid, 0)
        # alt-screen 잔재 정리
        sys.stdout.write("\033[?1049l")  # exit alt screen
        sys.stdout.write("\033[2J\033[H")  # clear + home
        sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print catalog and exit (no TTY required).")
    args = parser.parse_args()

    if args.dry_run:
        print(f"=== {t('app_title')} === ({len(GAMES)} games)")
        for g in GAMES:
            print(f"  [{category_ko(g.category):<12}] {g.title_ko} ({g.title}) — {g.module}")
        print(f"\n{t('goodbye')}")
        return

    if not sys.stdout.isatty():
        print("⚠️  TTY required for interactive launcher. Use --dry-run for catalog listing.")
        sys.exit(1)

    # 사용자가 선택한 게임 ID 받아 실행 (CLI 모드)
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        game_id = sys.argv[1]
        game = next((g for g in GAMES if g.id == game_id), None)
        if not game:
            print(f"Unknown game: {game_id}")
            sys.exit(1)
        print(f"{t('launching')} {game.title_ko}")
        launch_game(game)
        return

    # 풀 TUI 모드
    GalleryApp(title=t("app_title")).run()


if __name__ == "__main__":
    main()
```

**검증**:
```bash
# Dry run — 게임 32개 모두 출력
python -m examples.demos.launcher --dry-run | head -10
# → "[퍼즐] 4목 (Connect Four) — examples.advanced.connect4" 등

# 단일 게임 실행 — subprocess로 tetris 실행 후 종료
python -m examples.demos.launcher tetris
# → "실행 중... 테트리스" 표시 → tetris TUI 구동 → 종료 시 launcher로 복귀
```

### Task 5 — README.md 재작성

원본 attribution 포함 + 우리 저장소 목적 설명. (위 4.4 외 추가 작업)

---

## 6. 알려진 함정

### 6.1 🔴 batgrl 빌드 비용 (90분 함정)

Cython 컴파일 필요. **macOS Apple Silicon**에서 다음 의존성 사전 설치:

```bash
# 1) 시스템 의존성
brew install python@3.11 cython numpy

# 2) 가상환경 (선호)
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

빌드 실패 시 `pip install --no-build-isolation -e .`로 격리 해제 시도. 그래도 안 되면 `MallocStackLogging=no python -m examples.demos.launcher --dry-run`만이라도 검증 가능.

### 6.2 🔴 subprocess 후 alt-screen 잔재

batgrl App은 화면을 alt-screen으로 전환하고 종료 시 `\033[?1049l`로 복귀하지만, **subprocess kill** 시점에는 그 escape를 못 보낼 수 있음. Task 4 코드에는 명시적으로 `\033[?1049l` 출력 추가했음.

### 6.3 ⚠️ 게임 모듈 경로 정확성

`examples/advanced/sph/` 같은 디렉토리는 `__init__.py`가 있어 `examples.advanced.sph`로 임포트 가능. **단 `examples/advanced/tetris/`는 패키지 자체**이고 메인 모듈은 `tetris/__main__.py`. 직접 임포트 시 `from examples.advanced.tetris import tetris` 또는 `-m examples.advanced.tetris` 모두 가능. **둘 다 시도해보고 어느 쪽이 작동하는지 확인**.

### 6.4 ⚠️ 일부 게임은 assets 의존

`snake.py`, `pong.py` 등은 `examples/assets/spinner.gif` 같은 외부 자원 사용. 카탈로그에는 자산 의존 게임에 별도 표시 안 했으나, 실행 시 FileNotFoundError 가능. **첫 번째 실행 시점에만 문제** — 자산은 이미 git에 포함돼 있으므로 fresh clone에서는 OK.

### 6.5 ⚠️ 한국어 폰트 깨짐 (TUI)

batgrl의 텍스트 gadget은 unicode width 계산을 위해 `uwcwidth` 사용. 한국어 글자는 대부분 width 2로 정상 표시되지만, **구형 터미널/일부 iTerm 설정**에서는 깨질 수 있음. 검증 시 iTerm2 + 시스템 한글 폰트 조합 권장.

### 6.6 ⚠️ Task 4의 `os.waitpid`는 동기 블로킹

PTY 자식이 종료될 때까지 launcher 멈춤. 의도된 동작 (게임 끝나야 launcher 복귀). 다만 **유저가 게임 중간에 Ctrl+C** 누르면 waitpid가 즉시 리턴하고 alt-screen 잔재 정리만 실행됨. 추가 안전망으로 try/finally + 1초 timeout 고려.

---

## 7. 핵심 결정 + 성공 지표

### 7.1 핵심 결정 (변경 시 메인테이너와 협의 필요)

| 결정 | 채택 |
|---|---|
| Launcher 패턴 | subprocess + PTY |
| 한국어 시작 | ko 기본 |
| 다국어 토글 단축키 | L |
| 게임 모듈 임포트 | `-m examples.advanced.<name>` |
| 미니게임 카테고리 | 4종 (puzzle/arcade/simulation/visual) |
| 원본 sync 정책 | upstream sync 안 함 (완전 독립) |

### 7.2 성공 지표

- [ ] 32개 게임 모두 catalog에 등록
- [ ] `--dry-run` 모드에서 카테고리/한국어/모듈 경로 정상 출력
- [ ] `tetris` 단일 실행 시 TUI 정상 구동 + 종료 후 깨끗한 화면 복귀
- [ ] 풀 launcher 모드에서 ↑/↓ 네비게이션 + Enter 실행 + L 토글 + Esc 종료 모두 정상
- [ ] README에 원본 attribution 명시

### 7.3 작업 순서 권장

1. Task 1 (스캐폴드) → 30초
2. Task 2 (catalog.py) → 5분 (복붙 후 verify)
3. Task 3 (locales) → 2분
4. Task 4 (launcher.py) → 10분 (복붙 후 dry-run verify)
5. Task 5 (README) → 10분
6. 통합 verify (`python -m examples.demos.launcher --dry-run`) → 2분
7. 단일 게임 실행 verify (`python -m examples.demos.launcher tetris`) → 5분

**총 예상 시간: 30~40분** (빌드 시간 제외)

### 7.4 빌드 시간 분리

위 30분 + **`pip install -e .` 첫 빌드 = 15~25분**. 둘은 병행 가능:
- 빌드 시간 동안 catalog/locales 작업
- 빌드 완료 후 launcher 실행 검증