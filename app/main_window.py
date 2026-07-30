"""메인 윈도우: 파일 로딩(드래그앤드롭/버튼), 결합, 테이블, 그래프 UI."""
from __future__ import annotations

from pathlib import Path

from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent, QMouseEvent
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
from app.data_loader import (
    MDF_SUFFIXES,
    combine_frames,
    convert_to_mdf,
    is_supported_file,
    load_files,
    numeric_columns,
)
from app.plot_canvas import PlotCanvas
from app.table_model import PandasTableModel

_FILE_PATH_ROLE = Qt.UserRole


class _PlotToolbar(NavigationToolbar2QT):
    """이전/다음 보기(Back/Forward), Pan 버튼을 뺀 도구모음.

    `_update_plot`이 다시 그릴 때마다 `self._plot_toolbar.update()`로 뷰 기록을 통째로
    지우기 때문에(원래대로 버튼이 항상 최신 전체 보기로 돌아가게 하려고 그렇게 함)
    이전/다음 보기로 되돌아갈 기록이 애초에 남지 않아 실사용상 의미가 없어서 뺐다.

    Pan 버튼("Left button pans, Right button zooms")은 버튼을 먼저 눌러 모드를 켜야만
    동작해서 한 번 더 클릭해야 하는 게 번거롭다는 사용자 요청에 따라 뺐다. 그 대신
    같은 동작(왼쪽 버튼 드래그=이동, 오른쪽 버튼 드래그=확대·축소)을 그래프 위에서 바로
    쓸 수 있도록 `PlotCanvas`가 항상 켜놓는다(자세한 구현은 `PlotCanvas._on_button_press`
    참고).
    """

    toolitems = [item for item in NavigationToolbar2QT.toolitems if item[0] not in ("Back", "Forward", "Pan")]

    def edit_parameters(self) -> None:
        """Customize 버튼 동작. matplotlib 기본 다이얼로그 대신 Scale 드롭다운과 Axes 탭을
        뺀 `app.figure_options.figure_edit`을 쓴다 — 자세한 이유는 그 모듈의 docstring
        참고. 축 Min/Max/Label 편집은 그래프에서 해당 축을 더블클릭하면 뜨는 작은
        다이얼로그(`PlotCanvas._on_axis_double_click`)가 대신한다. 커브 색을 바꾸면
        범례/축 색도 같이 갱신되도록 `on_apply`로 `refresh_legend`를 넘긴다.
        """
        axes = self.canvas.figure.get_axes()
        if not axes:
            return
        _figure_options.figure_edit(axes[0], self, on_apply=self.canvas.refresh_legend)


class _FileListWidget(QListWidget):
    """드래그로 항목 순서를 바꿀 수 있는 파일 목록. 순서가 바뀌면 `order_changed`를 emit한다.

    QListWidget은 `moveRows()`를 구현하지 않아 내부 드래그 이동이 항상 model의
    rowsMoved로 이어진다는 보장이 없다(Qt 버전에 따라 remove+insert로 처리될 수 있음).
    그래서 신호 종류에 의존하지 않고 dropEvent 자체를 가로채 드롭이 끝난 뒤 한 번만
    emit한다.
    """

    order_changed = Signal()
    empty_area_double_clicked = Signal()

    def dropEvent(self, event: QDropEvent) -> None:
        super().dropEvent(event)
        self.order_changed.emit()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """항목이 없는 빈 여백을 더블클릭하면 `empty_area_double_clicked`를 emit한다.

        구간 표시를 해제하는 용도(빈 곳을 더블클릭 = 표시 해제)로 쓴다. 항목 위를
        더블클릭했을 때는 그대로 기본 동작(itemDoubleClicked 등)을 타도록 넘긴다.
        """
        if self.itemAt(event.pos()) is None:
            self.empty_area_double_clicked.emit()
            return
        super().mouseDoubleClickEvent(event)


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
        # 마지막으로 "결합하기"를 눌렀을 때 결합했던 파일 경로들(목록 순서대로).
        # 드래그로 순서를 바꾸면 그 순간 화면 선택은 끌던 항목만 남기 때문에,
        # 순서 변경 시 재결합할 대상은 실시간 selectedItems()가 아니라 이 목록을 써야 한다.
        self._combined_paths: list[str] = []
        # 결합된 테이블에서 각 파일이 차지하는 [시작, 끝) 행 구간. 파일을 더블클릭했을 때
        # 그래프에서 어느 구간을 칠할지 찾는 데 쓴다. 열 구조가 달라 결합에서 제외된
        # 파일은 여기 들어가지 않는다.
        self._file_row_ranges: dict[str, tuple[int, int]] = {}
        # 현재 그래프에 구간 표시 중인 파일. 그래프가 다시 그려져도(Y축 체크 변경 등)
        # 표시가 계속 유지되도록 _update_plot()에서 이 값을 참고해 다시 칠한다.
        self._highlighted_path: str | None = None

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

        drop_hint = QLabel("여기에 CSV/Excel/MDF 파일을\n드래그 앤 드롭하세요")
        drop_hint.setObjectName("DropHint")
        drop_hint.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(drop_hint)

        self._file_list = _FileListWidget()
        self._file_list.setObjectName("FileList")
        self._file_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._file_list.setDragDropMode(QAbstractItemView.InternalMove)
        # 더블클릭은 그래프 구간 표시 용도로 쓴다. 기본 편집 트리거를 꺼두지 않으면
        # Qt가 더블클릭을 "이름 바꾸기" 시작으로도 처리해서 인라인 편집 상자가 함께 뜬다.
        self._file_list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._file_list.order_changed.connect(self._on_file_order_changed)
        self._file_list.itemDoubleClicked.connect(self._on_file_item_double_clicked)
        self._file_list.empty_area_double_clicked.connect(self._on_file_list_empty_double_clicked)
        left_layout.addWidget(self._file_list)

        remove_button = QPushButton("선택 파일 제거")
        remove_button.clicked.connect(self._remove_selected_files)
        left_layout.addWidget(remove_button)

        convert_button = QPushButton("MDF로 변환")
        convert_button.setObjectName("SecondaryButton")
        convert_button.clicked.connect(self._convert_selected_to_mdf)
        left_layout.addWidget(convert_button)

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
        # 그래프의 점을 더블클릭하면 테이블에서 해당 행으로 이동하도록 연결한다.
        self._plot_canvas.on_point_double_click = self._on_plot_point_double_click
        # 부분 확대(드래그로 사각형 선택), 이동, 원래대로 등 표준 그래프 탐색 도구.
        # 마우스 휠 확대/축소는 PlotCanvas._on_scroll이 별도로 처리한다.
        self._plot_toolbar = _PlotToolbar(self._plot_canvas, self)
        self._plot_toolbar.setObjectName("PlotToolbar")
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
            "CSV/Excel/MDF 파일 선택",
            "",
            "데이터 파일 (*.csv *.xlsx *.xls *.mf4 *.mdf)",
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
            if path_str in self._combined_paths:
                self._combined_paths.remove(path_str)
            self._file_list.takeItem(self._file_list.row(item))

    def _select_paths(self, paths: set[str]) -> None:
        """전달된 경로에 해당하는 항목들만 목록에서 선택 상태로 만든다."""
        for i in range(self._file_list.count()):
            item = self._file_list.item(i)
            item.setSelected(item.data(_FILE_PATH_ROLE) in paths)

    def _on_file_item_double_clicked(self, item: QListWidgetItem) -> None:
        """파일 목록에서 파일을 더블클릭하면, 그 파일이 결합된 데이터에서 차지하는 구간을 그래프에 배경색으로 표시한다."""
        path = item.data(_FILE_PATH_ROLE)
        row_range = self._file_row_ranges.get(path)
        if row_range is None:
            QMessageBox.information(
                self,
                "그래프 구간 표시",
                "이 파일은 현재 결합된 데이터에 포함되어 있지 않습니다. 먼저 결합해주세요.",
            )
            return
        self._highlighted_path = path
        self._plot_canvas.highlight_row_range(*row_range)

    def _on_file_list_empty_double_clicked(self) -> None:
        """파일 목록의 빈 여백을 더블클릭하면 표시 중이던 그래프 구간 강조를 해제한다."""
        if self._highlighted_path is None:
            return
        self._highlighted_path = None
        self._plot_canvas.clear_highlight()

    def _on_file_order_changed(self) -> None:
        """드래그로 파일 순서를 바꾸면, 이미 결합해서 보여주고 있던 데이터/그래프도 새 순서로 다시 그린다.

        드래그는 "끄는 항목"만 선택 상태로 남기기 때문에(여러 개를 선택해 결합해둔 뒤 그중
        하나만 끌면 나머지 선택은 풀림), 드롭 직후의 `selectedItems()`를 기준으로 재결합하면
        원래 결합해서 보여주던 파일 중 일부가 빠진 채로 다시 그려진다. 그래서 마지막으로
        "결합하기"를 눌렀을 때의 파일 집합(`self._combined_paths`)을 따로 기억해두고, 목록의
        새 순서를 그대로 반영해 그 집합으로 재결합한다. 아직 한 번도 결합하지 않았으면 조용히
        아무 것도 하지 않는다.
        """
        if not self._combined_paths:
            return

        combined_set = set(self._combined_paths)
        ordered_paths = [
            self._file_list.item(i).data(_FILE_PATH_ROLE)
            for i in range(self._file_list.count())
            if self._file_list.item(i).data(_FILE_PATH_ROLE) in combined_set
        ]
        if not ordered_paths:
            return

        self._combined_paths = ordered_paths
        self._apply_combine(ordered_paths, reset_selection=False)
        # 재결합 대상이 무엇인지 계속 눈에 보이도록, 드래그로 흐트러진 선택을 다시 맞춰준다.
        self._select_paths(combined_set)

    def _convert_selected_to_mdf(self) -> None:
        """목록에서 선택한 CSV/Excel 파일을 같은 폴더에 MDF(.mf4)로 저장해둔다.

        다음에 같은 데이터를 열 때는 원본 CSV/Excel 대신 여기서 만든 .mf4 파일을 "파일
        열기"로 불러오면 된다. CSV는 pandas C 파서가 이미 빨라 캐싱 이득이 거의 없지만,
        Excel(.xlsx)은 openpyxl의 셀 단위 XML 파싱이 병목이라 재로딩이 실측상 수십 배
        빨라진다(자세한 내용은 dataviewer-mdf-investigation 메모리 참고).
        """
        items = self._file_list.selectedItems()
        if not items:
            QMessageBox.information(self, "MDF 변환", "변환할 파일을 목록에서 선택해주세요.")
            return

        converted: list[Path] = []
        skipped: list[str] = []
        errors: dict[str, str] = {}

        for item in items:
            path_str = item.data(_FILE_PATH_ROLE)
            path = Path(path_str)
            if path.suffix.lower() in MDF_SUFFIXES:
                skipped.append(path.name)
                continue
            try:
                target = convert_to_mdf(path, self._loaded_frames[path_str])
                converted.append(target)
            except Exception as exc:  # noqa: BLE001 - 파일별 오류를 모아서 보여줘야 함
                errors[path.name] = str(exc)

        message_parts = []
        if converted:
            names = "\n".join(str(p) for p in converted)
            message_parts.append(f"다음 파일로 변환되었습니다(다음에는 이 파일을 열면 더 빠릅니다):\n{names}")
        if skipped:
            message_parts.append(f"이미 MDF라 건너뜀: {', '.join(skipped)}")
        if errors:
            details = "\n".join(f"{k}: {v}" for k, v in errors.items())
            message_parts.append(f"변환 실패:\n{details}")
        QMessageBox.information(self, "MDF 변환", "\n\n".join(message_parts) if message_parts else "변환할 파일이 없습니다.")

    # --- 결합/표시 ---
    def _combine_and_display(self) -> None:
        items = self._file_list.selectedItems()
        if not items:
            QMessageBox.information(self, "결합", "결합할 파일을 목록에서 선택해주세요.")
            return
        paths = [item.data(_FILE_PATH_ROLE) for item in items]
        self._combined_paths = paths
        self._apply_combine(paths, reset_selection=True)

    def _apply_combine(self, paths: list[str], *, reset_selection: bool) -> None:
        """전달된 파일 경로들을 그 순서대로 결합해서 테이블에 반영하고, 필요하면 그래프도 다시 그린다.

        `reset_selection=False`(드래그로 순서만 바꾼 경우)인데 결합 후 열 구성이 이전과
        똑같으면 X/Y 선택과 체크 상태를 그대로 유지한 채 새 순서의 데이터로 그래프까지
        다시 그린다. 열 구성이 달라졌으면(파일 선택 자체가 바뀐 경우 등) 새로 고른 것과
        똑같이 취급해 X/Y 선택을 초기화한다.
        """
        previous_columns = [self._x_combo.itemText(i) for i in range(self._x_combo.count())]

        selected_frames = {path: self._loaded_frames[path] for path in paths}
        result = combine_frames(selected_frames)
        self._table_model.set_dataframe(result.data)

        if result.mismatched_files:
            names = "\n".join(Path(p).name for p in result.mismatched_files)
            QMessageBox.warning(
                self,
                "열 구조 불일치",
                f"다음 파일은 열 구조가 달라 결합에서 제외되었습니다:\n{names}",
            )

        # combine_frames()가 mismatched_files를 뺀 나머지를 paths 순서 그대로 이어붙이므로,
        # 같은 순서로 각 파일의 길이를 누적하면 결합된 테이블에서 그 파일이 차지하는
        # [시작, 끝) 행 구간을 알 수 있다.
        mismatched = set(result.mismatched_files)
        row_ranges: dict[str, tuple[int, int]] = {}
        cursor = 0
        for path in paths:
            if path in mismatched:
                continue
            length = len(self._loaded_frames[path])
            row_ranges[path] = (cursor, cursor + length)
            cursor += length
        self._file_row_ranges = row_ranges
        if self._highlighted_path not in row_ranges:
            self._highlighted_path = None

        columns = list(result.data.columns)
        self._numeric_columns = set(numeric_columns(result.data))

        if reset_selection or columns != previous_columns:
            self._y_checked = {c: False for c in columns}  # 사용자가 체크하기 전까진 그래프를 그리지 않음

            self._x_combo.blockSignals(True)
            self._x_combo.clear()
            self._x_combo.addItems(columns)
            self._x_combo.blockSignals(False)

            self._refresh_y_list()
            self._plot_canvas.clear()  # 이전 결합 결과로 그려져 있던 그래프가 남아있지 않도록 비운다
            self._plot_toolbar.update()  # 이전 데이터의 확대/축소 기록(원래대로 버튼 포함)도 함께 비운다
        else:
            # 열 구성은 그대로이고 행 순서만 바뀐 경우: X/Y 선택을 유지한 채 새 순서로 다시 그린다.
            self._refresh_y_list()
            self._update_plot()

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
    def _on_plot_point_double_click(self, row: int) -> None:
        """그래프에서 더블클릭한 지점과 가장 가까운 행을 테이블에서 선택하고 보이는 위치로 스크롤한다."""
        if not 0 <= row < self._table_model.rowCount():
            return
        self._table_view.selectRow(row)
        self._table_view.scrollTo(self._table_model.index(row, 0), QAbstractItemView.PositionAtCenter)

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

        # plot_lines()는 매번 축을 새로 그리며 이전 구간 표시를 지우므로, 더블클릭으로
        # 표시해둔 파일이 있으면(Y축 체크 변경 등으로 다시 그려진 뒤에도) 같은 구간을 다시 칠한다.
        if self._highlighted_path is not None:
            row_range = self._file_row_ranges.get(self._highlighted_path)
            if row_range is not None:
                self._plot_canvas.highlight_row_range(*row_range)
            else:
                self._highlighted_path = None

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
