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
            **kwargs: Additional Plotly-specific options.

        Returns:
            A Plotly Figure object.
        """
        pandas_df = df.to_pandas()
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

