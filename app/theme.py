"""애플리케이션 전체에 적용할 QSS 스타일시트.

참고 컨셉: 어두운 네이비 사이드바 + 밝고 깔끔한 메인 영역 + 파란 계열 포인트 컬러
(Asana류 모던 SaaS 대시보드 느낌).
"""

STYLESHEET = """
* {
    font-family: "Segoe UI", "Malgun Gothic", sans-serif;
    font-size: 10pt;
    color: #151B26;
}

QMainWindow, QWidget#Central {
    background-color: #F6F7F9;
}

QSplitter::handle {
    background-color: #E4E6EA;
    width: 1px;
}

/* --- 왼쪽 사이드바 --- */
QWidget#Sidebar {
    background-color: #1E2130;
    border-radius: 10px;
}

QWidget#Sidebar QLabel {
    color: #9CA3AF;
}

QLabel#SidebarTitle {
    color: #FFFFFF;
    font-size: 12pt;
    font-weight: 600;
    padding: 2px 2px 6px 2px;
}

QWidget#Sidebar QPushButton {
    background-color: #2A2D40;
    color: #E4E6EB;
    border: 1px solid #363A52;
    border-radius: 6px;
    padding: 8px 12px;
    text-align: left;
}
QWidget#Sidebar QPushButton:hover {
    background-color: #363A52;
}
QWidget#Sidebar QPushButton:pressed {
    background-color: #40445E;
}

QListWidget#FileList {
    background-color: #262A3D;
    color: #E4E6EB;
    border: 1px solid #33374D;
    border-radius: 8px;
    padding: 4px;
}
QListWidget#FileList::item {
    padding: 6px 8px;
    border-radius: 4px;
}
QListWidget#FileList::item:selected {
    background-color: #4573D2;
    color: #FFFFFF;
}

QLabel#DropHint {
    color: #7B8094;
    border: 1px dashed #40445E;
    border-radius: 8px;
    padding: 14px;
}

/* --- 강조(주요 액션) 버튼 --- */
QWidget#Sidebar QPushButton#PrimaryButton,
QPushButton#PrimaryButton {
    background-color: #4573D2;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 9px 14px;
    font-weight: 600;
}
QWidget#Sidebar QPushButton#PrimaryButton:hover,
QPushButton#PrimaryButton:hover {
    background-color: #3A63B8;
}
QWidget#Sidebar QPushButton#PrimaryButton:pressed,
QPushButton#PrimaryButton:pressed {
    background-color: #30549C;
}

/* --- 가운데 테이블 --- */
QTableView {
    background-color: #FFFFFF;
    alternate-background-color: #F6F7F9;
    gridline-color: #EBEDF0;
    border: 1px solid #E4E6EA;
    border-radius: 8px;
    selection-background-color: #E8F0FE;
    selection-color: #151B26;
}
QHeaderView::section {
    background-color: #F6F7F9;
    color: #6B6F76;
    padding: 8px;
    border: none;
    border-bottom: 2px solid #E4E6EA;
    font-weight: 600;
}
QTableView QTableCornerButton::section {
    background-color: #F6F7F9;
    border: none;
}

/* --- 오른쪽 패널 --- */
QLabel#SectionLabel {
    color: #151B26;
    font-weight: 600;
    font-size: 10.5pt;
    padding-top: 4px;
}

QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #D8DBE0;
    border-radius: 6px;
    padding: 6px 8px;
}
QComboBox:hover {
    border-color: #4573D2;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}

QListWidget#YList {
    background-color: #FFFFFF;
    border: 1px solid #D8DBE0;
    border-radius: 8px;
    padding: 4px;
}
QListWidget#YList::item {
    padding: 5px 6px;
    border-radius: 4px;
}
QListWidget#YList::item:hover {
    background-color: #F1F4FA;
}

QPushButton#SecondaryButton {
    background-color: #FFFFFF;
    color: #151B26;
    border: 1px solid #D8DBE0;
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 600;
}
QPushButton#SecondaryButton:hover {
    background-color: #F1F4FA;
    border-color: #4573D2;
}

QWidget#PlotCard {
    background-color: #FFFFFF;
    border: 1px solid #E4E6EA;
    border-radius: 8px;
}
"""
