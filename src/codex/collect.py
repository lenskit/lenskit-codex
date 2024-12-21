import json
from pathlib import Path
from typing import IO

import zstandard
from pydantic import JsonValue


class NDJSONCollector:
    """
    Collect objects into an NDJSON file, with optional zstd compression.
    """

    path: Path
    fields: dict[str, JsonValue]
    output: IO[str]

    def __init__(self, path: Path, fields: dict[str, JsonValue] | None = None, **options):
        self.path = path
        self.fields = fields or {}

        path.parent.mkdir(exist_ok=True, parents=True)
        if path.suffix == ".zst":
            self.output = zstandard.open(path, "wt", zstandard.ZstdCompressor(**options))
        else:
            self.output = path.open("wt")

    def write_object(self, data: dict[str, JsonValue]):
        """
        Write the specified line to the output file.
        """
        print(json.dumps(self.fields | data), file=self.output)

    def close(self):
        self.output.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
