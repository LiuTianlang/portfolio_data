from __future__ import annotations

import pandas as pd

AGGREGATIONS = {
    "None (raw rows)": None,
    "Count": "count",
    "Sum": "sum",
    "Mean": "mean",
    "Min": "min",
    "Max": "max",
}


def build_chart_data(filtered_data: pd.DataFrame, config: dict) -> pd.DataFrame:
    aggregation = config["aggregation"]
    if aggregation == "None (raw rows)":
        return filtered_data.copy()

    agg_func = AGGREGATIONS[aggregation]
    groupers = [config["x_axis"]]

    if config["color_dimension"] != "(none)":
        groupers.append(config["color_dimension"])

    if config["chart_type"] == "Line":
        if config["line_symbol"] != "(none)":
            groupers.append(config["line_symbol"])
        if config["line_dash"] != "(none)":
            groupers.append(config["line_dash"])

    if config["chart_type"] == "Bar":
        if config["bar_pattern"] != "(none)":
            groupers.append(config["bar_pattern"])
        if config["bar_facet"] != "(none)":
            groupers.append(config["bar_facet"])

    return (
        filtered_data.groupby(groupers, dropna=False, as_index=False)[config["y_axis"]]
        .agg(agg_func)
    )
