# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Windows desktop app (PySide6) that loads multiple CSV/Excel files, concatenates them into one table (row-wise), and plots selected columns as a line chart. Files must share the same column structure to be combined — see "Combine semantics" below.

## Commands

Install dependencies (project uses a `.venv` virtualenv, not global site-packages):
```bash
python -m venv .venv
./.venv/Scripts/pip install -r requirements.txt
```

Run the app:
```bash
./.venv/Scripts/python main.py
```

Build a standalone Windows exe (PyInstaller, one-file, no console window):
```bash
./.venv/Scripts/pip install pyinstaller
./.venv/Scripts/pyinstaller --noconfirm --onefile --windowed --name DataViewer main.py
```
Output goes to `dist/DataViewer.exe`. `build/`, `dist/`, and `*.spec` are gitignored — the exe is a local build artifact, not committed.

There is no test suite and no linter configured in this repo. The most useful manual check for data logic is exercising `app/data_loader.py`'s `load_files`/`combine_frames` directly with sample files (see `sample_data/` for two matching-schema `.xlsx` fixtures).

## Architecture

Four modules under `app/`, wired together by `main_window.MainWindow`:

- **`data_loader.py`** — pure pandas logic, no Qt dependency. `load_files()` reads each path via `pd.read_csv`/`pd.read_excel` based on extension, collecting per-file errors instead of raising. `combine_frames()` concatenates row-wise but only across files whose column tuples exactly match the first file's; mismatched files are dropped from the result and their paths returned separately so the UI can warn about them. There is no column-remapping or alignment — schema must match exactly.
- **`table_model.py`** — `PandasTableModel(QAbstractTableModel)` is a thin read-only adapter exposing a DataFrame to `QTableView`.
- **`plot_canvas.py`** — `PlotCanvas(FigureCanvasQTAgg)` embeds a matplotlib figure in Qt. `plot_lines()` coerces each requested Y column with `pd.to_numeric(errors="coerce")`; columns that end up all-NaN are skipped and returned to the caller (so the UI can report which ones were dropped) instead of raising. Module-level `plt.rcParams["font.family"] = "Malgun Gothic"` is set so Hangul labels don't render as missing-glyph boxes — don't remove this without another CJK-capable font in place.
- **`main_window.py`** — owns all UI state and orchestration. Key non-obvious behavior:
  - X-axis combo and Y-axis checklist are mutually exclusive: whichever column is selected as X is excluded from the Y list (`_refresh_y_list`), and switching X rebuilds the Y list.
  - Y-axis check state persists across rebuilds in `self._y_checked` (dict keyed by column name), defaulting new/unseen columns to checked. This is what makes "all columns shown after combine" and "toggle a column in/out without losing other selections" work.
  - The plot updates reactively (`_update_plot`) on every X change or Y checkbox toggle — there's no separate "confirm selection" step; the "그래프 새로고침" button is just a manual re-trigger of the same method.
  - Drag-and-drop requires overriding **both** `dragEnterEvent` and `dragMoveEvent` (both must call `acceptProposedAction()`). Qt's default `dragMoveEvent` ignores the event, which silently blocks `dropEvent` from firing even when `dragEnterEvent` accepted — this is a real gotcha, not defensive boilerplate.

`main.py` is a minimal entry point (`QApplication` + `MainWindow().show()`).

Everything currently runs synchronously on the Qt main thread — loading/combining large files will freeze the UI. If large-file handling becomes a requirement, that's the place to introduce a worker thread.
