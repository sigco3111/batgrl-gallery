# batgrl Gallery

**한국어 라벨 + 미니게임 통합 Launcher가 추가된 batgrl 갤러리.**

원본 [salt-die/batgrl](https://github.com/salt-die/batgrl) (MIT)을 기반으로, 한국어 사용자가 미니게임을 한 화면에서 둘러보고 즉시 실행할 수 있도록 확장한 독립 포크입니다. **upstream PR은 보내지 않으며**, sigco3111 계정에서 단독 운영됩니다.

---

## 🎮 무엇이 다른가?

원본 batgrl은 TUI에서 멋진 그래픽을 그릴 수 있는 Python 라이브러리입니다. `examples/advanced/` 폴더에 **32개의 풀 게임·시뮬레이션**이 들어있지만, 게임마다 별도로 실행해야 하고 UI는 영문만 지원합니다.

이 갤러리는:

- 🇰🇷 **한국어 UI 라벨** 기본 제공 (영어 토글 가능)
- 🗂️ **모든 미니게임을 한 화면에서** 둘러보는 TUI Launcher
- ⌨️ Enter 한 번으로 선택한 게임을 새 TTY에 즉시 실행
- 📦 **32개 게임 카탈로그** (퍼즐 / 아케이드 / 시뮬레이션 / 비주얼 4개 카테고리)

---

## 🚀 빠른 시작

```bash
# 1) 의존성 설치 (Cython 컴파일 필요, 5~15분 소요)
# Python 3.12+ 필수 (pyproject.toml requires-python)
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .

# 2) 갤러리 Launcher 실행
python -m examples.demos.launcher

# 또는 dry-run (TTY 없이 카탈로그만 보기)
python -m examples.demos.launcher --dry-run

# 단일 게임 직접 실행 (헤드리스 환경에서 --timeout 권장)
python -m examples.demos.launcher tetris --timeout 5

# 영어 라벨로 실행
python -m examples.demos.launcher --lang en
```

---

## 🎯 Launcher 키 바인딩

| 키 | 동작 |
|---|---|
| ↑ / ↓ | 게임 선택 (카드 간 이동) |
| Enter | 선택한 게임 실행 (새 TTY) |
| L | 한국어 � 영어 토글 |
| 0 | 전체 필터 해제 (카테고리 + 즐겨찾기 + 검색) |
| 1 | 퍼즐만 보기 |
| 2 | 아케이드만 보기 |
| 3 | 시뮬레이션만 보기 |
| 4 | 비주얼만 보기 |
| 5 | 즐겨찾기만 보기 (토글) |
| / | 검색 모드 진입 (한 글자씩 live 필터) |
| f | 즐겨찾기 토글 (영구 저장) |
| Esc | 검색 취소 / Launcher 종료 |

### 비주얼 기능 (Tier 1+2)

- **카테고리 색상**: 퍼즐(파랑), 아케이드(빨강), 시뮬레이션(청록), 비주얼(보라)
- **▶ 선택 화살표**: 포커스된 카드 좌측에 화살표 표시
- **컨트롤 �트**: 카드 우측에 그 게임의 조작법 (`←→↑↓`, `click`, `watch` 등)
- **의존성 경고**: 실행에 추가 패키지가 필요한 게임은 `⚠ networkx` 같은 표시
- **즐겨찾기 ★**: `f`로 토글, `5`로 즐겨찾기만 보기. `~/.config/batgrl-gallery/state.json`에 영구 저장.
- **최근 실행 ●**: 24시간 내 실행하면 ●, 7일 내면 ○ 표시. 같은 파일에 저장.
- **타입어헤드 검색**: `/`로 입력 모드, 타이핑하며 실시간 필터. Esc로 취소.
- **사이드바**: 우측에 선택된 게임의 제목 / 카테고리 / 컨트롤 / 의존성 / 최근 실행 시각 표시.

### CLI 옵션

| 옵션 | 설명 |
|---|---|
| `--dry-run` | TUI 진입 없이 카탈로그만 출력 (TTY 불필요) |
| `--lang ko\|en` | 시작 로케일 강제 지정 (기본: ko) |
| `--timeout N` | 단일 게임 모드에서 N초 후 자식 프로세스 종료 |
| `<game_id>` | 위치 인자로 게임 ID 직접 지정 (예: `tetris`, `snake`) |

---

## 🗂️ 32개 게임 카테고리

| 카테고리 | 게임 예시 |
|---|---|
| 🧩 퍼즐 | 테트리스, 4목, 지뢰찾기, 슬라이딩 퍼즐, 루빅스 큐브, 미로, 무한 틱택토 |
| 🎮 아케이드 | 스네이크, 퐁, 핵 (로그라이크), 샌드박스 |
| 🌊 시뮬레이션 | 생명의 게임, 나비에-스토크스, 안정적 유체, 반응-확산, 점균, 광선 추적, 레이캐스팅, 천, SPH |
| ✨ 비주얼 | 둠 파이어, 플라즈마 셰이더, 회전 큐브, FIGlet 폰트, 무아레, 아이소메트릭 타일, 디지털 시계 등 |

자세한 게임 목록은 `--dry-run` 옵션으로 확인 가능합니다.

---

## 📂 디렉토리 구조

```
examples/
├── advanced/                # 원본 batgrl의 32개 게임/시뮬레이션 예제
├── basic/                   # 원본 batgrl의 UI 위젯 예제
└── demos/                   # [신규] 이 갤러리 추가분
    ├── launcher.py          # TUI Launcher
    ├── catalog.py           # 32개 게임 메타데이터 (SSoT)
    └── locales/
        ├── en.py
        └── ko.py
```

---

## 📜 원본 attribution

이 저장소는 다음 원본에서 파생되었습니다:

- **원본**: [salt-die/batgrl](https://github.com/salt-die/batgrl)
- **저자**: salt-die 및 batgrl 기여자
- **라이선스**: MIT
- **원본 commit 기반**: 이 저장소는 원본의 특정 시점을 그대로 복제 + `examples/demos/` 폴더만 추가

원본의 모든 저작권은 원저자에게 있습니다. 이 저장소의 추가분(`examples/demos/`)도 동일한 MIT 라이선스를 따릅니다.

---

## 📝 작업 진행

이 저장소의 실제 구현은 [HANDOFF.md](./HANDOFF.md) 문서를 따라 다른 에이전트/세션에서 수행됩니다.

- ✅ 원본 클론 + 핸드오프 문서 작성
- ✅ `examples/demos/` 디렉토리 구현 (Launcher + 32-game catalog + ko/en locales)
- ✅ README / 빌드 가이드 보완 (Python 3.12+ 명시, --timeout 옵션 문서화)
- ✅ 미니게임 32개 한국어 라벨 정밀 조정
- ✅ Tier 1 고도화 (카테고리 필터, 색상, 컨트롤 힌트, 의존성 경고)
- ✅ Tier 2 고도화 (검색, 즐겨찾기, 최근 실행, 사이드바)

---

## 🔗 관련 링크

- 원본 batgrl: https://github.com/salt-die/batgrl
- 원본 라이브 데모: https://salt-die.github.io/batgrl/
- 원본 문서: https://github.com/salt-die/batgrl/tree/main/docs

---

**유지보수**: sigco3111 · **원본 라이선스**: MIT · **갤러리 추가분 라이선스**: MIT