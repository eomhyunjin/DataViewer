"""CSV/Excel/MDF 파일을 읽고 결합하는 로직."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from asammdf import MDF, Signal

MDF_SUFFIXES = {".mf4", ".mdf"}
SUPPORTED_SUFFIXES = {".csv", ".xlsx", ".xls"} | MDF_SUFFIXES


def _columns_sidecar_path(mdf_path: Path) -> Path:
    return mdf_path.with_name(mdf_path.name + ".columns.json")


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
    if suffix in MDF_SUFFIXES:
        return read_mdf(path)
    raise ValueError(f"지원하지 않는 파일 형식입니다: {path.suffix}")


def read_mdf(path: Path) -> pd.DataFrame:
    """MDF(.mf4/.mdf) 파일을 DataFrame으로 읽는다.

    `MDF.to_dataframe()`은 문자열 채널을 인코딩한 바이트 그대로 돌려주고 채널 순서도
    원본 DataFrame의 컬럼 순서와 다르게(내부 채널 그룹 구성 순서로) 재배열하므로, 여기서
    바이트를 문자열로 디코딩하고 `convert_to_mdf`가 함께 저장해 둔 사이드카 JSON으로
    원래 컬럼 순서를 복원한다. 사이드카가 없거나(예: mdf 파일만 따로 옮겨진 경우) 컬럼
    구성이 달라졌으면 `to_dataframe()`이 반환한 순서를 그대로 쓴다.
    """
    with MDF(path) as mdf:
        df = mdf.to_dataframe().reset_index(drop=True)
    for column in df.columns:
        if df[column].dtype == object:
            df[column] = df[column].apply(lambda v: v.decode("utf-8") if isinstance(v, bytes) else v)

    sidecar = _columns_sidecar_path(path)
    if sidecar.exists():
        try:
            order = json.loads(sidecar.read_text(encoding="utf-8"))["columns"]
        except (json.JSONDecodeError, KeyError, OSError):
            order = None
        if order:
            # asammdf가 채널 이름의 앞뒤 공백을 저장/로딩 과정에서 지워버리는 경우가 있어서
            # (예: "Warn Current " -> "Warn Current"), 공백을 뺀 이름으로 대응시켜 순서를
            # 복원하고 원래 이름(공백 포함)으로 되돌린다. 채널 개수가 다르거나 공백 제거 후
            # 이름이 겹치면(충돌) 안전하게 원래 순서를 포기하고 to_dataframe() 결과를 그대로 쓴다.
            stripped_to_actual = {str(c).strip(): c for c in df.columns}
            if len(stripped_to_actual) == len(df.columns) and all(
                o.strip() in stripped_to_actual for o in order
            ):
                df = df[[stripped_to_actual[o.strip()] for o in order]]
                df.columns = order
    return df


def convert_to_mdf(path: Path, df: pd.DataFrame) -> Path:
    """CSV/Excel에서 읽은 DataFrame을 같은 폴더에 MDF(.mf4) 파일로 저장한다.

    asammdf(설치된 8.8.22 기준)는 pandas 3.0의 새 문자열 dtype과 궁합이 안 맞아 DataFrame을
    통째로 넘기는 표준 경로가 에러를 내므로, 컬럼마다 직접 `Signal`을 만든다. 문자열 컬럼은
    `encoding` 인자를 반드시 지정해야 한다(빠뜨리면 "wrong encoding" 에러). `MDF.save()`는
    지정한 확장자를 무시하고 항상 `.mf4`로 저장하므로 대상 경로를 미리 `.mf4`로 맞춰둔다.
    컬럼 순서는 MDF에 남지 않아서 `read_mdf`가 복원할 수 있도록 사이드카 JSON에 별도 저장한다.
    """
    timestamps = np.arange(len(df), dtype=np.float64)
    signals = []
    for column in df.columns:
        series = df[column]
        name = str(column)
        if pd.api.types.is_numeric_dtype(series):
            signals.append(Signal(samples=series.to_numpy(), timestamps=timestamps, name=name))
        else:
            # asammdf는 object dtype(가변 길이 bytes) 배열을 거부하므로 고정폭 numpy 'S' 배열이 필요하다.
            # numpy가 str -> 'S'를 직접 변환하면 ASCII로 인코딩해 한글 등이 깨지므로, 먼저 UTF-8
            # bytes로 인코딩한 뒤 그 bytes 값 그대로 고정폭 배열에 담는다.
            encoded = series.astype(str).map(lambda s: s.encode("utf-8"))
            samples = np.array(encoded.tolist(), dtype="S")
            signals.append(Signal(samples=samples, timestamps=timestamps, name=name, encoding="utf-8"))

    target = path.with_suffix(".mf4")
    with MDF() as mdf:
        mdf.append(signals)
        mdf.save(target, overwrite=True)

    _columns_sidecar_path(target).write_text(
        json.dumps({"columns": [str(c) for c in df.columns]}, ensure_ascii=False),
        encoding="utf-8",
    )
    return target


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


def numeric_columns(df: pd.DataFrame) -> list[str]:
    """숫자로 변환 가능한 값이 하나라도 있는 컬럼만 원래 순서대로 반환한다(Y축 후보용).

    Status, Save Period처럼 항상 텍스트뿐인 컬럼은 그래프에 그릴 수 없으므로 아예
    후보에서 제외한다.
    """
    return [c for c in df.columns if pd.to_numeric(df[c], errors="coerce").notna().any()]
