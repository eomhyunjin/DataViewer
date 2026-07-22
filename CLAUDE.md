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

`app/` 아래 5개 모듈이 있고, `main_window.MainWindow`가 이들을 엮어 조립합니다.

- **`data_loader.py`** — Qt에 의존하지 않는 순수 pandas 로직. `load_files()`는 확장자에 따라 `pd.read_csv`/`pd.read_excel`로 각 경로를 읽고, 실패하면 예외를 던지는 대신 파일별 오류를 모아서 반환합니다. `combine_frames()`는 행 단위로 이어붙이되, 첫 번째 파일과 열(컬럼) 튜플이 정확히 일치하는 파일들끼리만 결합합니다. 열 구조가 다른 파일은 결과에서 제외되고, 그 경로들을 별도로 반환해 UI가 경고할 수 있게 합니다. 컬럼 재매핑이나 정렬 기능은 없으며 스키마가 완전히 일치해야만 합니다. `numeric_columns()`는 `pd.to_numeric` 변환 시 값이 하나라도 남는 컬럼만 골라주는 헬퍼로, Status/Save Period처럼 항상 텍스트뿐인 컬럼을 Y축 후보에서 아예 제외하는 데 쓰입니다.
- **`table_model.py`** — `PandasTableModel(QAbstractTableModel)`은 DataFrame을 `QTableView`에 보여주는 읽기 전용 어댑터입니다.
- **`figure_options.py`** — matplotlib 내장 "Figure options"(Customize) 다이얼로그(`matplotlib.backends.qt_editor.figureoptions.figure_edit`)를 그대로 옮겨온 뒤 X/Y축 Scale(linear/log/symlog/logit) 드롭다운만 뺀 버전입니다. matplotlib이 이 다이얼로그를 필드 단위로 커스터마이즈하는 공개 API를 제공하지 않아서 함수 전체를 vendoring했습니다 — `apply_callback`에서 축 하나당 읽어오는 필드 수가 원본의 4개(Min/Max/Label/Scale)에서 3개(Min/Max/Label)로 바뀐 게 실제 변경의 전부이니, matplotlib을 업그레이드할 때는 이 파일을 원본과 다시 비교해서 다른 변경 사항이 있는지 확인해야 합니다. `main_window.py`의 `_PlotToolbar.edit_parameters()`가 matplotlib 기본 `figureoptions.figure_edit` 대신 이 모듈을 호출하도록 오버라이드합니다.
- **`plot_canvas.py`** — `PlotCanvas(FigureCanvasQTAgg)`는 matplotlib figure를 Qt에 임베드합니다. `plot_lines()`는 요청받은 각 Y 컬럼을 `pd.to_numeric(errors="coerce")`로 강제 변환하고, 전부 NaN이 되어버린 컬럼은 예외를 던지지 않고 건너뛴 뒤 호출자에게 돌려줍니다(어떤 컬럼이 제외됐는지 UI가 알릴 수 있도록). X축이 숫자/날짜형이 아니면(예: 타임스탬프 문자열) 위치 인덱스를 실제 플롯 좌표로 쓰고 `FuncFormatter`로 눈금에만 원래 문자열을 붙입니다 — matplotlib이 문자열 X축을 범주형으로 취급해 값마다 변환하면 수십만~수백만 행에서 렌더링이 몇 분씩 걸리기 때문입니다(실측: 128만 행 기준 범주형 축 그대로면 15분 넘게 안 끝남, 위치 인덱스로 우회하면 4초). 마커는 행이 500개 이하일 때만 그리고(대용량에서는 점이 뭉개져 안 보이는 데다 렌더링만 느려짐), 범례는 자동 위치 탐색(`loc="best"`) 대신 `"upper right"`로 고정합니다 — `best`는 겹침 회피를 위해 모든 데이터 포인트를 훑어서 대용량에서 그 자체로 느립니다. 모듈 최상단의 `plt.rcParams["font.family"] = "Malgun Gothic"` 설정은 한글 라벨이 깨진 네모(□)로 나오지 않게 하기 위한 것이니, 다른 한중일 폰트로 대체하지 않는 한 제거하면 안 됩니다. `__init__`에서 `scroll_event`를 `_on_scroll`에 연결해 마우스 커서 위치를 중심으로 휠 확대/축소를 지원합니다.
- **`main_window.py`** — 모든 UI 상태와 흐름을 담당합니다. 눈에 잘 안 띄는 핵심 동작:
  - X축 콤보박스와 Y축 체크리스트는 서로 배타적입니다: X축으로 선택된 컬럼은 Y축 목록에서 제외되고(`_refresh_y_list`), X축을 바꾸면 Y축 목록이 다시 만들어집니다. `numeric_columns()`로 걸러지지 않는(텍스트뿐인) 컬럼도 Y축 후보에서 제외됩니다.
  - Y축 체크 상태는 목록이 다시 만들어져도 `self._y_checked`(컬럼명을 키로 하는 dict)에 유지되며, **결합 직후에는 전부 미체크 상태**입니다(`_combine_and_display`) — 대용량 데이터를 불러오자마자 모든 컬럼을 자동으로 그리면 그 자체로 몇 초가 걸리므로, 사용자가 실제로 보고 싶은 컬럼을 체크했을 때만 그래프가 그려지도록 의도한 것입니다. 체크박스를 토글하면 `_on_y_item_changed`가 그 컬럼만 켜고/끄고 `_update_plot`을 호출합니다.
  - 그래프는 X축 변경이나 Y축 체크박스 토글이 있을 때마다 즉시 갱신됩니다(`_update_plot`) — 단, **결합 직후에는 자동으로 그려지지 않습니다**(`_combine_and_display`가 `_update_plot`을 호출하지 않고 `_plot_canvas.clear()`로 이전 결합의 그래프만 지웁니다). "그래프 새로고침" 버튼은 `_update_plot`을 수동으로 다시 호출할 뿐입니다.
  - 파일 목록(`self._file_list`)에는 파일명만 보이지만, 결합/제거에 실제로 쓰는 전체 경로는 각 `QListWidgetItem`에 `setData(_FILE_PATH_ROLE, ...)`로 따로 심어둔 값입니다. `item.text()`가 아니라 `item.data(_FILE_PATH_ROLE)`을 읽어야 진짜 경로가 나옵니다 — `_loaded_frames` 딕셔너리의 키도 이 전체 경로이므로 텍스트로 조회하면 다른 폴더의 동명 파일과 충돌하거나 조회에 실패합니다.
  - 그래프 위에는 `_PlotToolbar`(모듈 상단에 정의된 `NavigationToolbar2QT` 서브클래스, `self._plot_toolbar`)를 붙여 부분 확대/이동/원래대로/Customize(범례·곡선 편집)/저장을 제공합니다. 기본 `toolitems`에서 **Back/Forward(이전·다음 보기)만 뺐습니다**: `_update_plot`이 매번 `self._plot_toolbar.update()`로 뷰 기록을 통째로 지우기 때문에(아래 항목 참고) 애초에 되돌아갈 기록이 안 남아 실사용상 무의미해서입니다. `_PlotToolbar.edit_parameters()`를 오버라이드해서 Customize 버튼이 matplotlib 기본 다이얼로그 대신 `app/figure_options.py`(X/Y축 Scale 드롭다운을 뺀 버전)를 열도록 바꿨습니다 — 이 앱은 장비 로그 시계열만 다루고 로그/symlog 축이 쓸모없다는 사용자 요청에 따른 것입니다.
  - **Customize(Figure options)의 "(Re-)Generate automatic legend" 체크박스는 토글이 아니라 "지금 다시 그려라" 일회성 트리거입니다** — 다이얼로그를 열 때마다 항상 미체크로 시작하고, 체크한 채 OK를 누르면 `axes.legend(ncols=...)`를 loc 인자 없이 호출해 matplotlib 기본 위치(`best`)로 범례를 다시 그립니다. 우리가 그리는 기본 위치는 `loc="upper right"`인데 `best`가 다른 자리(왼쪽 등)를 고르면서 "범례가 왼쪽으로 이동"하는 것처럼 보입니다. 체크를 풀고 다시 OK를 눌러도 이 트리거에는 "원래대로 되돌리기" 로직이 없어서(단순히 "이번엔 재생성하지 마라"는 뜻일 뿐) 범례는 이동한 자리에 그대로 남습니다 — matplotlib 다이얼로그 자체의 동작이라 우리 코드로 그 안의 체크박스 의미를 바꾸지 않는 한 고칠 수 없습니다. **"그래프 새로고침" 버튼(또는 X축/Y축 체크박스 변경)이 `_update_plot`을 다시 태워 `plot_lines`가 `ax.clear()` 후 `loc="upper right"`로 새로 그리므로, 이게 실질적인 "원상복귀" 방법입니다** — 실제로 시뮬레이션해서 legend `_loc` 코드가 `1`(upper right) → `0`(best) → 새로고침 후 다시 `1`로 돌아오는 것을 확인했습니다.
  - **"원래대로" 버튼이 스스로 기준 뷰를 잡는 시점은 사용자가 툴바의 이동/부분 확대를 처음 드래그하는 순간뿐입니다**(matplotlib `NavigationToolbar2._zoom_pan_handler` 참고) — `PlotCanvas._on_scroll`의 마우스 휠 확대는 툴바를 거치지 않으므로, 휠로만 확대했다면 "원래대로"를 눌러도 기준이 없어 아무 일도 안 일어납니다. 그래서 `_update_plot`이 새로 그릴 때마다 `self._plot_toolbar.update()`(기록 초기화) 다음 `push_current()`(지금 이 전체 보기를 기준으로 등록)를 호출해, 이후 휠이든 드래그든 어떻게 확대/축소하더라도 "원래대로"가 항상 이 시점으로 돌아가게 만듭니다. 이 두 호출을 지우면 안 됩니다.
  - 드래그앤드롭이 동작하려면 `dragEnterEvent`와 `dragMoveEvent` **둘 다** 오버라이드해서 `acceptProposedAction()`을 호출해야 합니다. Qt의 기본 `dragMoveEvent`는 이벤트를 무시하도록 되어 있어서, `dragEnterEvent`가 수락했더라도 `dropEvent`가 조용히 발생하지 않게 막습니다 — 이건 방어적 보일러플레이트가 아니라 실제로 겪은 함정이니 지우지 마세요.

`main.py`는 최소한의 진입점입니다 (`QApplication` + `MainWindow().show()`).

현재 모든 처리는 Qt 메인 스레드에서 동기적으로 실행됩니다. `plot_canvas.py`의 성능 수정 덕분에 수백만 행 규모에서도 결합+그래프가 몇 초 안에 끝나 체감상 멈추지는 않지만, 그보다 훨씬 큰 데이터를 다루게 되면 여전히 UI가 멈출 수 있습니다 — 그 정도 규모가 필요해지면 이 부분에 워커 스레드를 도입해야 합니다.

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
