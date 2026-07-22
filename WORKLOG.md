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
- `DataViewer.exe` 재빌드(위 두 변경 반영)

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
