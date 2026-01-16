from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class FilterConfig:
    title_column: str | None
    title_values: list[str] | None
    time_column: str | None
    start_date: str | None
    end_date: str | None


class DataFilter:
    """Apply user-specified filters to a dataframe."""

    @staticmethod
    def apply(data: pd.DataFrame, config: FilterConfig) -> pd.DataFrame:
        filtered = data.copy()

        if config.title_column and config.title_values:
            filtered = filtered[
                filtered[config.title_column].astype(str).isin(config.title_values)
            ]

        if config.time_column and config.start_date and config.end_date:
            converted = pd.to_datetime(filtered[config.time_column], errors="coerce")
            filtered = filtered.assign(**{config.time_column: converted})
            start = pd.to_datetime(config.start_date)
            end = pd.to_datetime(config.end_date)
            filtered = filtered[filtered[config.time_column].between(start, end)]

        return filtered

    @staticmethod
    def unique_values(series: pd.Series) -> list[str]:
        return sorted({str(value) for value in series.dropna().unique()})

    @staticmethod
    def datetime_bounds(series: pd.Series) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
        converted = pd.to_datetime(series, errors="coerce")
        min_time = converted.min()
        max_time = converted.max()
        if pd.isna(min_time) or pd.isna(max_time):
            return None, None
        return min_time, max_time
