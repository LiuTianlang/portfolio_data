from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from dash import (
    Dash,
    Input,
    Output,
    State,
    callback_context,
    dash_table,
    dcc,
    html,
    no_update,
)
from dash.dependencies import ALL

from aggregation import build_chart_data
from data_loader import CsvDataLoader
from filters import DataFilter, FilterConfig
from visualization import ChartBuilder


@dataclass(frozen=True)
class ComponentIds:
    upload: str = "csv-upload"
    datasets_store: str = "datasets-store"
    data_store: str = "data-store"
    upload_info: str = "upload-info"
    dataset_selector: str = "dataset-selector"
    delete_dataset: str = "delete-dataset"
    title_column: str = "title-column"
    title_values: str = "title-values"
    time_column: str = "time-column"
    time_range: str = "time-range"
    chart_count: str = "chart-count"
    add_chart: str = "add-chart"
    charts_container: str = "charts-container"
    data_preview: str = "data-preview"


class DashboardApp:
    """Dash app for CSV exploration."""

    def __init__(self) -> None:
        self.ids = ComponentIds()
        self.app = Dash(__name__)
        self.loader = CsvDataLoader()
        self.data_filter = DataFilter()
        self.chart_builder = ChartBuilder()
        self.app.layout = self._build_layout()
        self._register_callbacks()

    def _build_layout(self) -> html.Div:
        return html.Div(
            className="page",
            children=[
                html.H1("CSV Insight Studio"),
                html.P(
                    "Upload a CSV, filter rows, and explore charts with aggregation.",
                    className="hint",
                ),
                html.Div(
                    className="layout",
                    children=[
                        html.Aside(
                            className="sidebar",
                            children=[
                                html.Div(
                                    className="section",
                                    children=[
                                        html.H2("1) Data workspace"),
                                        html.Label("Upload CSV"),
                                        dcc.Upload(
                                            id=self.ids.upload,
                                            children=html.Div(
                                                ["Drag and Drop or ", html.A("Select Files")]
                                            ),
                                            style={
                                                "width": "100%",
                                                "height": "60px",
                                                "lineHeight": "60px",
                                                "textAlign": "center",
                                            },
                                            className="upload-area",
                                            multiple=False,
                                        ),
                                        html.Div(id=self.ids.upload_info, className="hint"),
                                        html.Label("Select dataset"),
                                        dcc.Dropdown(
                                            id=self.ids.dataset_selector,
                                            clearable=False,
                                        ),
                                        html.Button(
                                            "Delete dataset",
                                            id=self.ids.delete_dataset,
                                            className="secondary-button",
                                        ),
                                    ],
                                ),
                                html.Div(
                                    className="section",
                                    children=[
                                        html.H2("2) Global filters"),
                                        html.Div(
                                            className="filters",
                                            children=[
                                                html.Div(
                                                    className="filter",
                                                    children=[
                                                        html.Label("Title filter column"),
                                                        dcc.Dropdown(
                                                            id=self.ids.title_column,
                                                            clearable=True,
                                                        ),
                                                    ],
                                                ),
                                                html.Div(
                                                    className="filter",
                                                    children=[
                                                        html.Label("Choose titles"),
                                                        dcc.Dropdown(
                                                            id=self.ids.title_values,
                                                            multi=True,
                                                        ),
                                                    ],
                                                ),
                                                html.Div(
                                                    className="filter",
                                                    children=[
                                                        html.Label("Time filter column"),
                                                        dcc.Dropdown(
                                                            id=self.ids.time_column,
                                                            clearable=True,
                                                        ),
                                                    ],
                                                ),
                                                html.Div(
                                                    className="filter",
                                                    children=[
                                                        html.Label("Time range"),
                                                        dcc.DatePickerRange(
                                                            id=self.ids.time_range
                                                        ),
                                                    ],
                                                ),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        html.Main(
                            className="main",
                            children=[
                                html.Div(
                                    className="section",
                                    children=[
                                        html.Div(
                                            className="charts-header",
                                            children=[
                                                html.H2("3) Build charts"),
                                                html.Button(
                                                    "Add chart", id=self.ids.add_chart
                                                ),
                                            ],
                                        ),
                                        html.Div(id=self.ids.charts_container),
                                    ],
                                ),
                                html.Div(
                                    className="section",
                                    children=[
                                        html.H2("4) Preview filtered data"),
                                        html.Div(
                                            className="data-preview",
                                            children=[
                                                dash_table.DataTable(
                                                    id=self.ids.data_preview,
                                                    page_size=10,
                                                    style_table={"overflowX": "auto"},
                                                    style_header={
                                                        "backgroundColor": "#f1f5f9",
                                                        "fontWeight": "600",
                                                    },
                                                    style_cell={
                                                        "fontFamily": "Inter, system-ui, sans-serif",
                                                        "fontSize": "14px",
                                                        "padding": "8px",
                                                        "whiteSpace": "normal",
                                                    },
                                                )
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
                dcc.Store(id=self.ids.datasets_store, data={}),
                dcc.Store(id=self.ids.data_store),
                dcc.Store(id=self.ids.chart_count, data=1),
            ],
        )

    @staticmethod
    def _unique_dataset_name(name: str, datasets: dict) -> str:
        if name not in datasets:
            return name
        counter = 1
        base = name.rsplit(".", 1)
        while True:
            suffix = f" ({counter})"
            candidate = (
                f"{base[0]}{suffix}.{base[1]}" if len(base) == 2 else f"{base[0]}{suffix}"
            )
            if candidate not in datasets:
                return candidate
            counter += 1

    def _register_callbacks(self) -> None:
        ids = self.ids

        @self.app.callback(
            Output(ids.datasets_store, "data"),
            Output(ids.dataset_selector, "value"),
            Output(ids.upload_info, "children"),
            Input(ids.upload, "contents"),
            Input(ids.delete_dataset, "n_clicks"),
            State(ids.upload, "filename"),
            State(ids.datasets_store, "data"),
            State(ids.dataset_selector, "value"),
            prevent_initial_call=True,
        )
        def _update_datasets(
            contents: str | None,
            delete_clicks: int | None,
            filename: str | None,
            datasets: dict,
            selected_dataset: str | None,
        ) -> tuple[dict, str | None, str]:
            datasets = datasets or {}
            triggered = callback_context.triggered_id

            if triggered == ids.delete_dataset:
                if selected_dataset and selected_dataset in datasets:
                    datasets.pop(selected_dataset)
                    remaining = list(datasets.keys())
                    return datasets, (remaining[0] if remaining else None), ""
                return datasets, selected_dataset, ""

            if triggered == ids.upload:
                if not contents:
                    return datasets, selected_dataset, ""
                payload = self.loader.parse_contents(contents, filename)
                if payload.error:
                    return datasets, selected_dataset, payload.error
                if payload.dataframe is None or payload.dataframe.empty:
                    return datasets, selected_dataset, "The uploaded CSV has no rows."
                dataset_name = self._unique_dataset_name(
                    filename or "uploaded.csv",
                    datasets,
                )
                datasets[dataset_name] = payload.dataframe.to_json(
                    date_format="iso", orient="split"
                )
                return datasets, dataset_name, ""

            return no_update, no_update, ""

        @self.app.callback(
            Output(ids.dataset_selector, "options"),
            Input(ids.datasets_store, "data"),
        )
        def _update_dataset_options(datasets: dict) -> list[dict]:
            datasets = datasets or {}
            return [{"label": name, "value": name} for name in datasets.keys()]

        @self.app.callback(
            Output(ids.data_store, "data"),
            Input(ids.datasets_store, "data"),
            Input(ids.dataset_selector, "value"),
        )
        def _sync_selected_dataset(datasets: dict, selected_name: str | None):
            if not datasets or not selected_name or selected_name not in datasets:
                return None
            return datasets[selected_name]

        @self.app.callback(
            Output(ids.title_column, "options"),
            Output(ids.title_column, "value"),
            Output(ids.time_column, "options"),
            Output(ids.time_column, "value"),
            Input(ids.data_store, "data"),
        )
        def _update_column_options(data_json: str | None):
            if not data_json:
                return [], None, [], None
            data = pd.read_json(data_json, orient="split")
            options = [{"label": col, "value": col} for col in data.columns]
            return options, None, options, None

        @self.app.callback(
            Output(ids.title_values, "options"),
            Output(ids.title_values, "value"),
            Input(ids.title_column, "value"),
            Input(ids.data_store, "data"),
        )
        def _update_title_values(title_column: str | None, data_json: str | None):
            if not data_json or not title_column:
                return [], []
            data = pd.read_json(data_json, orient="split")
            values = self.data_filter.unique_values(data[title_column])
            return [{"label": v, "value": v} for v in values], values[:10]

        @self.app.callback(
            Output(ids.time_range, "min_date_allowed"),
            Output(ids.time_range, "max_date_allowed"),
            Output(ids.time_range, "start_date"),
            Output(ids.time_range, "end_date"),
            Input(ids.time_column, "value"),
            Input(ids.data_store, "data"),
        )
        def _update_time_range(time_column: str | None, data_json: str | None):
            if not data_json or not time_column:
                return None, None, None, None
            data = pd.read_json(data_json, orient="split")
            min_time, max_time = self.data_filter.datetime_bounds(data[time_column])
            if not min_time or not max_time:
                return None, None, None, None
            return (
                min_time.date(),
                max_time.date(),
                min_time.date(),
                max_time.date(),
            )

        @self.app.callback(
            Output(ids.chart_count, "data"),
            Input(ids.add_chart, "n_clicks"),
            State(ids.chart_count, "data"),
            prevent_initial_call=True,
        )
        def _add_chart(n_clicks: int | None, current_count: int) -> int:
            if not n_clicks:
                return current_count
            return current_count + 1

        @self.app.callback(
            Output(ids.charts_container, "children"),
            Input(ids.chart_count, "data"),
            Input(ids.data_store, "data"),
        )
        def _render_charts(count: int, data_json: str | None):
            if not data_json:
                return html.Div("Upload a CSV to configure charts.")
            data = pd.read_json(data_json, orient="split")
            numeric_columns = [
                col for col in data.columns if pd.api.types.is_numeric_dtype(data[col])
            ]
            if not numeric_columns:
                return html.Div("No numeric columns found for charting.")
            default = self.chart_builder.default_config(list(data.columns), numeric_columns)
            return [
                self.chart_builder.build_layout(
                    index,
                    list(data.columns),
                    numeric_columns,
                    default,
                )
                for index in range(count)
            ]

        @self.app.callback(
            Output({"type": "chart-graph", "index": ALL}, "figure"),
            Output(ids.data_preview, "data"),
            Output(ids.data_preview, "columns"),
            Input(ids.data_store, "data"),
            Input(ids.title_column, "value"),
            Input(ids.title_values, "value"),
            Input(ids.time_column, "value"),
            Input(ids.time_range, "start_date"),
            Input(ids.time_range, "end_date"),
            Input({"type": "chart-filter-title-column", "index": ALL}, "value"),
            Input({"type": "chart-filter-title-values", "index": ALL}, "value"),
            Input({"type": "chart-filter-time-column", "index": ALL}, "value"),
            Input({"type": "chart-filter-time-range", "index": ALL}, "start_date"),
            Input({"type": "chart-filter-time-range", "index": ALL}, "end_date"),
            Input({"type": "chart-type", "index": ALL}, "value"),
            Input({"type": "x-axis", "index": ALL}, "value"),
            Input({"type": "y-axis", "index": ALL}, "value"),
            Input({"type": "aggregation", "index": ALL}, "value"),
            Input({"type": "color-dimension", "index": ALL}, "value"),
            Input({"type": "line-symbol", "index": ALL}, "value"),
            Input({"type": "line-dash", "index": ALL}, "value"),
            Input({"type": "bar-pattern", "index": ALL}, "value"),
            Input({"type": "bar-facet", "index": ALL}, "value"),
            Input({"type": "layout-height", "index": ALL}, "value"),
        )
        def _update_charts(
            data_json: str | None,
            title_column: str | None,
            title_values: list[str] | None,
            time_column: str | None,
            start_date: str | None,
            end_date: str | None,
            chart_title_columns: list[str | None],
            chart_title_values: list[list[str] | None],
            chart_time_columns: list[str | None],
            chart_start_dates: list[str | None],
            chart_end_dates: list[str | None],
            chart_types: list[str],
            x_axes: list[str],
            y_axes: list[str],
            aggregations: list[str],
            color_dimensions: list[str],
            line_symbols: list[str],
            line_dashes: list[str],
            bar_patterns: list[str],
            bar_facets: list[str],
            layout_heights: list[int],
        ):
            if not data_json:
                return [], [], []

            data = pd.read_json(data_json, orient="split")
            global_config = FilterConfig(
                title_column=title_column,
                title_values=title_values or [],
                time_column=time_column,
                start_date=start_date,
                end_date=end_date,
            )
            filtered = self.data_filter.apply(data, global_config)
            preview_columns = [{"name": col, "id": col} for col in filtered.columns]
            preview_data = filtered.head(50).to_dict("records")

            figures = []
            for index in range(len(chart_types)):
                chart_filtered = filtered
                per_chart_config = FilterConfig(
                    title_column=(
                        chart_title_columns[index]
                        if index < len(chart_title_columns)
                        else None
                    ),
                    title_values=(
                        chart_title_values[index]
                        if index < len(chart_title_values)
                        else []
                    ),
                    time_column=(
                        chart_time_columns[index]
                        if index < len(chart_time_columns)
                        else None
                    ),
                    start_date=(
                        chart_start_dates[index]
                        if index < len(chart_start_dates)
                        else None
                    ),
                    end_date=(
                        chart_end_dates[index] if index < len(chart_end_dates) else None
                    ),
                )
                chart_filtered = self.data_filter.apply(chart_filtered, per_chart_config)
                chart_config = self.chart_builder.to_config(
                    chart_type=chart_types[index],
                    x_axis=x_axes[index],
                    y_axis=y_axes[index],
                    aggregation=aggregations[index],
                    color_dimension=color_dimensions[index],
                    line_symbol=line_symbols[index],
                    line_dash=line_dashes[index],
                    bar_pattern=bar_patterns[index],
                    bar_facet=bar_facets[index],
                    layout_height=layout_heights[index],
                )
                chart_data = build_chart_data(chart_filtered, chart_config.__dict__)
                figures.append(self.chart_builder.build_figure(chart_data, chart_config))

            return figures, preview_data, preview_columns

        @self.app.callback(
            Output({"type": "chart-filter-title-column", "index": ALL}, "options"),
            Output({"type": "chart-filter-time-column", "index": ALL}, "options"),
            Input(ids.data_store, "data"),
            Input(ids.chart_count, "data"),
        )
        def _update_chart_filter_columns(data_json: str | None, count: int):
            if not data_json:
                return [[] for _ in range(count)], [[] for _ in range(count)]
            data = pd.read_json(data_json, orient="split")
            options = [{"label": col, "value": col} for col in data.columns]
            return [options for _ in range(count)], [options for _ in range(count)]

        @self.app.callback(
            Output({"type": "chart-filter-title-values", "index": ALL}, "options"),
            Output({"type": "chart-filter-title-values", "index": ALL}, "value"),
            Input({"type": "chart-filter-title-column", "index": ALL}, "value"),
            Input(ids.data_store, "data"),
        )
        def _update_chart_title_values(
            title_columns: list[str | None], data_json: str | None
        ):
            if not data_json:
                return (
                    [[] for _ in range(len(title_columns))],
                    [[] for _ in range(len(title_columns))],
                )
            data = pd.read_json(data_json, orient="split")
            options_list = []
            values_list = []
            for column in title_columns:
                if not column:
                    options_list.append([])
                    values_list.append([])
                    continue
                values = self.data_filter.unique_values(data[column])
                options_list.append([{"label": v, "value": v} for v in values])
                values_list.append(values[:10])
            return options_list, values_list

        @self.app.callback(
            Output({"type": "chart-filter-time-range", "index": ALL}, "min_date_allowed"),
            Output({"type": "chart-filter-time-range", "index": ALL}, "max_date_allowed"),
            Output({"type": "chart-filter-time-range", "index": ALL}, "start_date"),
            Output({"type": "chart-filter-time-range", "index": ALL}, "end_date"),
            Input({"type": "chart-filter-time-column", "index": ALL}, "value"),
            Input(ids.data_store, "data"),
        )
        def _update_chart_time_ranges(
            time_columns: list[str | None], data_json: str | None
        ):
            if not data_json:
                return (
                    [None for _ in range(len(time_columns))],
                    [None for _ in range(len(time_columns))],
                    [None for _ in range(len(time_columns))],
                    [None for _ in range(len(time_columns))],
                )
            data = pd.read_json(data_json, orient="split")
            min_dates = []
            max_dates = []
            start_dates = []
            end_dates = []
            for column in time_columns:
                if not column:
                    min_dates.append(None)
                    max_dates.append(None)
                    start_dates.append(None)
                    end_dates.append(None)
                    continue
                min_time, max_time = self.data_filter.datetime_bounds(data[column])
                if not min_time or not max_time:
                    min_dates.append(None)
                    max_dates.append(None)
                    start_dates.append(None)
                    end_dates.append(None)
                else:
                    min_dates.append(min_time.date())
                    max_dates.append(max_time.date())
                    start_dates.append(min_time.date())
                    end_dates.append(max_time.date())
            return min_dates, max_dates, start_dates, end_dates

    def run(self) -> None:
        self.app.run(debug=False, host="0.0.0.0", port=8050)


if __name__ == "__main__":
    DashboardApp().run()
