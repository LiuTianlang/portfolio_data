from __future__ import annotations

from typing import Iterable

import pandas as pd
import streamlit as st


def _coerce_datetime(series: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    return pd.to_datetime(series, errors="coerce")


def _safe_unique(values: Iterable) -> list:
    return sorted({value for value in values if pd.notna(value)})


def render_filters(data: pd.DataFrame) -> pd.DataFrame:
    st.subheader("1) Filter your data")

    column_options = list(data.columns)
    filter_col, time_col = st.columns(2)

    with filter_col:
        title_column = st.selectbox("Title filter column", options=["(none)"] + column_options)

    with time_col:
        time_column = st.selectbox("Time filter column", options=["(none)"] + column_options)

    filtered_data = data.copy()

    if title_column != "(none)":
        title_values = _safe_unique(filtered_data[title_column])
        selected_titles = st.multiselect(
            "Choose titles",
            options=title_values,
            default=title_values[: min(len(title_values), 10)],
        )
        if selected_titles:
            filtered_data = filtered_data[filtered_data[title_column].isin(selected_titles)]

    if time_column != "(none)":
        converted = _coerce_datetime(filtered_data[time_column])
        filtered_data = filtered_data.assign(**{time_column: converted})
        min_time = converted.min()
        max_time = converted.max()

        if pd.isna(min_time) or pd.isna(max_time):
            st.warning("Selected time column could not be parsed as datetime.")
        else:
            start, end = st.slider(
                "Time range",
                min_value=min_time.to_pydatetime(),
                max_value=max_time.to_pydatetime(),
                value=(min_time.to_pydatetime(), max_time.to_pydatetime()),
                format="YYYY-MM-DD HH:mm",
            )
            filtered_data = filtered_data[
                filtered_data[time_column].between(pd.Timestamp(start), pd.Timestamp(end))
            ]

    return filtered_data
