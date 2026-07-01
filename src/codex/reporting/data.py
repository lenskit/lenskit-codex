import pandas as pd

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
