"""메인 윈도우: 파일 로딩(드래그앤드롭/버튼), 결합, 테이블, 그래프 UI."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.data_loader import combine_frames, is_supported_file, load_files
from app.plot_canvas import PlotCanvas
from app.table_model import PandasTableModel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DataViewer")
        self.resize(1100, 700)
        self.setAcceptDrops(True)

        self._loaded_frames: dict[str, object] = {}
        self._table_model = PandasTableModel()
        self._y_checked: dict[str, bool] = {}

        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)

        # --- 왼쪽: 파일 목록 패널 ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        open_button = QPushButton("파일 열기")
        open_button.clicked.connect(self._open_files_dialog)
        left_layout.addWidget(open_button)

        drop_hint = QLabel("여기에 CSV/Excel 파일을\n드래그 앤 드롭하세요")
        drop_hint.setAlignment(Qt.AlignCenter)
        drop_hint.setStyleSheet("color: gray; border: 1px dashed gray; padding: 12px;")
        left_layout.addWidget(drop_hint)

        self._file_list = QListWidget()
        left_layout.addWidget(self._file_list)

        remove_button = QPushButton("선택 파일 제거")
        remove_button.clicked.connect(self._remove_selected_files)
        left_layout.addWidget(remove_button)

        combine_button = QPushButton("결합하기")
        combine_button.clicked.connect(self._combine_and_display)
        left_layout.addWidget(combine_button)

        left_panel.setMaximumWidth(280)

        # --- 가운데: 테이블 ---
        self._table_view = QTableView()
        self._table_view.setModel(self._table_model)
        self._table_view.setSelectionBehavior(QAbstractItemView.SelectRows)

        # --- 오른쪽: 축 선택 + 그래프 ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        axis_layout = QHBoxLayout()
        axis_layout.addWidget(QLabel("X축:"))
        self._x_combo = QComboBox()
        self._x_combo.currentTextChanged.connect(self._on_x_changed)
        axis_layout.addWidget(self._x_combo)
        right_layout.addLayout(axis_layout)

        right_layout.addWidget(QLabel("Y축 (체크하면 그래프에 표시/숨김):"))
        self._y_list = QListWidget()
        self._y_list.setSelectionMode(QAbstractItemView.NoSelection)
        self._y_list.setMaximumHeight(120)
        self._y_list.itemChanged.connect(self._on_y_item_changed)
        right_layout.addWidget(self._y_list)

        plot_button = QPushButton("그래프 새로고침")
        plot_button.clicked.connect(self._update_plot)
        right_layout.addWidget(plot_button)

        self._plot_canvas = PlotCanvas()
        right_layout.addWidget(self._plot_canvas)

        splitter = QSplitter()
        splitter.addWidget(left_panel)
        splitter.addWidget(self._table_view)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 2)
        root_layout.addWidget(splitter)

    # --- 드래그앤드롭 ---
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        # dragEnterEvent만 구현하면 Qt 기본 동작이 드래그 중 계속 거부 상태를
        # 유지해서 실제 dropEvent가 발생하지 않는다. 이동 중에도 매번 수락해야 한다.
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls()]
        event.acceptProposedAction()
        self._add_files(paths)

    def _open_files_dialog(self) -> None:
        file_names, _ = QFileDialog.getOpenFileNames(
            self,
            "CSV/Excel 파일 선택",
            "",
            "데이터 파일 (*.csv *.xlsx *.xls)",
        )
        self._add_files([Path(name) for name in file_names])

    def _add_files(self, paths: list[Path]) -> None:
        supported = [p for p in paths if is_supported_file(p)]
        unsupported = [p for p in paths if not is_supported_file(p)]

        if unsupported:
            names = "\n".join(p.name for p in unsupported)
            QMessageBox.warning(self, "지원하지 않는 파일", f"다음 파일은 무시됩니다:\n{names}")

        result = load_files(supported)
        for path_str in result.frames:
            if path_str not in self._loaded_frames:
                self._file_list.addItem(path_str)
        self._loaded_frames.update(result.frames)

        if result.errors:
            details = "\n".join(f"{k}: {v}" for k, v in result.errors.items())
            QMessageBox.warning(self, "파일 읽기 오류", details)

    def _remove_selected_files(self) -> None:
        for item in self._file_list.selectedItems():
            path_str = item.text()
            self._loaded_frames.pop(path_str, None)
            self._file_list.takeItem(self._file_list.row(item))

    # --- 결합/표시 ---
    def _combine_and_display(self) -> None:
        if not self._loaded_frames:
            QMessageBox.information(self, "결합", "먼저 파일을 추가해주세요.")
            return

        result = combine_frames(self._loaded_frames)
        self._table_model.set_dataframe(result.data)

        if result.mismatched_files:
            names = "\n".join(Path(p).name for p in result.mismatched_files)
            QMessageBox.warning(
                self,
                "열 구조 불일치",
                f"다음 파일은 열 구조가 달라 결합에서 제외되었습니다:\n{names}",
            )

        columns = list(result.data.columns)
        self._y_checked = {c: True for c in columns}  # 처음엔 전체 표시

        self._x_combo.blockSignals(True)
        self._x_combo.clear()
        self._x_combo.addItems(columns)
        self._x_combo.blockSignals(False)

        self._refresh_y_list()
        self._update_plot()

    # --- X/Y축 선택 ---
    def _on_x_changed(self, _text: str) -> None:
        self._refresh_y_list()
        self._update_plot()

    def _refresh_y_list(self) -> None:
        """Y축 목록을 채운다. 현재 X축으로 선택된 열은 목록에서 제외한다."""
        x_column = self._x_combo.currentText()
        columns = list(self._table_model.dataframe().columns)

        self._y_list.blockSignals(True)
        self._y_list.clear()
        for column in columns:
            if column == x_column:
                continue
            item = QListWidgetItem(column)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            checked = self._y_checked.get(column, True)
            item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
            self._y_list.addItem(item)
        self._y_list.blockSignals(False)

    def _on_y_item_changed(self, item: QListWidgetItem) -> None:
        self._y_checked[item.text()] = item.checkState() == Qt.Checked
        self._update_plot()

    # --- 그래프 ---
    def _update_plot(self) -> None:
        data = self._table_model.dataframe()
        if data.empty:
            return

        x_column = self._x_combo.currentText()
        y_columns = [
            self._y_list.item(i).text()
            for i in range(self._y_list.count())
            if self._y_list.item(i).checkState() == Qt.Checked
        ]

        if not x_column or not y_columns:
            self._plot_canvas.clear()
            return

        skipped = self._plot_canvas.plot_lines(data, x_column, y_columns)
        if skipped:
            names = ", ".join(skipped)
            QMessageBox.warning(self, "그래프", f"숫자형이 아니라 제외된 열: {names}")
