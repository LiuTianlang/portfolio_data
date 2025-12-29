from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from aggregation import AGGREGATIONS, build_chart_data


def _option_index(options: list[str], value: str) -> int:
    return options.index(value) if value in options else 0


def default_chart_config(columns: list[str], numeric_columns: list[str]) -> dict:
    return {
        "chart_type": "Line",
        "x_axis": columns[0],
        "y_axis": numeric_columns[0],
        "aggregation": "None (raw rows)",
        "color_dimension": "(none)",
        "line_symbol": "(none)",
        "line_dash": "(none)",
        "bar_pattern": "(none)",
        "bar_facet": "(none)",
        "layout_height": 480,
    }


def _build_chart(chart_data: pd.DataFrame, config: dict) -> None:
    chart_type = config["chart_type"]
    x_axis = config["x_axis"]
    y_axis = config["y_axis"]
    aggregation = config["aggregation"]
    color_dimension = config["color_dimension"]
    line_symbol = config["line_symbol"]
    line_dash = config["line_dash"]
    bar_pattern = config["bar_pattern"]
    bar_facet = config["bar_facet"]

    if chart_type == "Line":
        fig = px.line(
            chart_data,
            x=x_axis,
            y=y_axis,
            color=None if color_dimension == "(none)" else color_dimension,
            symbol=None if line_symbol == "(none)" else line_symbol,
            line_dash=None if line_dash == "(none)" else line_dash,
            markers=True,
        )
    elif chart_type == "Bar":
        bar_mode = "stack" if color_dimension != "(none)" else "group"
        fig = px.bar(
            chart_data,
            x=x_axis,
            y=y_axis,
            color=None if color_dimension == "(none)" else color_dimension,
            pattern_shape=None if bar_pattern == "(none)" else bar_pattern,
            facet_col=None if bar_facet == "(none)" else bar_facet,
            barmode=bar_mode,
        )
    elif chart_type == "Pie":
        fig = px.pie(
            chart_data,
            names=x_axis,
            values=y_axis,
            color=None if color_dimension == "(none)" else color_dimension,
        )
    else:
        fig = px.density_heatmap(
            chart_data,
            x=x_axis,
            y=y_axis,
            z=y_axis if aggregation != "None (raw rows)" else None,
            histfunc=AGGREGATIONS.get(aggregation) or "count",
            color_continuous_scale="Viridis",
        )

    fig.update_layout(
        height=int(config["layout_height"]),
        margin=dict(l=20, r=20, t=40, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_chart_builder(
    filtered_data: pd.DataFrame,
    column_options: list[str],
    numeric_columns: list[str],
) -> None:
    st.subheader("2) Build charts")

    if "charts" not in st.session_state:
        st.session_state.charts = [default_chart_config(column_options, numeric_columns)]

    add_col, _ = st.columns([1, 3])
    with add_col:
        if st.button("Add chart"):
            st.session_state.charts.append(default_chart_config(column_options, numeric_columns))

    chart_tabs = st.tabs([f"Chart {index + 1}" for index in range(len(st.session_state.charts))])

    for index, chart_tab in enumerate(chart_tabs):
        config = st.session_state.charts[index]
        defaults = default_chart_config(column_options, numeric_columns)
        for key, value in defaults.items():
            config.setdefault(key, value)

        with chart_tab:
            st.markdown(f"#### Chart {index + 1}")
            config_col, chart_col = st.columns([1, 2])

            with config_col:
                chart_type = st.selectbox(
                    "Chart type",
                    ["Line", "Bar", "Pie", "Heatmap"],
                    index=_option_index(["Line", "Bar", "Pie", "Heatmap"], config["chart_type"]),
                    key=f"chart_type_{index}",
                )
                x_axis = st.selectbox(
                    "X-axis",
                    options=filtered_data.columns,
                    index=_option_index(list(filtered_data.columns), config["x_axis"]),
                    key=f"x_axis_{index}",
                )
                y_axis = st.selectbox(
                    "Y-axis",
                    options=numeric_columns,
                    index=_option_index(numeric_columns, config["y_axis"]),
                    key=f"y_axis_{index}",
                )
                aggregation = st.selectbox(
                    "Aggregation",
                    options=list(AGGREGATIONS.keys()),
                    index=_option_index(list(AGGREGATIONS.keys()), config["aggregation"]),
                    key=f"aggregation_{index}",
                )
                dimension_options = ["(none)"] + column_options
                color_dimension = st.selectbox(
                    "Color / stack by (optional)",
                    options=dimension_options,
                    index=_option_index(dimension_options, config["color_dimension"]),
                    key=f"color_dimension_{index}",
                )
                if chart_type == "Line":
                    line_symbol = st.selectbox(
                        "Dot shape (optional)",
                        options=dimension_options,
                        index=_option_index(dimension_options, config["line_symbol"]),
                        key=f"line_symbol_{index}",
                    )
                    line_dash = st.selectbox(
                        "Line type (optional)",
                        options=dimension_options,
                        index=_option_index(dimension_options, config["line_dash"]),
                        key=f"line_dash_{index}",
                    )
                    bar_pattern = config["bar_pattern"]
                    bar_facet = config["bar_facet"]
                elif chart_type == "Bar":
                    line_symbol = config["line_symbol"]
                    line_dash = config["line_dash"]
                    bar_pattern = st.selectbox(
                        "Bar pattern (optional)",
                        options=dimension_options,
                        index=_option_index(dimension_options, config["bar_pattern"]),
                        key=f"bar_pattern_{index}",
                    )
                    bar_facet = st.selectbox(
                        "Facet column (optional)",
                        options=dimension_options,
                        index=_option_index(dimension_options, config["bar_facet"]),
                        key=f"bar_facet_{index}",
                    )
                else:
                    line_symbol = config["line_symbol"]
                    line_dash = config["line_dash"]
                    bar_pattern = config["bar_pattern"]
                    bar_facet = config["bar_facet"]
                layout_height = st.slider(
                    "Chart height",
                    min_value=320,
                    max_value=800,
                    value=int(config["layout_height"]),
                    step=20,
                    key=f"layout_height_{index}",
                )

            config.update(
                {
                    "chart_type": chart_type,
                    "x_axis": x_axis,
                    "y_axis": y_axis,
                    "aggregation": aggregation,
                    "color_dimension": color_dimension,
                    "line_symbol": line_symbol,
                    "line_dash": line_dash,
                    "bar_pattern": bar_pattern,
                    "bar_facet": bar_facet,
                    "layout_height": layout_height,
                }
            )

            chart_data = build_chart_data(filtered_data, config)

            with chart_col:
                _build_chart(chart_data, config)
