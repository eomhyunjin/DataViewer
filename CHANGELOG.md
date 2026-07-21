# Changelog

이 프로젝트의 버전별 주요 변경 사항을 기록합니다. [Keep a Changelog](https://keepachangelog.com/) 형식을 따르고, [시맨틱 버저닝](https://semver.org/lang/ko/)을 사용합니다.

## [Unreleased]

### Changed
- 어두운 사이드바 + 밝은 콘텐츠 영역의 모던 SaaS 대시보드 스타일로 UI 리디자인

## [v0.1.0] - 2026-07-21

### Added
- CSV(.csv), Excel(.xlsx/.xls) 파일을 드래그 앤 드롭 또는 파일 선택 버튼으로 불러오기
- 같은 열 구조를 가진 여러 파일을 행 단위로 결합, 열 구조가 다른 파일은 자동 제외 후 안내
- 결합된 데이터를 표(QTableView)로 확인
- X축/Y축 선택 후 선 그래프로 시각화
- Y축 다중 선택 및 체크박스로 그래프에 즉시 표시/숨김 토글, X축으로 선택된 열은 Y축 목록에서 자동 제외
- 한글 라벨이 깨지지 않도록 matplotlib 폰트 설정
- PyInstaller 기반 단일 실행파일(exe) 빌드, GitHub Releases로 배포
