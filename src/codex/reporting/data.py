from pathlib import Path

import pandas as pd

from codex.layout import DataSetInfo

try:
    _json = Path("dataset.json").read_text()
    DATA_INFO = DataSetInfo.model_validate_json(_json)
except FileNotFoundError:
    DATA_INFO = None


def filter_part(data: pd.DataFrame, part: str):
    assert DATA_INFO is not None

    if "random" in DATA_INFO.splits:
        if part == "test":
            mask = data["part"] != 0
        elif part == "valid":
            mask = data["part"] == 0
        else:
            raise ValueError(f"invalid part {part}")
    else:
        mask = data["part"] == part
    return data[mask]
