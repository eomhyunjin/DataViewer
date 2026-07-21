"""CSV/Excel 파일을 읽고 결합하는 로직."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

SUPPORTED_SUFFIXES = {".csv", ".xlsx", ".xls"}


@dataclass
class LoadResult:
    frames: dict[str, pd.DataFrame] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)


def is_supported_file(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_SUFFIXES


def read_file(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(path)
    raise ValueError(f"지원하지 않는 파일 형식입니다: {path.suffix}")


def load_files(paths: list[Path]) -> LoadResult:
    result = LoadResult()
    for path in paths:
        try:
            if not is_supported_file(path):
                raise ValueError(f"지원하지 않는 파일 형식입니다: {path.suffix}")
            result.frames[str(path)] = read_file(path)
        except Exception as exc:  # noqa: BLE001 - 파일별 오류를 모아서 보여줘야 함
            result.errors[str(path)] = str(exc)
    return result


@dataclass
class CombineResult:
    data: pd.DataFrame
    mismatched_files: list[str]


def combine_frames(frames: dict[str, pd.DataFrame]) -> CombineResult:
    """열 구조가 같다고 가정하고 행 단위로 이어붙인다.

    열 구조가 다른 파일은 결합에서 제외하고 mismatched_files로 알려준다.
    """
    if not frames:
        return CombineResult(data=pd.DataFrame(), mismatched_files=[])

    items = list(frames.items())
    base_path, base_df = items[0]
    base_columns = tuple(base_df.columns)

    matching = [base_df]
    mismatched = []
    for path, df in items[1:]:
        if tuple(df.columns) == base_columns:
            matching.append(df)
        else:
            mismatched.append(path)

    combined = pd.concat(matching, ignore_index=True)
    return CombineResult(data=combined, mismatched_files=mismatched)
