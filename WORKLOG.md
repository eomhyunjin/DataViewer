# 작업 기록

세션/작업 단위로 무엇을 했는지 기록합니다. 릴리스 시점의 사용자 대상 변경 요약은 `CHANGELOG.md`를 참고하세요. 이 파일은 그보다 더 잘게, 작업할 때마다 남기는 개발 로그입니다.

## 2026-07-30

- 기능 추가(이전 세션에서 구현된 뒤 기록/커밋이 안 된 채 작업 트리에 남아있던 것을 뒤늦게 기록 후 커밋): 파일 목록 드래그로 순서 변경 + 파일 더블클릭 시 그래프에 해당 구간 하이라이트 표시
  - `app/main_window.py`: `_FileListWidget`(`QListWidget` 서브클래스) 신설 — 내부 드래그로 항목 순서가 바뀌면 `order_changed`를 emit, 항목이 없는 빈 여백을 더블클릭하면 `empty_area_double_clicked`를 emit. `_combined_paths`(마지막으로 "결합하기"를 눌렀을 때의 파일 집합)와 `_file_row_ranges`(결합된 테이블에서 각 파일이 차지하는 [시작,끝) 행 구간)를 추가로 추적
  - 드래그로 순서를 바꾸면(`_on_file_order_changed`) 열 구성이 그대로일 때 X/Y 선택을 유지한 채 새 순서로 재결합/재그리기, 열 구성이 달라지면 새로 고른 것과 동일하게 선택을 초기화(`_apply_combine`의 `reset_selection` 분기로 정리)
  - 파일 목록에서 파일을 더블클릭하면(`_on_file_item_double_clicked`) 그 파일이 결합된 데이터에서 차지하는 행 구간을 그래프에 노란 배경(`axvspan`)으로 표시(`app/plot_canvas.py`의 `highlight_row_range`/`clear_highlight`), 빈 여백을 더블클릭하면 해제
  - `app/plot_canvas.py`: `_highlight_span` 상태 추가, `_reset_axes()`가 `ax.clear()`로 함께 지워지는 것과 별도로 관리
- UI 변경: 그래프 영역을 DAQsystem(INCA/CANalyzer 스타일) 그래프와 같은 톤으로 리스타일링(matplotlib 엔진과 기존 기능은 전부 그대로 유지 — 시각 스타일만 변경)
  - `app/plot_canvas.py`: 커브 색상 팔레트를 DAQsystem `ui/main_window.py`의 `CURVE_PALETTE`와 동일한 값(`#2563eb`, `#d97706`, `#16a34a`, ...)으로 교체. `Figure`/`Axes` 배경을 명시적으로 흰색 고정, 옅은 회색 격자(`ax.grid(alpha=0.3)`, DAQsystem의 `pg.PlotWidget.showGrid(alpha=0.3)`과 동일한 톤) 추가, 범례 상자를 흰 배경+옅은 테두리로 스타일링(pyqtgraph `addLegend()`의 흰 범례 상자와 톤 맞춤)
  - `app/theme.py`: 그래프 툴바(`QToolBar#PlotToolbar`)에 흰 배경 + 파란 강조 호버 QSS 추가(기존 matplotlib 기본 회색 툴바 대신 앱 전체 톤과 통일)
  - `app/main_window.py`: `_plot_toolbar`에 `objectName("PlotToolbar")` 부여(위 QSS 스코프 지정용)
  - 멀티 Y축, 범례 드래그, 축 더블클릭 편집, 그래프 포인트 더블클릭→테이블 행 선택, 구간 하이라이트, Figure options(Customize) 등 기존 기능은 코드 변경 없이 그대로 동작
  - 오프스크린(`QT_QPA_PLATFORM=offscreen`) 렌더링으로 실제 데이터 로드→결합→그래프 표시까지 스모크 테스트 후 `widget.grab()` 캡처로 흰 배경/격자/팔레트 색/범례 스타일 적용 확인

## 2026-07-24

- 버그 수정: 멀티 Y축(twinx로 만든 축이 2개 이상)일 때 범례 드래그가 전혀 동작하지 않던 문제 수정
  - 원인: 범례가 `self.ax`에 붙어있었는데, matplotlib은 클릭이 일어난 axes(`event.inaxes`)가 범례를 가진 axes와 같을 때만 드래그용 pick 이벤트를 넘겨준다. `twinx()`로 만든 두 번째 이후 Y축은 `self.ax`와 완전히 겹친 채 zorder도 같아 항상 나중에 추가된 축이 topmost로 판정되고, 그 결과 `event.inaxes`가 항상 twin 축이 되어 `self.ax`에 붙은 범례는 pick 이벤트를 못 받음(Y축 1개일 때만 우연히 동작했음)
  - `app/plot_canvas.py`: 범례를 `self.ax.legend(...)` 대신 `self.figure.legend(...)`로 붙여서 axes 매칭 조건 자체를 없앰
  - 덧붙여, `plot_lines()`가 매번 새 범례를 만들다 보니 컬럼 체크/해제로 그래프를 다시 그릴 때마다 드래그해둔 위치가 기본값(`upper right`)으로 초기화되던 것도 같이 수정 — 이전 범례의 `_loc`을 기억해뒀다가 새 범례에 그대로 적용
  - 사용자가 실제 프로그램에서 확인 완료

- 기능 추가: 그래프의 X/Y축을 더블클릭하면 그 축의 Min/Max/Label만 편집하는 작은 다이얼로그(`axis_edit`)를 열도록 추가
  - `app/figure_options.py`: `figure_edit()`에서 뗀 축 하나 분량 로직으로 `axis_edit()` 신설. Y축 편집 시 라벨을 바꾸면 그 축에 그려진 선의 범례 이름(label)도 함께 바꿔서 축 라벨과 범례 이름이 어긋나지 않게 함
  - `app/plot_canvas.py`: `button_press_event`를 `_on_axis_double_click`에 연결. `Axis`(XAxis/YAxis)는 pick 가능한 `contains()`를 구현하지 않아서(기본 구현은 항상 False) `get_tightbbox()`가 반환하는 bbox로 직접 히트 테스트
  - Customize(Figure options) 다이얼로그에서는 Title/축 Min·Max·Label/legend 재생성 체크박스를 담은 "Axes" 탭 전체를 제거(Curves 탭만 남음) — 축 편집은 위 더블클릭 다이얼로그로 옮겨감. 기존 Axes 탭은 항상 첫 번째 축만 편집 가능해 twinx로 만든 추가 Y축은 건드릴 수 없었음
  - `app/plot_canvas.py`: Customize에서 커브 색을 바꾸면 그 축의 y라벨/눈금 색과 범례 아이콘 색도 같이 최신 색으로 갱신되도록 `refresh_legend()`/`on_apply` 콜백 추가(matplotlib 범례는 라인 색의 복사본을 그려서 원본 색이 바뀌어도 자동으로 안 따라감)
  - 사용자가 실제 프로그램에서 Y축 라벨 변경 시 범례 이름도 같이 바뀌는 것을 확인 완료

- 기능 변경: 툴바 Pan 버튼("Left button pans, Right button zooms")을 없애고, 그 동작을 그래프 위 클릭+드래그에 항상 기본으로 적용
  - `app/main_window.py`: `_PlotToolbar.toolitems`에서 `"Pan"` 제거
  - `app/plot_canvas.py`: `_on_button_press`/`_on_button_release` 추가. matplotlib이 Pan 모드에서 쓰는 `toolbar.press_pan`/`drag_pan`/`release_pan`을 그대로 재사용해서(twinx로 만든 여러 Y축까지 자동으로 같이 처리됨) 왼쪽 드래그=이동, 오른쪽 드래그=확대·축소가 버튼 없이 기본 동작이 되도록 함
  - 범례를 클릭해서 드래그로 옮기는 기존 동작과 겹치지 않도록 클릭 지점이 범례 영역이면 건너뛰고, "Zoom"(사각형 확대) 버튼이 켜져 있을 때도 겹치지 않도록 건너뜀
  - 가상 마우스 이벤트로 왼쪽 드래그(이동)/오른쪽 드래그(확대, 멀티 Y축 포함)/범례 드래그 미간섭/Zoom 모드와의 미충돌을 확인
- 조사: 사용자가 "드래그앤드롭이 안 된다"고 보고해서 코드(`dragEnterEvent`/`dragMoveEvent`/`dropEvent`, `data_loader.SUPPORTED_SUFFIXES`)를 확인했으나 이상 없었음(MDF도 이미 지원 대상에 포함되어 있었음). 실제 원인은 코드가 아니라 **이 세션(터미널)이 관리자 권한으로 실행 중이어서** Windows UIPI가 일반 권한 탐색기 → 관리자 권한 앱 창으로의 드래그앤드롭을 차단한 것이었음(커서만 움직이고 드롭해도 무반응인 게 특징) — 일반 권한 터미널에서 실행하니 정상 동작 확인. 코드 변경 없음
  - 드롭 안내 문구만 "CSV/Excel 파일을" → "CSV/Excel/MDF 파일을"로 갱신

- UI 변경: 왼쪽 사이드바(파일 패널)를 어두운 네이비 테마에서 밝은 테마로 전환
  - `app/theme.py`: `QWidget#Sidebar`와 그 안의 라벨/버튼/드롭 안내 문구, `QListWidget#FileList`를 전부 흰 배경/어두운 텍스트로 변경(Y축 리스트·오른쪽 패널과 톤 통일). 나머지 화면과 구분되도록 사이드바에 옅은 회색 테두리 추가. "결합하기" 파란 강조 버튼은 포인트 컬러라 그대로 둠
  - 오프스크린 렌더링으로 스크린샷 찍어 확인 후 사용자가 실제 프로그램에서도 확인 완료
- 기능 변경: Y/X축 편집 다이얼로그(더블클릭, `axis_edit`)의 Min/Max 값을 소수점 4자리로 반올림해서 표시
  - `app/figure_options.py`: 기존에는 `get_xlim`/`get_ylim`이 돌려주는 float를 그대로 넘겨서 matplotlib `_formlayout`이 `repr()`로 부동소수점 오차까지 그대로 보여줬음(예: `16.264285714285716`). `round(v, 4)`로 미리 반올림해서 넘기도록 수정 — `_formlayout.fedit`이 필드 서식을 커스터마이즈하는 훅을 제공하지 않아 값 자체를 반올림하는 방법 외에는 없음
  - 가짜 `fedit`으로 `datalist`를 가로채서 `-1.6547891234567` -> `-1.6548`처럼 4자리로 반올림되는 것을 확인

## 2026-07-23

- 기능 추가: CSV/Excel 파일을 MDF(.mf4)로 변환해서 캐시처럼 저장하는 기능
  - `app/data_loader.py`: `convert_to_mdf()`(DataFrame -> 컬럼별 `Signal` 생성 후 저장)와 `read_mdf()`(MDF -> DataFrame) 추가. `SUPPORTED_SUFFIXES`에 `.mf4`/`.mdf` 포함
  - 사전 조사(실측): CSV는 pandas C 파서가 이미 빨라 MDF 캐싱 이득이 없었지만, Excel(.xlsx)은 openpyxl의 셀 단위 XML 파싱이 병목이라 실측상 재로딩이 크게 빨라짐(100,000행 xlsx 기준 3.7초 -> 0.19초, 실제 86,206행 79컬럼 운전 데이터 기준 17.8초 -> 0.30초, 약 60배)
  - 실전에서 겪은 asammdf(8.8.22) 함정과 대응: (1) pandas 3.0 문자열 dtype과 안 맞아 DataFrame을 통째로 못 넘겨서 컬럼별로 수동 `Signal` 생성, 문자열은 UTF-8 bytes로 인코딩한 고정폭 numpy `'S'` 배열로 변환(object dtype bytes 배열은 거부됨), (2) `MDF.save()`가 지정 확장자를 무시하고 항상 `.mf4`로 저장, (3) `MDF.to_dataframe()`이 채널을 숫자형 먼저/문자열 나중으로 재배열하고 채널 이름의 앞뒤 공백을 지워버려서, 원래 컬럼 순서를 사이드카 JSON(`<파일명>.mf4.columns.json`)에 저장해뒀다가 공백을 무시하고 매칭해 복원하도록 처리(실제 79컬럼 데이터에서 공백 포함 채널명 3개 때문에 전체 순서 복원이 통째로 실패했던 걸 재현 후 수정)
  - `app/main_window.py`: "MDF로 변환" 버튼 추가, 파일 열기 다이얼로그 필터에 `.mf4`/`.mdf` 포함
  - `requirements.txt`에 `asammdf` 추가
- 기능 변경: 파일 목록 복수 선택 지원, "결합하기"/"MDF로 변환"이 전체가 아닌 선택한 파일만 대상으로 동작
  - `app/main_window.py`: `QListWidget.setSelectionMode(ExtendedSelection)` 추가. `_combine_and_display`/`_convert_selected_to_mdf`가 선택 항목이 없으면 안내 메시지만 띄우고 동작하지 않도록 변경(이전엔 선택 없으면 전체 대상으로 동작했음)
- 기능 추가: 멀티 Y축 그래프 (사용자 제공 참고 이미지 기반)
  - `app/plot_canvas.py`: `plot_lines()`가 체크된 Y축 컬럼마다 `twinx()`로 별도 축을 만들어 왼쪽/오른쪽으로 번갈아 바깥으로 배치(`_OUTWARD_STEP_PT`), 각 축의 라벨/눈금 색을 해당 선 색과 맞춤
  - 실제로 겪은 버그 2개를 실측 재현 후 수정: (1) `handles, labels = ax.get_legend_handles_labels()`가 X축 라벨 배열을 담아둔 변수명 `labels`를 그대로 재사용해서, X축 눈금에 날짜/시간 대신 마지막으로 그린 컬럼 이름이 표시되던 클로저 버그(변수명을 `line_labels`로 분리해 수정) — 79컬럼 실데이터로 재현/검증, (2) `constrained_layout=True`가 여러 개의 바깥으로 밀어낸(outward-offset) 축의 자리를 안정적으로 계산하지 못해 축 라벨이 엉뚱한 위치(그래프 하단)에 겹쳐 그려지는 걸 실측으로 확인 — Figure 크기(인치) 기준으로 직접 여백을 계산하는 방식(`subplots_adjust`)으로 교체해 해결
  - `_on_scroll`(마우스 휠 확대/축소)도 여러 축을 지원하도록 변경: 커서의 화면상 세로 위치를 각 축의 `transAxes` 비율로 변환해 모든 축에 동일 비율로 확대/축소 적용
- 기능 추가: 그래프 범례(legend)를 마우스로 드래그해서 옮길 수 있도록 `legend.set_draggable(True)` 적용(데이터를 가릴 때 사용자가 직접 위치 조정 가능)
- 배포 방식 조사 및 변경: PyInstaller 빌드를 `--onefile`에서 `--onedir`로 변경
  - 원인 조사: (1) onefile은 실행할 때마다 압축 해제가 필요해 시작이 느림(실측 체감), (2) USB에서 onefile exe를 직접 실행하면 압축 해제 도중 파일 하나를 못 읽어 실행 자체가 실패하는 사례 실제 발생(`Failed to extract entry: ... failed to open archive file!`), (3) Windows 11 Smart App Control이 서명 안 된 exe를 자체 판단으로 막았다 안 막았다 하는 걸 이벤트 로그(`Microsoft-Windows-CodeIntegrity/Operational`, 이벤트 ID 3033/3077)로 반복 확인 — 같은 프로젝트를 4번 빌드했는데 3번은 통과, 1번은 차단됨. onedir로 바꾼 뒤에는(같은 PC, SAC 켠 상태에서도) 차단 없이 실행됨을 확인
  - `CLAUDE.md`의 빌드 명령/설명을 onedir 기준으로 갱신, 배포 시 `dist/DataViewer/` 폴더 전체(exe + `_internal/`)를 옮겨야 한다는 점 명시

## 2026-07-22

- 버그 수정: 대용량 CSV 5개(약 128만 행) 결합 후 그래프가 무한 로딩하는 문제 조사 및 수정
  - 실제 샘플 데이터로 벤치마크한 결과, 원인은 결합(`combine_frames`) 자체가 아니라 그래프 렌더링(`plot_canvas.plot_lines`)이었음
  - X축(`Current Time`)이 문자열 타임스탬프라 matplotlib이 범주형 축으로 처리, 128만 개 고유값을 변환하느라 컬럼당 수 초~수십 분 소요(마커+범례 `loc="best"`까지 겹치면 15분 이상 걸려도 안 끝남을 실측으로 확인)
  - `app/plot_canvas.py`: 숫자/날짜형이 아닌 X축은 위치 인덱스로 그리고 눈금 라벨만 원래 문자열로 보여주도록 변경, 마커는 데이터가 500행 이하일 때만 표시, 범례 위치를 `loc="best"` 대신 `loc="upper right"`로 고정
  - 수정 후 실측: 전체 파이프라인(로드 1.8s + 결합 0.1s + 그래프 3.9s) ≈ 6초로 단축 (수정 전에는 그래프 단계에서만 15분 이상 무응답)
- 기능 변경: Y축 후보/그래프 자동 표시 동작 개선
  - `app/data_loader.py`: `numeric_columns()` 추가 — `pd.to_numeric` 변환 시 값이 하나도 안 남는(Status, Save Period 같은 텍스트 전용) 컬럼을 Y축 후보에서 제외
  - `app/main_window.py`: `_refresh_y_list`가 `numeric_columns` 기준으로 목록을 필터링하도록 변경. 결합 직후 Y축 체크 상태를 전부 미체크로 초기화하고 `_combine_and_display`에서 `_update_plot` 자동 호출을 제거(대신 `_plot_canvas.clear()`로 이전 그래프만 정리) — 사용자가 실제로 체크한 컬럼만 그래프에 나타남
  - `CLAUDE.md`의 `main_window.py`/`data_loader.py`/`plot_canvas.py` 설명을 최신 동작에 맞춰 갱신
  - 실측(샘플 데이터 5개, 128만 행): 결합 직후 그래프 0개 라인으로 시작, 체크박스 하나 체크 시 0.2초 만에 해당 라인 표시 확인
- 기능 추가: 그래프 확대/축소
  - `app/main_window.py`: 그래프 위에 matplotlib `NavigationToolbar2QT` 추가 — 부분 확대(드래그 사각형), 이동, 원래대로/이전/다음 보기, 저장 버튼 제공
  - `app/plot_canvas.py`: `scroll_event`를 연결해 마우스 커서 위치를 중심으로 휠로 확대/축소하는 `_on_scroll` 추가
  - 헤드리스 Qt(`QT_QPA_PLATFORM=offscreen`)로 스크린샷을 찍어 툴바와 그래프가 정상 렌더링되는지, 휠 확대/축소로 xlim이 좁아지고/넓어지는지 실측 확인
- 버그 수정: "원래대로"(Home) 버튼이 원래 그래프로 안 돌아오는 문제 수정
  - 원인: matplotlib 툴바는 사용자가 툴바의 이동/부분 확대를 처음 드래그할 때만 기준 뷰(홈)를 자동으로 기록하는데, 마우스 휠 확대(`PlotCanvas._on_scroll`)는 툴바를 거치지 않아 휠로만 확대한 경우 기준이 아예 안 잡혀 있었음
  - `app/main_window.py`: `_update_plot`에서 그래프를 새로 그릴 때마다 `self._plot_toolbar.update()`로 기록을 지우고 `push_current()`로 지금 이 전체 보기를 기준으로 다시 등록하도록 수정
  - 검증: 헤드리스로 툴바를 전혀 안 쓰고 휠로만 5번 확대한 뒤 `toolbar.home()` 호출 → 원래 xlim/ylim으로 정확히 복원됨을 실측 확인(수정 전에는 복원 안 됨)
- 기능 변경: 파일 목록 표시를 전체 경로에서 파일명으로 변경, 그래프 툴바에서 이전/다음 보기 버튼 제거
  - `app/main_window.py`: 파일 목록 아이템은 `Path(path_str).name`을 텍스트로 보여주고, 결합/제거에 쓰는 실제 전체 경로는 `item.setData(_FILE_PATH_ROLE, path_str)`로 따로 보관. `_remove_selected_files`도 이 데이터로 조회하도록 변경
  - `_PlotToolbar(NavigationToolbar2QT)` 서브클래스를 추가해 `toolitems`에서 Back/Forward만 제외(실제로는 `_update_plot`이 매번 `toolbar.update()`로 뷰 기록을 지우기 때문에 항상 비활성이었음)
  - 검증: 실제 샘플 CSV로 파일 목록에 파일명만 뜨는지, 제거가 전체 경로 기준으로 여전히 정상 동작하는지, 툴바 버튼 목록이 `[Home, Pan, Zoom, Subplots, Save]`인지 실측 확인
  - 처음에 Customize(Figure options) 버튼도 같이 뺐다가, 사용자가 명시적으로 유지를 원해 되돌림(아래 항목 참고)
- 조사: Customize(Figure options)의 "(Re-)Generate automatic legend" 체크 해제 시 범례가 원래 위치로 안 돌아오는 문제
  - 원인은 우리 코드 버그가 아니라 matplotlib `figureoptions.py`의 다이얼로그 설계: 이 체크박스는 켜짐/꺼짐을 유지하는 토글이 아니라 열 때마다 항상 미체크로 초기화되는 "지금 다시 그려라" 일회성 트리거임. 체크 후 OK를 누르면 `axes.legend(ncols=...)`를 loc 없이 호출해 matplotlib 기본 위치(`best`)로 다시 그리는데, 우리 기본값(`loc="upper right"`)과 달라서 "왼쪽으로 이동한 것처럼" 보임. 체크 해제 후 OK는 단순히 "이번엔 재생성 안 함"일 뿐 되돌리기 로직이 없어서 이동한 채로 남음
  - Customize 버튼 자체를 없애는 대신 그대로 유지하기로 함(사용자 요청). 대신 이미 있는 "그래프 새로고침" 버튼(또는 X축/Y축 체크박스 변경)을 누르면 `_update_plot` → `plot_lines`가 `ax.clear()` 후 `loc="upper right"`로 처음부터 다시 그리므로 그게 실질적인 복구 방법임을 확인
  - 검증: 실제 데이터로 legend 위치 코드가 `1`(upper right, 우리 기본값) → Customize의 "재생성" 동작 재현 후 `0`(best) → "그래프 새로고침" 재현(`_update_plot` 재호출) 후 다시 `1`로 돌아오는 것을 실측 확인. `CLAUDE.md`에 이 matplotlib 다이얼로그의 함정과 복구 방법을 기록
- 기능 변경: Figure options(Customize)에서 X/Y축 Scale(linear/log/symlog/logit) 설정 기능 제거
  - matplotlib 내장 다이얼로그는 필드 단위로 뺄 수 있는 공개 API가 없어서, `app/figure_options.py`에 `figureoptions.figure_edit` 전체를 그대로 옮겨온 뒤 Scale 드롭다운만 제거한 버전을 새로 만듦(`apply_callback`의 축당 필드 수를 4개→3개로 조정)
  - `app/main_window.py`: `_PlotToolbar.edit_parameters()`를 오버라이드해서 Customize 버튼이 matplotlib 기본 다이얼로그 대신 이 버전을 열도록 변경
  - 검증: `_formlayout.fedit`을 가짜로 바꿔치기해서 다이얼로그에 전달되는 필드 목록에 "Scale"이 없는지, 필드 개수가 예상대로(13개: Title+sep+축당 5개×2+범례 체크)인지, 그리고 실제 제출값 형태로 `apply_callback`을 호출했을 때 제목/Min/Max/Label/범례가 Scale 없이도 정상 적용되는지 실측 확인
- `DataViewer.exe` 재빌드(위 변경들 반영)

## 2026-07-21

- 저장소 초기화, `README.md` 작성, GitHub(`eomhyunjin/DataViewer`) 원격 연결 확인
- MVP 구현: PySide6 데스크톱 앱으로 CSV/Excel 파일 결합 + 선 그래프 시각화
  (`app/data_loader.py`, `app/table_model.py`, `app/plot_canvas.py`, `app/main_window.py`, `main.py`)
- PyInstaller로 `DataViewer.exe` 빌드(onefile, windowed)
- 버그 수정 및 기능 추가:
  - 드래그앤드롭이 동작하지 않던 문제 수정 (`dragMoveEvent` 미구현이 원인)
  - Y축 체크리스트: 결합 직후 전체 컬럼 표시, X축으로 선택된 컬럼은 Y축 목록에서 자동 제외, 체크박스로 그래프에 즉시 토글
  - matplotlib 한글 폰트(Malgun Gothic) 설정으로 라벨 깨짐 수정
- 테스트용 샘플 데이터(`sample_data/`) 2개 생성 (열 구조 동일한 xlsx)
- `CLAUDE.md` 작성: 개발 명령어, 아키텍처, 각 모듈의 비직관적 동작 설명
- 프로젝트 전체를 `C:\Users\hj\DataViewer` → `D:\claude_worker\DataViewer`로 이동 (가상환경/빌드 산출물은 새로 생성, 기존 위치는 삭제)
- 새 위치에서 exe 재빌드
- 버전 관리 체계 도입: `app/__init__.py`에 `__version__` 추가(창 제목에 표시), `v0.1.0` git 태그 생성, GitHub CLI(`gh`) 설치 및 로그인, `v0.1.0` GitHub Release 생성 후 exe 첨부
- `CLAUDE.md`에 버전 관리 & 릴리스 절차 문서화
- `CHANGELOG.md` 생성 및 릴리스 절차에 편입
- 이 `WORKLOG.md` 생성
- `CLAUDE.md`에 기록 규칙(작업 확정 시마다 WORKLOG/CHANGELOG 기록) 명문화
- UI 리디자인: 사용자가 제공한 참고 이미지(어두운 사이드바 + 밝은 콘텐츠의 SaaS 대시보드 컨셉)를 바탕으로 `app/theme.py`에 QSS 스타일시트 작성, `main_window.py`에 오브젝트 이름 부여 및 레이아웃 여백 정리, `main.py`에서 앱 전체에 스타일 적용. 실제 실행 후 스크린샷으로 확인
