# 작업 기록

세션/작업 단위로 무엇을 했는지 기록합니다. 릴리스 시점의 사용자 대상 변경 요약은 `CHANGELOG.md`를 참고하세요. 이 파일은 그보다 더 잘게, 작업할 때마다 남기는 개발 로그입니다.

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
