# 작업 기록

세션/작업 단위로 무엇을 했는지 기록합니다. 릴리스 시점의 사용자 대상 변경 요약은 `CHANGELOG.md`를 참고하세요. 이 파일은 그보다 더 잘게, 작업할 때마다 남기는 개발 로그입니다.

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
