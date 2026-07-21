"""pandas DataFrame을 QTableView에 표시하기 위한 모델."""
from __future__ import annotations

import pandas as pd
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt


class PandasTableModel(QAbstractTableModel):
    def __init__(self, data: pd.DataFrame | None = None):
        super().__init__()
        self._data = data if data is not None else pd.DataFrame()

    def set_dataframe(self, data: pd.DataFrame) -> None:
        self.beginResetModel()
        self._data = data
        self.endResetModel()

    def dataframe(self) -> pd.DataFrame:
        return self._data

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._data.index)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._data.columns)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        value = self._data.iat[index.row(), index.column()]
        return "" if pd.isna(value) else str(value)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return str(self._data.columns[section])
        return str(section + 1)
