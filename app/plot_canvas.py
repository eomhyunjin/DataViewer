"""matplotlib 선 그래프를 Qt 위젯에 임베드."""
from __future__ import annotations

import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class PlotCanvas(FigureCanvasQTAgg):
    def __init__(self):
        self.figure = Figure(figsize=(5, 4), tight_layout=True)
        super().__init__(self.figure)
        self.ax = self.figure.add_subplot(111)

    def plot_lines(self, data: pd.DataFrame, x_column: str, y_columns: list[str]) -> list[str]:
        """x_column 기준으로 y_columns를 선 그래프로 그린다.

        숫자형이 아닌 y 컬럼은 건너뛰고, 건너뛴 컬럼명 목록을 반환한다.
        """
        self.ax.clear()
        skipped: list[str] = []

        x_values = data[x_column]
        for y_column in y_columns:
            y_series = pd.to_numeric(data[y_column], errors="coerce")
            if y_series.notna().sum() == 0:
                skipped.append(y_column)
                continue
            self.ax.plot(x_values, y_series, marker="o", markersize=3, label=y_column)

        if y_columns and len(y_columns) > len(skipped):
            self.ax.legend()
        self.ax.set_xlabel(x_column)
        self.ax.tick_params(axis="x", rotation=45)
        self.draw()
        return skipped
