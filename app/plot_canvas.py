"""matplotlib 선 그래프를 Qt 위젯에 임베드."""
from __future__ import annotations

from typing import Callable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backend_bases import MouseButton, _Mode
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

from app import figure_options as _figure_options

# Windows 기본 한글 폰트로 설정해 축/범례의 한글이 깨지지 않도록 한다.
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

# 표식(marker)은 점이 이 개수 이하로 적을 때만 그린다. 대용량 데이터(수십만~수백만 행)에서
# 점마다 마커를 찍으면 픽셀이 뭉개져 보이지도 않을뿐더러 렌더링 비용만 늘어난다.
_MARKER_ROW_THRESHOLD = 500

# 두 번째 이후 Y축(twinx)을 왼쪽/오른쪽으로 바깥으로 밀어낼 때 축 하나당 벌리는 간격(포인트).
_OUTWARD_STEP_PT = 60

# DAQsystem(INCA/CANalyzer 스타일) 그래프와 톤을 맞추기 위한 커브 색상 팔레트.
# DAQsystem의 ui/main_window.py CURVE_PALETTE와 동일한 값을 그대로 사용한다.
_CURVE_PALETTE = ["#2563eb", "#d97706", "#16a34a", "#dc2626", "#7c3aed", "#0891b2", "#be185d", "#4d7c0f"]

# 그리드 선 색/굵기도 DAQsystem의 pyqtgraph showGrid(alpha=0.3)와 비슷한 옅은 톤으로 맞춘다.
_GRID_COLOR = "#94a3b8"
_GRID_ALPHA = 0.3


class PlotCanvas(FigureCanvasQTAgg):
    def __init__(self):
        self.figure = Figure(figsize=(5, 4))
        super().__init__(self.figure)
        # DAQsystem(pyqtgraph, background="w")과 톤을 맞추기 위해 배경을 명시적으로 흰색으로 고정한다.
        self.figure.set_facecolor("white")
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor("white")
        self._extra_axes: list = []  # 두 번째 이후 Y축(twinx)들. clear()/plot_lines()마다 새로 만든다.
        self._legend = None  # 현재 범례. 다음 plot_lines() 호출 때 드래그 위치를 이어받기 위해 들고 있는다.
        self._reference_line = None  # plot_lines()가 그린 첫 번째 선. 더블클릭한 x위치에서 가장 가까운 행을 찾는 기준.
        self._highlight_span = None  # highlight_row_range()가 그린 구간 배경. 다시 그릴 때마다 하나만 유지한다.
        # 그래프의 점을 더블클릭했을 때 호출된다(인자: 데이터프레임 내 행 위치). MainWindow가 연결해
        # 테이블에서 해당 행을 선택/스크롤하는 데 쓴다.
        self.on_point_double_click: Callable[[int], None] | None = None
        self.mpl_connect("scroll_event", self._on_scroll)
        self.mpl_connect("button_press_event", self._on_axis_double_click)
        self.mpl_connect("button_press_event", self._on_point_double_click)
        self.mpl_connect("button_press_event", self._on_button_press)
        self.mpl_connect("button_release_event", self._on_button_release)

    def _on_button_press(self, event) -> None:
        """그래프 위에서 왼쪽 버튼 드래그=이동, 오른쪽 버튼 드래그=확대/축소가 항상 되도록 한다.

        matplotlib 기본 Pan 도구("Left button pans, Right button zooms")와 완전히 같은
        동작이지만, 원래는 툴바에서 Pan 버튼을 눌러 모드를 켜야만 동작한다. 이 앱은 그
        버튼을 없애고 이 동작을 기본값으로 켜뒀다 — `NavigationToolbar2.press_pan`/
        `drag_pan`/`release_pan`을 그대로 재사용하는데, 이 메서드들은 `self.mode`(Pan
        모드 on/off 상태)를 참조하지 않고 그 자체로 동작하며, twinx로 만든 여러 Y축까지
        `Axes.start_pan`/`drag_pan`을 통해 자동으로 함께 다뤄준다.

        "Zoom"(사각형으로 확대) 버튼이 켜져 있으면(`toolbar.mode == _Mode.ZOOM`) 그 동작과
        겹치지 않도록 건너뛴다. 범례는 `self.figure`에 붙어 있어(축과 무관하게 항상 그
        위에 겹쳐 보임) 범례를 클릭해서 드래그로 옮기는 동작과 겹치지 않도록, 클릭 지점이
        범례 영역이면 이동/확대를 시작하지 않는다.
        """
        if event.button not in (MouseButton.LEFT, MouseButton.RIGHT) or event.dblclick:
            return
        toolbar = self.toolbar
        if toolbar is None or toolbar.mode != _Mode.NONE:
            return
        if self._legend is not None and self._legend.get_window_extent().contains(event.x, event.y):
            return
        toolbar.press_pan(event)

    def _on_button_release(self, event) -> None:
        """`_on_button_press`가 시작한 이동/확대 드래그를 마무리한다."""
        toolbar = self.toolbar
        if toolbar is not None and toolbar._pan_info is not None:
            toolbar.release_pan(event)

    def _on_axis_double_click(self, event) -> None:
        """눈금/라벨 등 축 영역을 더블클릭하면 그 축의 Min/Max/Label을 바로 편집하는
        작은 다이얼로그를 연다(`app.figure_options.axis_edit`). Customize(Figure options)
        버튼은 axes 전체를 다루는 큰 다이얼로그라 축 범위만 빠르게 바꾸기엔 번거로워서,
        축을 직접 더블클릭해서 편집할 수 있게 한 것.

        Axis(XAxis/YAxis)는 matplotlib Artist의 pick 가능한 contains()를 구현하지 않으므로
        (기본 구현은 항상 False), 대신 get_tightbbox()가 반환하는 디스플레이 좌표 bbox(눈금
        라벨+축 라벨을 포함하는 영역)로 직접 히트 테스트한다. twinx()로 만든 축들은 X축을
        공유하고 자기 xaxis는 숨기므로, X축 후보는 self.ax.xaxis 하나뿐이다.
        """
        if not event.dblclick or event.button != 1:
            return
        renderer = self.figure.canvas.get_renderer()
        candidates = [self.ax.xaxis, self.ax.yaxis, *(ax.yaxis for ax in self._extra_axes)]
        for axis in candidates:
            bbox = axis.get_tightbbox(renderer)
            if bbox is not None and bbox.contains(event.x, event.y):
                _figure_options.axis_edit(axis, self, on_apply=self.refresh_legend)
                return

    def _on_point_double_click(self, event) -> None:
        """그래프 위 지점을 더블클릭하면 그 x위치에 가장 가까운 행을 `on_point_double_click`으로 알린다.

        가장 가까운 "행"은 x값만으로 찾는다(더블클릭한 지점과 x가 가장 가까운 데이터 포인트).
        y_columns는 모두 같은 x_column을 공유하고 plot_lines()에서 어떤 값도 행 단위로 걸러내지
        않으므로(숫자 변환 실패는 NaN으로만 남김), 어떤 선을 기준으로 삼아도 같은 위치(인덱스)가
        데이터프레임의 같은 행을 가리킨다 — 그래서 첫 번째로 그려진 선(`_reference_line`) 하나만
        있으면 된다.

        `line.get_xdata(orig=False)`로 matplotlib이 그릴 때 실제 사용한(단위 변환을 이미 거친)
        x좌표를 그대로 재사용한다. X축이 날짜/문자열이라 원본 x값을 직접 변환해야 했다면
        matplotlib 내부 변환과 어긋날 위험이 있는데, 이미 변환된 값을 재사용하면 그 위험이 없다.
        """
        if not event.dblclick or event.button != 1:
            return
        if event.inaxes not in (self.ax, *self._extra_axes):
            return
        if self._legend is not None and self._legend.get_window_extent().contains(event.x, event.y):
            return
        if self._reference_line is None or event.xdata is None or self.on_point_double_click is None:
            return
        x_converted = np.asarray(self._reference_line.get_xdata(orig=False), dtype=float)
        row = int(np.nanargmin(np.abs(x_converted - event.xdata)))
        self.on_point_double_click(row)

    def _on_scroll(self, event) -> None:
        """마우스 커서 위치를 중심으로 휠 확대/축소한다 (위로: 확대, 아래로: 축소).

        부분 확대(드래그 사각형)와 이동/원래대로는 NavigationToolbar2QT 버튼이 담당하고,
        이건 그 사이의 빠른 확대/축소 조작을 보완한다. Y축이 여러 개(twinx)면 서로 스케일이
        달라 event.ydata를 그대로 쓸 수 없으므로, 커서의 화면상 세로 위치를 각 축의
        transAxes 기준 비율(0~1)로 바꿔 모든 축에 동일한 비율로 확대/축소를 적용한다.
        twinx 축들은 화면상 같은 위치를 공유하므로 이 비율은 축마다 동일하다.
        """
        axes = [self.ax, *self._extra_axes]
        if event.inaxes not in axes or event.xdata is None:
            return
        zoom_factor = 0.85 if event.button == "up" else 1 / 0.85

        xlim = self.ax.get_xlim()
        x = event.xdata
        self.ax.set_xlim(x - (x - xlim[0]) * zoom_factor, x + (xlim[1] - x) * zoom_factor)

        _, frac_y = event.inaxes.transAxes.inverted().transform((event.x, event.y))
        for ax in axes:
            ylim = ax.get_ylim()
            y_at_frac = ylim[0] + frac_y * (ylim[1] - ylim[0])
            new_height = (ylim[1] - ylim[0]) * zoom_factor
            new_bottom = y_at_frac - frac_y * new_height
            ax.set_ylim(new_bottom, new_bottom + new_height)
        self.draw_idle()

    def _rebuild_legend(self, all_handles: list, all_labels: list, prev_loc=None) -> None:
        """handles/labels로 범례를 (다시) 만든다. `self._legend`을 갱신해둔다.

        loc="best"는 겹침을 피하려고 모든 데이터 포인트와 위치를 비교하기 때문에
        데이터가 많으면 그 자체로 몇 초~수십 초가 걸린다. 고정 위치로 그 비용을 없앤다.

        self.ax가 아니라 self.figure에 범례를 붙인다: axes에 붙이면 matplotlib은 클릭이
        일어난 axes(event.inaxes)가 범례를 가진 axes와 같을 때만 드래그용 pick 이벤트를
        전달하는데, twinx()로 만든 두 번째 이후 Y축은 self.ax와 완전히 겹친 채 위에 쌓이고
        zorder도 같아서 "나중에 추가된 축"이 topmost로 판정된다. 그 결과 Y축이 2개 이상이면
        event.inaxes가 항상 twin 축이 되어 self.ax에 붙은 범례는 pick 이벤트를 못 받아
        드래그가 전혀 안 먹는다(축이 1개일 때만 우연히 동작). figure에 붙이면 이 axes 매칭
        조건 자체가 없어서 축 개수와 상관없이 항상 드래그된다.
        """
        if self._legend is not None:
            self._legend.remove()
            self._legend = None
        if not all_handles:
            return
        legend = self.figure.legend(all_handles, all_labels, loc="upper right")
        # 범례가 그래프 데이터를 가릴 때 사용자가 마우스로 직접 끌어서 옮길 수 있게 한다.
        legend.set_draggable(True)
        # DAQsystem(pyqtgraph addLegend())의 흰 배경+옅은 테두리 범례 상자와 톤을 맞춘다.
        frame = legend.get_frame()
        frame.set_facecolor("white")
        frame.set_edgecolor(_GRID_COLOR)
        frame.set_alpha(0.95)
        if prev_loc is not None:
            legend._loc = prev_loc
        self._legend = legend

    def refresh_legend(self) -> None:
        """지금 그려진 라인들의 handle/label로 범례를 다시 그린다(드래그 위치는 유지).

        matplotlib 범례는 handle을 그대로 참조하지 않고 생성 시점의 색/스타일로 복사본을
        만들어 스스로 그리므로(HandlerLine2D), 이후 원본 라인의 색을 바꿔도 범례 아이콘은
        자동으로 안 바뀐다. Customize(Figure options)에서 커브 색을 바꾼 뒤
        `figure_options.figure_edit`의 `on_apply` 콜백으로 이 메서드를 호출해 범례를
        최신 색으로 다시 그린다.
        """
        all_handles: list = []
        all_labels: list = []
        for ax in (self.ax, *self._extra_axes):
            handles, labels = ax.get_legend_handles_labels()
            all_handles += handles
            all_labels += labels
        prev_loc = self._legend._loc if self._legend is not None else None
        self._rebuild_legend(all_handles, all_labels, prev_loc)
        self.draw_idle()

    def _reset_axes(self) -> None:
        """이전에 plot_lines()가 만든 twinx 축들과 범례를 모두 지우고 기본 축 하나만 남긴다.

        범례는 self.ax가 아니라 self.figure에 붙어 있어서(이유는 plot_lines() 참고)
        self.ax.clear()로는 지워지지 않으므로 따로 제거해야 한다.
        """
        for ax in self._extra_axes:
            ax.remove()
        self._extra_axes = []
        self.ax.clear()  # ax.clear()가 highlight_row_range()로 그려둔 axvspan도 함께 지운다.
        if self._legend is not None:
            self._legend.remove()
            self._legend = None
        self._reference_line = None
        self._highlight_span = None

    def plot_lines(self, data: pd.DataFrame, x_column: str, y_columns: list[str]) -> list[str]:
        """x_column 기준으로 y_columns를 선 그래프로 그린다.

        y_columns 각각에 별도의 Y축(twinx)을 하나씩 만들어서(참고: `y축 그래프 샘플.png`) 단위/
        범위가 서로 다른 신호를 한 그래프에서 동시에 봐도 한쪽이 눌려 보이지 않게 한다. 각 축의
        라벨/눈금 색을 해당 선 색과 맞춰서 어떤 축이 어떤 선인지 한눈에 구분되게 한다. 축은
        첫 번째 컬럼은 기본 축(왼쪽)에 그대로 두고, 이후 컬럼부터 오른쪽/왼쪽으로 번갈아 바깥으로
        밀어내며 배치한다.

        숫자형이 아닌 y 컬럼은 건너뛰고, 건너뛴 컬럼명 목록을 반환한다.
        """
        # 이전 범례가 있었다면(=드래그로 옮겨놨을 수 있음) 위치를 기억해뒀다가 새 범례에 그대로
        # 적용한다. _reset_axes()가 매번 범례를 새로 만들기 때문에, 이걸 안 하면 항목을
        # 추가/제거할 때마다 기본 위치("upper right")로 되돌아가 버린다.
        prev_loc = self._legend._loc if self._legend is not None else None

        self._reset_axes()
        skipped: list[str] = []

        x_raw = data[x_column]
        if pd.api.types.is_numeric_dtype(x_raw) or pd.api.types.is_datetime64_any_dtype(x_raw):
            x_values = x_raw
        else:
            # X축이 문자열(예: "24-01-29 Time 07:16:33.71" 같은 타임스탬프 텍스트)이면
            # matplotlib이 이를 범주형 축으로 취급해 값마다 개별 변환을 거치는데, 행이
            # 수십만~수백만 개면 이 변환 자체가 수 분~수십 분씩 걸려 "결합하기"를 누른 뒤
            # 그래프가 무한 로딩하는 것처럼 보인다. 위치 인덱스를 실제 X값으로 쓰고, 눈금에
            # 보이는 라벨만 원래 문자열로 표시해 화면에 보이는 몇 개만 변환하도록 우회한다.
            labels = x_raw.astype(str).to_numpy()
            x_values = range(len(labels))
            self.ax.xaxis.set_major_formatter(
                FuncFormatter(lambda pos, _: labels[int(pos)] if 0 <= int(pos) < len(labels) else "")
            )

        use_markers = len(data) <= _MARKER_ROW_THRESHOLD
        color_cycle = _CURVE_PALETTE

        plotted = 0  # 건너뛴 컬럼은 축을 만들지 않으므로 y_columns의 인덱스가 아니라 별도로 센다.
        left_extra = 0
        right_extra = 0
        all_handles = []
        all_labels = []
        for y_column in y_columns:
            y_series = pd.to_numeric(data[y_column], errors="coerce")
            if y_series.notna().sum() == 0:
                skipped.append(y_column)
                continue

            color = color_cycle[plotted % len(color_cycle)]
            if plotted == 0:
                ax = self.ax
            else:
                ax = self.ax.twinx()
                self._extra_axes.append(ax)
                ax.patch.set_visible(False)
                if plotted % 2 == 1:
                    right_extra += 1
                    ax.spines["right"].set_position(("outward", _OUTWARD_STEP_PT * (right_extra - 1)))
                else:
                    left_extra += 1
                    ax.yaxis.set_label_position("left")
                    ax.yaxis.set_ticks_position("left")
                    ax.spines["left"].set_visible(True)
                    ax.spines["right"].set_visible(False)
                    ax.spines["left"].set_position(("outward", _OUTWARD_STEP_PT * left_extra))

            if use_markers:
                (line,) = ax.plot(x_values, y_series, color=color, marker="o", markersize=3, label=y_column)
            else:
                (line,) = ax.plot(x_values, y_series, color=color, label=y_column)
            if plotted == 0:
                self._reference_line = line
            ax.set_ylabel(y_column, color=color)
            ax.tick_params(axis="y", colors=color)
            handles, line_labels = ax.get_legend_handles_labels()
            all_handles += handles
            all_labels += line_labels
            plotted += 1

        self._rebuild_legend(all_handles, all_labels, prev_loc)
        self.ax.set_xlabel(x_column)
        self.ax.tick_params(axis="x", rotation=45)
        # DAQsystem 그래프(pyqtgraph showGrid(alpha=0.3))와 같은 옅은 격자 톤.
        # zorder=0으로 항상 데이터 선 아래에 깔리도록 고정한다.
        self.ax.grid(True, color=_GRID_COLOR, alpha=_GRID_ALPHA, linewidth=0.6, zorder=0)
        self.ax.set_axisbelow(True)

        # constrained_layout/tight_layout는 twinx로 바깥에 쌓인(outward-offset) 축들의 자리를
        # 안정적으로 계산하지 못해서(축이 여러 개일 때 라벨이 엉뚱한 자리로 튀는 현상을 실제로
        # 확인함), 현재 Figure 크기(인치)를 기준으로 각 축이 필요로 하는 여백을 직접 계산한다.
        # OUTWARD_STEP_PT만큼 바깥으로 밀어낸 축마다 그 간격(포인트->인치 변환) + 축 자체의
        # 눈금/라벨 텍스트가 차지할 여백을 더한다.
        fig_width_in, _ = self.figure.get_size_inches()
        base_axis_in = 0.55  # 안쪽(호스트/기본 위치) 축 하나의 눈금+라벨 폭
        outer_label_in = 0.5  # 가장 바깥 축의 눈금+라벨이 추가로 필요로 하는 폭
        step_in = _OUTWARD_STEP_PT / 72

        left_in = base_axis_in + (left_extra * step_in + outer_label_in if left_extra else 0)
        right_in = base_axis_in + (right_extra * step_in + outer_label_in if right_extra else 0)
        left_margin = left_in / fig_width_in
        right_margin = 1 - right_in / fig_width_in
        if right_margin <= left_margin:
            right_margin = left_margin + 0.05
        self.figure.subplots_adjust(left=left_margin, right=right_margin, bottom=0.22, top=0.92)
        self.draw()
        return skipped

    def highlight_row_range(self, row_start: int, row_end: int) -> None:
        """[row_start, row_end) 구간에 배경색을 칠해 그래프에서 어느 파일의 구간인지 표시한다.

        `_reference_line`이 들고 있는, 실제로 그려질 때 이미 변환을 거친 x좌표
        (`get_xdata(orig=False)`)를 그대로 재사용한다. `_on_point_double_click`과 같은
        이유로 이렇게 해야 X축이 날짜/문자열이라 위치 인덱스로 대체된 경우에도(참고:
        `plot_lines`) 항상 올바른 화면 위치를 가리킨다.
        """
        self._clear_highlight()
        if self._reference_line is None or row_start >= row_end:
            return
        x_converted = np.asarray(self._reference_line.get_xdata(orig=False), dtype=float)
        if row_start >= len(x_converted):
            return
        row_end = min(row_end, len(x_converted))
        x_start = x_converted[row_start]
        x_end = x_converted[row_end - 1]
        self._highlight_span = self.ax.axvspan(x_start, x_end, color="#ffca28", alpha=0.25, zorder=0)
        self.draw_idle()

    def clear_highlight(self) -> None:
        """구간 표시를 지운다. 표시된 게 없으면 아무 것도 하지 않는다."""
        if self._highlight_span is None:
            return
        self._clear_highlight()
        self.draw_idle()

    def _clear_highlight(self) -> None:
        if self._highlight_span is not None:
            self._highlight_span.remove()
            self._highlight_span = None

    def clear(self) -> None:
        self._reset_axes()
        self.draw()
