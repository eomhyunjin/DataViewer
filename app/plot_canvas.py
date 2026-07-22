"""matplotlib 선 그래프를 Qt 위젯에 임베드."""
from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

# Windows 기본 한글 폰트로 설정해 축/범례의 한글이 깨지지 않도록 한다.
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

# 표식(marker)은 점이 이 개수 이하로 적을 때만 그린다. 대용량 데이터(수십만~수백만 행)에서
# 점마다 마커를 찍으면 픽셀이 뭉개져 보이지도 않을뿐더러 렌더링 비용만 늘어난다.
_MARKER_ROW_THRESHOLD = 500


class PlotCanvas(FigureCanvasQTAgg):
    def __init__(self):
        self.figure = Figure(figsize=(5, 4), tight_layout=True)
        super().__init__(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.mpl_connect("scroll_event", self._on_scroll)

    def _on_scroll(self, event) -> None:
        """마우스 커서 위치를 중심으로 휠 확대/축소한다 (위로: 확대, 아래로: 축소).

        부분 확대(드래그 사각형)와 이동/원래대로는 NavigationToolbar2QT 버튼이 담당하고,
        이건 그 사이의 빠른 확대/축소 조작을 보완한다.
        """
        if event.inaxes != self.ax or event.xdata is None or event.ydata is None:
            return
        zoom_factor = 0.85 if event.button == "up" else 1 / 0.85
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        x, y = event.xdata, event.ydata
        self.ax.set_xlim(x - (x - xlim[0]) * zoom_factor, x + (xlim[1] - x) * zoom_factor)
        self.ax.set_ylim(y - (y - ylim[0]) * zoom_factor, y + (ylim[1] - y) * zoom_factor)
        self.draw_idle()

    def plot_lines(self, data: pd.DataFrame, x_column: str, y_columns: list[str]) -> list[str]:
        """x_column 기준으로 y_columns를 선 그래프로 그린다.

        숫자형이 아닌 y 컬럼은 건너뛰고, 건너뛴 컬럼명 목록을 반환한다.
        """
        self.ax.clear()
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
        for y_column in y_columns:
            y_series = pd.to_numeric(data[y_column], errors="coerce")
            if y_series.notna().sum() == 0:
                skipped.append(y_column)
                continue
            if use_markers:
                self.ax.plot(x_values, y_series, marker="o", markersize=3, label=y_column)
            else:
                self.ax.plot(x_values, y_series, label=y_column)

        if y_columns and len(y_columns) > len(skipped):
            # loc="best"는 겹침을 피하려고 모든 데이터 포인트와 위치를 비교하기 때문에
            # 데이터가 많으면 그 자체로 몇 초~수십 초가 걸린다. 고정 위치로 그 비용을 없앤다.
            self.ax.legend(loc="upper right")
        self.ax.set_xlabel(x_column)
        self.ax.tick_params(axis="x", rotation=45)
        self.draw()
        return skipped

    def clear(self) -> None:
        self.ax.clear()
        self.draw()
