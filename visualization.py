from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import plotly.express as px
from dash import dcc, html

from aggregation import AGGREGATIONS, build_chart_data

CHART_TYPES = ["Line", "Bar", "Pie", "Heatmap"]


@dataclass(frozen=True)
class ChartConfig:
    chart_type: str
    x_axis: str
    y_axis: str
    aggregation: str
    color_dimension: str
    line_symbol: str
    line_dash: str
    bar_pattern: str
    bar_facet: str
    layout_height: int


class ChartBuilder:
    """Build chart controls and figures."""

    def default_config(self, columns: list[str], numeric_columns: list[str]) -> ChartConfig:
        return ChartConfig(
            chart_type="Line",
            x_axis=columns[0],
            y_axis=numeric_columns[0],
            aggregation="None (raw rows)",
            color_dimension="(none)",
            line_symbol="(none)",
            line_dash="(none)",
            bar_pattern="(none)",
            bar_facet="(none)",
            layout_height=480,
        )

    def build_layout(
        self,
        index: int,
        columns: list[str],
        numeric_columns: list[str],
        config: ChartConfig,
    ) -> html.Div:
        dimension_options = ["(none)"] + columns
        return html.Div(
            className="chart-card",
            children=[
                html.H4(f"Chart {index + 1}"),
                html.Div(
                    className="chart-card__content",
                    children=[
                        html.Div(
                            className="chart-card__controls",
                            children=[
                                html.Label("Chart type"),
                                dcc.Dropdown(
                                    id={"type": "chart-type", "index": index},
                                    options=[{"label": t, "value": t} for t in CHART_TYPES],
                                    value=config.chart_type,
                                    clearable=False,
                                    persistence=True,
                                ),
                                html.Label("X-axis"),
                                dcc.Dropdown(
                                    id={"type": "x-axis", "index": index},
                                    options=[{"label": c, "value": c} for c in columns],
                                    value=config.x_axis,
                                    clearable=False,
                                    persistence=True,
                                ),
                                html.Label("Y-axis"),
                                dcc.Dropdown(
                                    id={"type": "y-axis", "index": index},
                                    options=[{"label": c, "value": c} for c in numeric_columns],
                                    value=config.y_axis,
                                    clearable=False,
                                    persistence=True,
                                ),
                                html.Label("Aggregation"),
                                dcc.Dropdown(
                                    id={"type": "aggregation", "index": index},
                                    options=[
                                        {"label": label, "value": label}
                                        for label in AGGREGATIONS.keys()
                                    ],
                                    value=config.aggregation,
                                    clearable=False,
                                    persistence=True,
                                ),
                                html.Label("Color / stack by (optional)"),
                                dcc.Dropdown(
                                    id={"type": "color-dimension", "index": index},
                                    options=[{"label": c, "value": c} for c in dimension_options],
                                    value=config.color_dimension,
                                    clearable=False,
                                    persistence=True,
                                ),
                                html.Label("Dot shape (optional)"),
                                dcc.Dropdown(
                                    id={"type": "line-symbol", "index": index},
                                    options=[{"label": c, "value": c} for c in dimension_options],
                                    value=config.line_symbol,
                                    clearable=False,
                                    persistence=True,
                                ),
                                html.Label("Line type (optional)"),
                                dcc.Dropdown(
                                    id={"type": "line-dash", "index": index},
                                    options=[{"label": c, "value": c} for c in dimension_options],
                                    value=config.line_dash,
                                    clearable=False,
                                    persistence=True,
                                ),
                                html.Label("Bar pattern (optional)"),
                                dcc.Dropdown(
                                    id={"type": "bar-pattern", "index": index},
                                    options=[{"label": c, "value": c} for c in dimension_options],
                                    value=config.bar_pattern,
                                    clearable=False,
                                    persistence=True,
                                ),
                                html.Label("Facet column (optional)"),
                                dcc.Dropdown(
                                    id={"type": "bar-facet", "index": index},
                                    options=[{"label": c, "value": c} for c in dimension_options],
                                    value=config.bar_facet,
                                    clearable=False,
                                    persistence=True,
                                ),
                                html.Label("Chart height"),
                                dcc.Slider(
                                    id={"type": "layout-height", "index": index},
                                    min=320,
                                    max=800,
                                    step=20,
                                    value=config.layout_height,
                                    marks=None,
                                    tooltip={"placement": "bottom", "always_visible": True},
                                    persistence=True,
                                ),
                            ],
                        ),
                        html.Div(
                            className="chart-card__chart",
                            children=[
                                dcc.Loading(
                                    dcc.Graph(
                                        id={"type": "chart-graph", "index": index},
                                        config={"displayModeBar": False},
                                    )
                                )
                            ],
                        ),
                    ],
                ),
            ],
        )

    def build_figure(self, chart_data: pd.DataFrame, config: ChartConfig) -> dict:
        if chart_data.empty:
            return px.scatter().update_layout(
                title="No data after filtering",
                xaxis={"visible": False},
                yaxis={"visible": False},
                height=config.layout_height,
            )

        if config.chart_type == "Line":
            fig = px.line(
                chart_data,
                x=config.x_axis,
                y=config.y_axis,
                color=None if config.color_dimension == "(none)" else config.color_dimension,
                symbol=None if config.line_symbol == "(none)" else config.line_symbol,
                line_dash=None if config.line_dash == "(none)" else config.line_dash,
                markers=True,
            )
        elif config.chart_type == "Bar":
            bar_mode = "stack" if config.color_dimension != "(none)" else "group"
            fig = px.bar(
                chart_data,
                x=config.x_axis,
                y=config.y_axis,
                color=None if config.color_dimension == "(none)" else config.color_dimension,
                pattern_shape=None if config.bar_pattern == "(none)" else config.bar_pattern,
                facet_col=None if config.bar_facet == "(none)" else config.bar_facet,
                barmode=bar_mode,
            )
        elif config.chart_type == "Pie":
            fig = px.pie(
                chart_data,
                names=config.x_axis,
                values=config.y_axis,
                color=None if config.color_dimension == "(none)" else config.color_dimension,
            )
        else:
            fig = px.density_heatmap(
                chart_data,
                x=config.x_axis,
                y=config.y_axis,
                z=config.y_axis if config.aggregation != "None (raw rows)" else None,
                histfunc=AGGREGATIONS.get(config.aggregation) or "count",
                color_continuous_scale="Viridis",
            )

        fig.update_layout(
            height=int(config.layout_height),
            margin=dict(l=20, r=20, t=40, b=20),
        )
        return fig

    def to_config(
        self,
        chart_type: str,
        x_axis: str,
        y_axis: str,
        aggregation: str,
        color_dimension: str,
        line_symbol: str,
        line_dash: str,
        bar_pattern: str,
        bar_facet: str,
        layout_height: int,
    ) -> ChartConfig:
        return ChartConfig(
            chart_type=chart_type,
            x_axis=x_axis,
            y_axis=y_axis,
            aggregation=aggregation,
            color_dimension=color_dimension,
            line_symbol=line_symbol,
            line_dash=line_dash,
            bar_pattern=bar_pattern,
            bar_facet=bar_facet,
            layout_height=layout_height,
        )
