"""Plotly implementation of the GraphRenderer protocol."""

import networkx as nx
import plotly.express as px
import plotly.graph_objects as go
import polars as pl

from .types import ChartType, ExportFormat, FigureResult


class PlotlyRenderer:
    """
    Graph renderer implementation using Plotly.

    Provides interactive charts and network visualizations
    with support for HTML, PNG, PDF, and SVG export.
    """

    def create_chart(
        self,
        df: pl.DataFrame,
        chart_type: ChartType,
        x: str,
        y: str | list[str],
        *,
        title: str | None = None,
        color: str | None = None,
        facet_columns: list[str] | None = None,
        **kwargs: object,
    ) -> FigureResult:
        """
        Create a statistical chart using Plotly Express.

        Args:
            df: Source DataFrame containing the data.
            chart_type: Type of chart to create.
            x: Column name for x-axis.
            y: Column name(s) for y-axis.
            title: Optional chart title.
            color: Optional column name for color grouping.
            facet_columns: Optional list of columns for creating interactive
                dropdown selector. Multiple columns are combined as "Val1 | Val2".
            **kwargs: Additional Plotly-specific options.

        Returns:
            A Plotly Figure object.
        """
        pandas_df = df.to_pandas()
        if facet_columns is not None and len(facet_columns) > 0:
            return self._create_faceted_chart(
                pandas_df, chart_type, x, y, title, color, facet_columns, **kwargs
            )
        chart_builders = {
            ChartType.BAR: self._create_bar,
            ChartType.LINE: self._create_line,
            ChartType.SCATTER: self._create_scatter,
            ChartType.HISTOGRAM: self._create_histogram,
            ChartType.PIE: self._create_pie,
        }
        builder = chart_builders.get(chart_type)
        if builder is None:
            raise ValueError(f"Unsupported chart type: {chart_type}")
        return builder(pandas_df, x, y, title, color, **kwargs)

    def _create_bar(
        self,
        df: object,
        x: str,
        y: str | list[str],
        title: str | None,
        color: str | None,
        **kwargs: object,
    ) -> go.Figure:
        """Create a bar chart."""
        return px.bar(df, x=x, y=y, title=title, color=color, **kwargs)

    def _create_line(
        self,
        df: object,
        x: str,
        y: str | list[str],
        title: str | None,
        color: str | None,
        **kwargs: object,
    ) -> go.Figure:
        """Create a line chart."""
        return px.line(df, x=x, y=y, title=title, color=color, **kwargs)

    def _create_scatter(
        self,
        df: object,
        x: str,
        y: str | list[str],
        title: str | None,
        color: str | None,
        **kwargs: object,
    ) -> go.Figure:
        """Create a scatter plot."""
        y_col = y[0] if isinstance(y, list) else y
        return px.scatter(df, x=x, y=y_col, title=title, color=color, **kwargs)

    def _create_histogram(
        self,
        df: object,
        x: str,
        y: str | list[str],
        title: str | None,
        color: str | None,
        **kwargs: object,
    ) -> go.Figure:
        """Create a histogram."""
        return px.histogram(df, x=x, title=title, color=color, **kwargs)

    def _create_pie(
        self,
        df: object,
        x: str,
        y: str | list[str],
        title: str | None,
        color: str | None,
        **kwargs: object,
    ) -> go.Figure:
        """Create a pie chart."""
        y_col = y[0] if isinstance(y, list) else y
        return px.pie(df, names=x, values=y_col, title=title, **kwargs)

    def _create_faceted_chart(
        self,
        df: object,
        chart_type: ChartType,
        x: str,
        y: str | list[str],
        title: str | None,
        color: str | None,
        facet_columns: list[str],
        **kwargs: object,
    ) -> go.Figure:
        """
        Create an interactive chart with dropdown selector for facet values.

        Generates separate traces for each unique combination of facet column
        values and adds a dropdown menu to switch between them. Multiple facet
        columns are combined as "Val1 | Val2 | ...".
        """
        import pandas as pd
        pandas_df = df if isinstance(df, pd.DataFrame) else df
        facet_label = " | ".join(facet_columns)
        if len(facet_columns) == 1:
            pandas_df = pandas_df.copy()
            pandas_df["_facet_combined"] = pandas_df[facet_columns[0]].astype(str)
        else:
            pandas_df = pandas_df.copy()
            pandas_df["_facet_combined"] = pandas_df[facet_columns].apply(
                lambda row: " | ".join(str(v) for v in row), axis=1
            )
        facet_values = sorted(pandas_df["_facet_combined"].unique().tolist())
        if len(facet_values) == 0:
            raise ValueError(f"No values found in facet columns '{facet_label}'")
        fig = go.Figure()
        y_col = y[0] if isinstance(y, list) else y

        # Handle pie charts differently - create a single pie chart that gets updated
        if chart_type == ChartType.PIE:
            # Start with the first facet
            first_facet_df = pandas_df[pandas_df["_facet_combined"] == facet_values[0]]
            fig.add_trace(go.Pie(
                labels=first_facet_df[x].tolist(),
                values=first_facet_df[y_col].tolist(),
                name=str(facet_values[0]),
            ))
        else:
            # For other chart types, create multiple traces with visibility toggle
            for idx, facet_value in enumerate(facet_values):
                facet_df = pandas_df[pandas_df["_facet_combined"] == facet_value]
                is_visible = idx == 0
                self._add_facet_traces(
                    fig, facet_df, chart_type, x, y_col, color, facet_value, is_visible
                )
        if chart_type == ChartType.PIE:
            dropdown_buttons = self._create_pie_dropdown_buttons(
                pandas_df, facet_values, facet_label, x, y_col
            )
        else:
            dropdown_buttons = self._create_dropdown_buttons(
                pandas_df, facet_values, facet_label, chart_type, color
            )
        chart_title = title or f"Chart by {facet_label}"
        fig.update_layout(
            title=f"{chart_title}: {facet_values[0]}",
            updatemenus=[{
                "active": 0,
                "buttons": dropdown_buttons,
                "direction": "down",
                "showactive": True,
                "x": 0.0,
                "xanchor": "left",
                "y": 1.15,
                "yanchor": "top",
            }],
        )
        return fig

    def _add_facet_traces(
        self,
        fig: go.Figure,
        df: object,
        chart_type: ChartType,
        x: str,
        y: str,
        color: str | None,
        facet_value: str,
        is_visible: bool,
    ) -> None:
        """Add traces for a single facet value to the figure."""
        import pandas as pd
        pandas_df = df if isinstance(df, pd.DataFrame) else df
        if color is not None and color in pandas_df.columns:
            color_values = sorted(pandas_df[color].unique().tolist())
            for color_val in color_values:
                color_df = pandas_df[pandas_df[color] == color_val]
                self._add_single_trace(
                    fig, color_df, chart_type, x, y, is_visible,
                    name=str(color_val), facet_value=facet_value
                )
        else:
            self._add_single_trace(
                fig, pandas_df, chart_type, x, y, is_visible,
                name=str(facet_value), facet_value=facet_value
            )

    def _add_single_trace(
        self,
        fig: go.Figure,
        df: object,
        chart_type: ChartType,
        x: str,
        y: str,
        is_visible: bool,
        name: str,
        facet_value: str,
    ) -> None:
        """Add a single trace to the figure based on chart type."""
        import pandas as pd
        pandas_df = df if isinstance(df, pd.DataFrame) else df
        trace_meta = {"facet_value": facet_value}
        if chart_type == ChartType.BAR:
            fig.add_trace(go.Bar(
                x=pandas_df[x].tolist(),
                y=pandas_df[y].tolist(),
                name=name,
                visible=is_visible,
                meta=trace_meta,
            ))
        elif chart_type == ChartType.LINE:
            fig.add_trace(go.Scatter(
                x=pandas_df[x].tolist(),
                y=pandas_df[y].tolist(),
                mode="lines+markers",
                name=name,
                visible=is_visible,
                meta=trace_meta,
            ))
        elif chart_type == ChartType.SCATTER:
            fig.add_trace(go.Scatter(
                x=pandas_df[x].tolist(),
                y=pandas_df[y].tolist(),
                mode="markers",
                name=name,
                visible=is_visible,
                meta=trace_meta,
            ))
        elif chart_type == ChartType.HISTOGRAM:
            fig.add_trace(go.Histogram(
                x=pandas_df[x].tolist(),
                name=name,
                visible=is_visible,
                meta=trace_meta,
            ))
        elif chart_type == ChartType.PIE:
            fig.add_trace(go.Pie(
                labels=pandas_df[x].tolist(),
                values=pandas_df[y].tolist(),
                name=name,
                visible=is_visible,
                meta=trace_meta,
            ))

    def _create_dropdown_buttons(
        self,
        df: object,
        facet_values: list[str],
        facet_column: str,
        chart_type: ChartType,
        color: str | None,
    ) -> list[dict]:
        """Create dropdown button definitions for facet selector."""
        import pandas as pd
        pandas_df = df if isinstance(df, pd.DataFrame) else df
        buttons = []
        has_color = color is not None and color in pandas_df.columns
        if has_color:
            num_color_values = len(pandas_df[color].unique())
        else:
            num_color_values = 1
        traces_per_facet = num_color_values
        total_traces = len(facet_values) * traces_per_facet
        for idx, facet_value in enumerate(facet_values):
            visibility = [False] * total_traces
            start_idx = idx * traces_per_facet
            end_idx = start_idx + traces_per_facet
            for i in range(start_idx, end_idx):
                visibility[i] = True
            buttons.append({
                "label": str(facet_value),
                "method": "update",
                "args": [
                    {"visible": visibility},
                    {"title": f"Chart by {facet_column}: {facet_value}"}
                ],
            })
        return buttons

    def _create_pie_dropdown_buttons(
        self,
        df: object,
        facet_values: list[str],
        facet_label: str,
        x: str,
        y: str,
    ) -> list[dict]:
        """Create dropdown button definitions for pie chart facet selector."""
        import pandas as pd
        pandas_df = df if isinstance(df, pd.DataFrame) else df
        buttons = []
        for facet_value in facet_values:
            facet_df = pandas_df[pandas_df["_facet_combined"] == facet_value]
            buttons.append({
                "label": str(facet_value),
                "method": "update",
                "args": [
                    {
                        "labels": [facet_df[x].tolist()],
                        "values": [facet_df[y].tolist()],
                        "name": [str(facet_value)],
                    },
                    {"title": f"Chart by {facet_label}: {facet_value}"}
                ],
            })
        return buttons

    def create_network(
        self,
        df: pl.DataFrame,
        source: str,
        target: str,
        *,
        weight: str | None = None,
        title: str | None = None,
        layout: str = "spring",
        **kwargs: object,
    ) -> FigureResult:
        """
        Create an interactive network graph using NetworkX and Plotly.

        Args:
            df: DataFrame containing edge list data.
            source: Column name for source nodes.
            target: Column name for target nodes.
            weight: Optional column name for edge weights.
            title: Optional chart title.
            layout: Layout algorithm (spring, circular, kamada_kawai, shell, random).
            **kwargs: Additional options.

        Returns:
            A Plotly Figure object with the network visualization.
        """
        graph = self._build_networkx_graph(df, source, target, weight)
        positions = self._calculate_layout(graph, layout)
        return self._render_network_figure(graph, positions, title)

    def _build_networkx_graph(
        self,
        df: pl.DataFrame,
        source: str,
        target: str,
        weight: str | None,
    ) -> nx.Graph:
        """Build a NetworkX graph from edge list DataFrame."""
        graph = nx.Graph()
        for row in df.iter_rows(named=True):
            edge_data = {}
            if weight and weight in row:
                edge_data["weight"] = row[weight]
            graph.add_edge(row[source], row[target], **edge_data)
        return graph

    def _calculate_layout(
        self,
        graph: nx.Graph,
        layout: str,
    ) -> dict[str, tuple[float, float]]:
        """Calculate node positions using specified layout algorithm."""
        layout_functions = {
            "spring": nx.spring_layout,
            "circular": nx.circular_layout,
            "kamada_kawai": nx.kamada_kawai_layout,
            "shell": nx.shell_layout,
            "random": nx.random_layout,
        }
        layout_func = layout_functions.get(layout, nx.spring_layout)
        return layout_func(graph)

    def _render_network_figure(
        self,
        graph: nx.Graph,
        positions: dict[str, tuple[float, float]],
        title: str | None,
    ) -> go.Figure:
        """Render NetworkX graph as a Plotly figure."""
        edge_x: list[float | None] = []
        edge_y: list[float | None] = []
        for edge in graph.edges():
            x0, y0 = positions[edge[0]]
            x1, y1 = positions[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
        edge_trace = go.Scatter(
            x=edge_x,
            y=edge_y,
            line={"width": 1, "color": "#888"},
            hoverinfo="none",
            mode="lines",
        )
        node_x = [positions[node][0] for node in graph.nodes()]
        node_y = [positions[node][1] for node in graph.nodes()]
        node_degrees = [graph.degree(node) for node in graph.nodes()]
        node_labels = [str(node) for node in graph.nodes()]
        node_trace = go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            hoverinfo="text",
            text=node_labels,
            textposition="top center",
            marker={
                "showscale": True,
                "colorscale": "Viridis",
                "size": 20,
                "color": node_degrees,
                "colorbar": {
                    "thickness": 15,
                    "title": "Node Connections",
                    "xanchor": "left",
                },
            },
        )
        fig = go.Figure(
            data=[edge_trace, node_trace],
            layout=go.Layout(
                title=title or "Network Graph",
                titlefont_size=16,
                showlegend=False,
                hovermode="closest",
                xaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
                yaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
            ),
        )
        return fig

    def export(
        self,
        figure: FigureResult,
        filepath: str,
        export_format: ExportFormat,
    ) -> None:
        """
        Export Plotly figure to file.

        Args:
            figure: The Plotly Figure object to export.
            filepath: Destination file path.
            export_format: Output format.
        """
        if export_format == ExportFormat.HTML:
            figure.write_html(filepath)
        elif export_format == ExportFormat.PNG:
            figure.write_image(filepath, format="png")
        elif export_format == ExportFormat.PDF:
            figure.write_image(filepath, format="pdf")
        elif export_format == ExportFormat.SVG:
            figure.write_image(filepath, format="svg")
        else:
            raise ValueError(f"Unsupported export format: {export_format}")

    def to_html(self, figure: FigureResult) -> str:
        """
        Convert Plotly figure to HTML string.

        Args:
            figure: The Plotly Figure object.

        Returns:
            HTML string with embedded interactive chart.
        """
        return figure.to_html(include_plotlyjs=True, full_html=False)

