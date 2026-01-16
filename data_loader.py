from __future__ import annotations

import base64
import io
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class CsvPayload:
    dataframe: pd.DataFrame | None
    error: str | None = None


class CsvDataLoader:
    """Parse CSV uploads from Dash."""

    @staticmethod
    def parse_contents(contents: str, filename: str | None) -> CsvPayload:
        if not contents:
            return CsvPayload(dataframe=None, error="No file contents provided.")

        try:
            _, content_string = contents.split(",", 1)
        except ValueError:
            return CsvPayload(dataframe=None, error="Invalid upload payload.")

        decoded = base64.b64decode(content_string)
        try:
            dataframe = pd.read_csv(io.BytesIO(decoded))
        except Exception as exc:  # noqa: BLE001 - surface file errors to the user
            return CsvPayload(dataframe=None, error=f"Unable to read {filename or 'CSV'}: {exc}")

        return CsvPayload(dataframe=dataframe)
