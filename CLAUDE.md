# CLAUDE.md

이 파일은 이 저장소에서 작업하는 Claude Code(claude.ai/code)에게 제공하는 가이드입니다.

## 이 프로젝트는

여러 개의 CSV/Excel 파일을 불러와 하나의 표로 이어붙이고(행 단위), 선택한 컬럼을 선 그래프로 그려주는 Windows 데스크톱 앱(PySide6)입니다. 결합하려면 파일들의 열 구조가 완전히 같아야 합니다 — 아래 "결합 로직" 참고.

## 명령어

의존성 설치 (전역 site-packages가 아니라 `.venv` 가상환경 사용):
```bash
python -m venv .venv
./.venv/Scripts/pip install -r requirements.txt
```

앱 실행:
```bash
./.venv/Scripts/python main.py
```

Windows 단일 실행파일(exe) 빌드 (PyInstaller, onefile, 콘솔창 없음):
```bash
./.venv/Scripts/pip install pyinstaller
./.venv/Scripts/pyinstaller --noconfirm --onefile --windowed --name DataViewer main.py
```
결과물은 `dist/DataViewer.exe`에 생성됩니다. `build/`, `dist/`, `*.spec`은 `.gitignore`에 포함되어 있습니다 — exe는 로컬 빌드 산출물일 뿐 커밋 대상이 아닙니다.

테스트 스위트와 린터는 아직 구성되어 있지 않습니다. 데이터 로직을 확인할 때 가장 유용한 방법은 `app/data_loader.py`의 `load_files`/`combine_frames`를 샘플 파일로 직접 실행해보는 것입니다 (`sample_data/`에 열 구조가 같은 `.xlsx` 샘플 2개가 있습니다).

## 아키텍처

`app/` 아래 4개 모듈이 있고, `main_window.MainWindow`가 이들을 엮어 조립합니다.

- **`data_loader.py`** — Qt에 의존하지 않는 순수 pandas 로직. `load_files()`는 확장자에 따라 `pd.read_csv`/`pd.read_excel`로 각 경로를 읽고, 실패하면 예외를 던지는 대신 파일별 오류를 모아서 반환합니다. `combine_frames()`는 행 단위로 이어붙이되, 첫 번째 파일과 열(컬럼) 튜플이 정확히 일치하는 파일들끼리만 결합합니다. 열 구조가 다른 파일은 결과에서 제외되고, 그 경로들을 별도로 반환해 UI가 경고할 수 있게 합니다. 컬럼 재매핑이나 정렬 기능은 없으며 스키마가 완전히 일치해야만 합니다.
- **`table_model.py`** — `PandasTableModel(QAbstractTableModel)`은 DataFrame을 `QTableView`에 보여주는 읽기 전용 어댑터입니다.
- **`plot_canvas.py`** — `PlotCanvas(FigureCanvasQTAgg)`는 matplotlib figure를 Qt에 임베드합니다. `plot_lines()`는 요청받은 각 Y 컬럼을 `pd.to_numeric(errors="coerce")`로 강제 변환하고, 전부 NaN이 되어버린 컬럼은 예외를 던지지 않고 건너뛴 뒤 호출자에게 돌려줍니다(어떤 컬럼이 제외됐는지 UI가 알릴 수 있도록). 모듈 최상단의 `plt.rcParams["font.family"] = "Malgun Gothic"` 설정은 한글 라벨이 깨진 네모(□)로 나오지 않게 하기 위한 것이니, 다른 한중일 폰트로 대체하지 않는 한 제거하면 안 됩니다.
- **`main_window.py`** — 모든 UI 상태와 흐름을 담당합니다. 눈에 잘 안 띄는 핵심 동작:
  - X축 콤보박스와 Y축 체크리스트는 서로 배타적입니다: X축으로 선택된 컬럼은 Y축 목록에서 제외되고(`_refresh_y_list`), X축을 바꾸면 Y축 목록이 다시 만들어집니다.
  - Y축 체크 상태는 목록이 다시 만들어져도 `self._y_checked`(컬럼명을 키로 하는 dict)에 유지되며, 처음 보는 컬럼은 기본으로 체크된 상태입니다. 이 덕분에 "결합 직후 전체 컬럼 표시"와 "다른 선택은 유지한 채 특정 컬럼만 껐다 켜기"가 동작합니다.
  - 그래프는 X축 변경이나 Y축 체크박스 토글이 있을 때마다 즉시 갱신됩니다(`_update_plot`) — 별도의 "선택 확정" 단계가 없습니다. "그래프 새로고침" 버튼은 같은 메서드를 수동으로 다시 호출할 뿐입니다.
  - 드래그앤드롭이 동작하려면 `dragEnterEvent`와 `dragMoveEvent` **둘 다** 오버라이드해서 `acceptProposedAction()`을 호출해야 합니다. Qt의 기본 `dragMoveEvent`는 이벤트를 무시하도록 되어 있어서, `dragEnterEvent`가 수락했더라도 `dropEvent`가 조용히 발생하지 않게 막습니다 — 이건 방어적 보일러플레이트가 아니라 실제로 겪은 함정이니 지우지 마세요.

`main.py`는 최소한의 진입점입니다 (`QApplication` + `MainWindow().show()`).

현재 모든 처리는 Qt 메인 스레드에서 동기적으로 실행됩니다 — 큰 파일을 불러오거나 결합하면 UI가 멈춥니다. 대용량 파일 처리가 필요해지면 이 부분에 워커 스레드를 도입해야 합니다.

## 버전 관리 & 릴리스

버전 문자열은 `app/__init__.py`의 `__version__`에 있고, 창 제목(`DataViewer v{__version__}`)에 표시됩니다. 시맨틱 버저닝(`v0.1.0`, `v0.2.0`, ...)을 따릅니다.

기능이 안정될 때마다 아래 순서로 릴리스합니다:
1. `CHANGELOG.md`에 새 버전 섹션을 추가하고 이번 버전에서 추가/변경/수정된 내용을 정리
2. `app/__init__.py`의 `__version__` 값을 올리고 커밋/푸시
3. `git tag -a vX.Y.Z -m "..."` 로 태그를 만들고 `git push origin vX.Y.Z`로 푸시
4. `./.venv/Scripts/pyinstaller --noconfirm --onefile --windowed --name DataViewer main.py`로 exe 빌드
5. `gh release create vX.Y.Z dist/DataViewer.exe --repo eomhyunjin/DataViewer --title "vX.Y.Z" --notes "..."`로 GitHub Release를 만들고 exe를 첨부 (release notes는 CHANGELOG.md의 해당 버전 내용을 재사용)

exe 자체는 git에 커밋하지 않고 GitHub Releases로만 배포합니다 — Python 설치 없이 Releases 페이지에서 exe를 내려받아 바로 실행할 수 있게 하기 위함입니다.

## 기록 규칙

작업이 확정될 때마다(사용자가 승인했거나, 커밋/푸시까지 끝나서 되돌릴 일 없이 마무리된 시점) 아래 두 파일에 반드시 기록을 남깁니다. 코드만 고치고 문서화를 빼먹지 않도록 커밋 전 마지막 단계로 챙깁니다.

- **`WORKLOG.md`** — 예외 없이 항상 남깁니다. 코드 변경, 버그 수정, 기능 추가, 문서/설정 변경 등 확정된 작업이면 크기와 무관하게 오늘 날짜 섹션에 한두 줄로 추가합니다. (릴리스 여부와 무관한, 매 작업 단위의 개발 로그)
- **`CHANGELOG.md`** — 사용자 입장에서 의미 있는 변경(새 기능, 동작 변경, 버그 수정 등)일 때만 남깁니다. 오타 수정이나 내부 리팩터링처럼 사용자에게 안 보이는 변경까지 넣지 않습니다. 버전을 태그/릴리스하는 시점에 `[Unreleased]` 또는 새 버전 섹션으로 정리합니다 (자세한 릴리스 절차는 위 "버전 관리 & 릴리스" 참고).

두 파일은 목적이 다릅니다: `WORKLOG.md`는 "무엇을 언제 했는지"에 대한 개발자용 이력이고, `CHANGELOG.md`는 "이 버전에서 뭐가 달라졌는지"에 대한 사용자용 요약입니다.
