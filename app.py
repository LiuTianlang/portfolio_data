from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from dash import Dash, Input, Output, State, dash_table, dcc, html
from dash.dependencies import ALL

from aggregation import build_chart_data
from data_loader import CsvDataLoader
from filters import DataFilter, FilterConfig
from visualization import ChartBuilder


@dataclass(frozen=True)
class ComponentIds:
    upload: str = "csv-upload"
    data_store: str = "data-store"
    upload_info: str = "upload-info"
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
                html.P("Upload a CSV, filter rows, and explore charts with aggregation."),
                html.Div(
                    className="section",
                    children=[
                        html.H2("1) Upload local CSV"),
                        dcc.Upload(
                            id=self.ids.upload,
                            children=html.Div(["Drag and Drop or ", html.A("Select Files")]),
                            style={
                                "width": "100%",
                                "height": "60px",
                                "lineHeight": "60px",
                                "borderWidth": "1px",
                                "borderStyle": "dashed",
                                "borderRadius": "6px",
                                "textAlign": "center",
                            },
                            multiple=False,
                        ),
                        html.Div(id=self.ids.upload_info, className="hint"),
                    ],
                ),
                html.Div(
                    className="section",
                    children=[
                        html.H2("2) Filter data"),
                        html.Div(
                            className="filters",
                            children=[
                                html.Div(
                                    className="filter",
                                    children=[
                                        html.Label("Title filter column"),
                                        dcc.Dropdown(id=self.ids.title_column, clearable=True),
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
                                        dcc.Dropdown(id=self.ids.time_column, clearable=True),
                                    ],
                                ),
                                html.Div(
                                    className="filter",
                                    children=[
                                        html.Label("Time range"),
                                        dcc.DatePickerRange(id=self.ids.time_range),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    className="section",
                    children=[
                        html.Div(
                            className="charts-header",
                            children=[
                                html.H2("3) Build charts"),
                                html.Button("Add chart", id=self.ids.add_chart),
                            ],
                        ),
                        html.Div(id=self.ids.charts_container),
                    ],
                ),
                html.Div(
                    className="section",
                    children=[
                        html.H2("4) Preview filtered data"),
                        dash_table.DataTable(
                            id=self.ids.data_preview,
                            page_size=10,
                            style_table={"overflowX": "auto"},
                        ),
                    ],
                ),
                dcc.Store(id=self.ids.data_store),
                dcc.Store(id=self.ids.chart_count, data=1),
            ],
        )

    def _register_callbacks(self) -> None:
        ids = self.ids

        @self.app.callback(
            Output(ids.data_store, "data"),
            Output(ids.upload_info, "children"),
            Input(ids.upload, "contents"),
            State(ids.upload, "filename"),
        )
        def _load_csv(contents: str | None, filename: str | None) -> tuple[str | None, str]:
            if not contents:
                return None, ""
            payload = self.loader.parse_contents(contents, filename)
            if payload.error:
                return None, payload.error
            if payload.dataframe is None or payload.dataframe.empty:
                return None, "The uploaded CSV has no rows."
            return payload.dataframe.to_json(date_format="iso", orient="split"), ""

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
            config = FilterConfig(
                title_column=title_column,
                title_values=title_values or [],
                time_column=time_column,
                start_date=start_date,
                end_date=end_date,
            )
            filtered = self.data_filter.apply(data, config)
            preview_columns = [{"name": col, "id": col} for col in filtered.columns]
            preview_data = filtered.head(50).to_dict("records")

            figures = []
            for index in range(len(chart_types)):
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
                chart_data = build_chart_data(filtered, chart_config.__dict__)
                figures.append(self.chart_builder.build_figure(chart_data, chart_config))

            return figures, preview_data, preview_columns

    def run(self) -> None:
        self.app.run(debug=False, host="0.0.0.0", port=8050)


if __name__ == "__main__":
    DashboardApp().run()
