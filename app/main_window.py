"""메인 윈도우: 파일 로딩(드래그앤드롭/버튼), 결합, 테이블, 그래프 UI."""
from __future__ import annotations

from pathlib import Path

from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
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

from app import __version__
from app import figure_options as _figure_options
from app.data_loader import combine_frames, is_supported_file, load_files, numeric_columns
from app.plot_canvas import PlotCanvas
from app.table_model import PandasTableModel

_FILE_PATH_ROLE = Qt.UserRole


class _PlotToolbar(NavigationToolbar2QT):
    """이전/다음 보기(Back/Forward) 버튼을 뺀 도구모음.

    `_update_plot`이 다시 그릴 때마다 `self._plot_toolbar.update()`로 뷰 기록을 통째로
    지우기 때문에(원래대로 버튼이 항상 최신 전체 보기로 돌아가게 하려고 그렇게 함)
    이전/다음 보기로 되돌아갈 기록이 애초에 남지 않아 실사용상 의미가 없어서 뺐다.
    """

    toolitems = [item for item in NavigationToolbar2QT.toolitems if item[0] not in ("Back", "Forward")]

    def edit_parameters(self) -> None:
        """Customize 버튼 동작. matplotlib 기본 다이얼로그 대신 X/Y축 Scale
        (linear/log/symlog/logit) 드롭다운만 뺀 `app.figure_options.figure_edit`을 쓴다
        — 자세한 이유는 그 모듈의 docstring 참고. 이 앱은 항상 축이 하나뿐이라
        matplotlib 원본에 있는 "여러 축 중 선택" 분기는 재현하지 않았다.
        """
        axes = self.canvas.figure.get_axes()
        if not axes:
            return
        _figure_options.figure_edit(axes[0], self)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"DataViewer v{__version__}")
        self.resize(1100, 700)
        self.setAcceptDrops(True)

        self._loaded_frames: dict[str, object] = {}
        self._table_model = PandasTableModel()
        self._y_checked: dict[str, bool] = {}
        self._numeric_columns: set[str] = set()

        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("Central")
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(16, 16, 16, 16)

        # --- 왼쪽: 파일 목록 패널 ---
        left_panel = QWidget()
        left_panel.setObjectName("Sidebar")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(10)

        left_layout.addWidget(QLabel("파일", objectName="SidebarTitle"))

        open_button = QPushButton("파일 열기")
        open_button.clicked.connect(self._open_files_dialog)
        left_layout.addWidget(open_button)

        drop_hint = QLabel("여기에 CSV/Excel 파일을\n드래그 앤 드롭하세요")
        drop_hint.setObjectName("DropHint")
        drop_hint.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(drop_hint)

        self._file_list = QListWidget()
        self._file_list.setObjectName("FileList")
        left_layout.addWidget(self._file_list)

        remove_button = QPushButton("선택 파일 제거")
        remove_button.clicked.connect(self._remove_selected_files)
        left_layout.addWidget(remove_button)

        combine_button = QPushButton("결합하기")
        combine_button.setObjectName("PrimaryButton")
        combine_button.clicked.connect(self._combine_and_display)
        left_layout.addWidget(combine_button)

        left_panel.setMaximumWidth(280)

        # --- 가운데: 테이블 ---
        self._table_view = QTableView()
        self._table_view.setModel(self._table_model)
        self._table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table_view.setAlternatingRowColors(True)
        self._table_view.horizontalHeader().setStretchLastSection(True)
        self._table_view.verticalHeader().setVisible(False)

        # --- 오른쪽: 축 선택 + 그래프 ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        right_layout.addWidget(QLabel("X축", objectName="SectionLabel"))
        self._x_combo = QComboBox()
        self._x_combo.currentTextChanged.connect(self._on_x_changed)
        right_layout.addWidget(self._x_combo)

        right_layout.addWidget(QLabel("Y축 (체크하면 그래프에 표시/숨김)", objectName="SectionLabel"))
        self._y_list = QListWidget()
        self._y_list.setObjectName("YList")
        self._y_list.setSelectionMode(QAbstractItemView.NoSelection)
        self._y_list.setMaximumHeight(120)
        self._y_list.itemChanged.connect(self._on_y_item_changed)
        right_layout.addWidget(self._y_list)

        plot_button = QPushButton("그래프 새로고침")
        plot_button.setObjectName("SecondaryButton")
        plot_button.clicked.connect(self._update_plot)
        right_layout.addWidget(plot_button)

        plot_card = QWidget()
        plot_card.setObjectName("PlotCard")
        plot_card_layout = QVBoxLayout(plot_card)
        plot_card_layout.setContentsMargins(8, 8, 8, 8)
        self._plot_canvas = PlotCanvas()
        # 부분 확대(드래그로 사각형 선택), 이동, 원래대로 등 표준 그래프 탐색 도구.
        # 마우스 휠 확대/축소는 PlotCanvas._on_scroll이 별도로 처리한다.
        self._plot_toolbar = _PlotToolbar(self._plot_canvas, self)
        plot_card_layout.addWidget(self._plot_toolbar)
        plot_card_layout.addWidget(self._plot_canvas)
        right_layout.addWidget(plot_card, stretch=1)

        splitter = QSplitter()
        splitter.addWidget(left_panel)
        splitter.addWidget(self._table_view)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 2)
        splitter.setHandleWidth(16)
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
                # 목록에는 파일명만 보여주고, 결합/제거에 쓰는 실제 키(전체 경로)는
                # 아이템 데이터로 따로 들고 있는다(같은 이름이 다른 폴더에 있어도 구분되도록).
                item = QListWidgetItem(Path(path_str).name)
                item.setData(_FILE_PATH_ROLE, path_str)
                self._file_list.addItem(item)
        self._loaded_frames.update(result.frames)

        if result.errors:
            details = "\n".join(f"{k}: {v}" for k, v in result.errors.items())
            QMessageBox.warning(self, "파일 읽기 오류", details)

    def _remove_selected_files(self) -> None:
        for item in self._file_list.selectedItems():
            path_str = item.data(_FILE_PATH_ROLE)
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
        self._numeric_columns = set(numeric_columns(result.data))
        self._y_checked = {c: False for c in columns}  # 사용자가 체크하기 전까진 그래프를 그리지 않음

        self._x_combo.blockSignals(True)
        self._x_combo.clear()
        self._x_combo.addItems(columns)
        self._x_combo.blockSignals(False)

        self._refresh_y_list()
        self._plot_canvas.clear()  # 이전 결합 결과로 그려져 있던 그래프가 남아있지 않도록 비운다
        self._plot_toolbar.update()  # 이전 데이터의 확대/축소 기록(원래대로 버튼 포함)도 함께 비운다

    # --- X/Y축 선택 ---
    def _on_x_changed(self, _text: str) -> None:
        self._refresh_y_list()
        self._update_plot()

    def _refresh_y_list(self) -> None:
        """Y축 목록을 채운다. 현재 X축으로 선택된 열과 숫자로 그릴 수 없는 열은 제외한다."""
        x_column = self._x_combo.currentText()
        columns = list(self._table_model.dataframe().columns)

        self._y_list.blockSignals(True)
        self._y_list.clear()
        for column in columns:
            if column == x_column or column not in self._numeric_columns:
                continue
            item = QListWidgetItem(column)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            checked = self._y_checked.get(column, False)
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
            self._plot_toolbar.update()
            return

        skipped = self._plot_canvas.plot_lines(data, x_column, y_columns)
        # matplotlib 툴바는 "원래대로" 버튼이 되돌아갈 기준(홈 뷰)을, 사용자가 처음으로 이동/부분
        # 확대를 시작하는 순간에야 자동으로 기록한다(matplotlib.backend_bases의
        # NavigationToolbar2._zoom_pan_handler 참고). 우리는 그 전에 마우스 휠로도 확대/축소가
        # 되는데(PlotCanvas._on_scroll) 휠 확대는 툴바를 거치지 않으므로 기준이 아예 안 잡힐 수
        # 있다. 그러면 "원래대로"를 눌러도 아무 일도 일어나지 않는다. 매번 새로 그린 직후 기록을
        # 지우고 지금 이 전체 보기를 기준으로 다시 잡아, 이후 어떤 방식으로 확대/축소하든 "원래대로"가
        # 항상 이 시점의 뷰로 돌아가도록 한다.
        self._plot_toolbar.update()
        self._plot_toolbar.push_current()
        if skipped:
            names = ", ".join(skipped)
            QMessageBox.warning(self, "그래프", f"숫자형이 아니라 제외된 열: {names}")
