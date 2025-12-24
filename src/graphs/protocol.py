"""Protocol definition for graph renderers."""

from typing import Protocol

import polars as pl

from .types import ChartType, ExportFormat, FigureResult


class GraphRenderer(Protocol):
    """
    Protocol defining the contract for all graph renderers.

    Implementations must provide methods for creating statistical charts,
    network graphs, and exporting figures to various formats.
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
        Create a statistical chart from DataFrame data.

        Args:
            df: Source DataFrame containing the data.
            chart_type: Type of chart to create.
            x: Column name for x-axis.
            y: Column name(s) for y-axis.
            title: Optional chart title.
            color: Optional column name for color grouping.
            **kwargs: Additional renderer-specific options.

        Returns:
            A renderer-specific figure object.
        """
        ...

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
        Create a network graph from edge list data.

        Args:
            df: DataFrame containing edge list (source, target, optional weight).
            source: Column name for source nodes.
            target: Column name for target nodes.
            weight: Optional column name for edge weights.
            title: Optional chart title.
            layout: Graph layout algorithm (spring, circular, kamada_kawai, etc.).
            **kwargs: Additional renderer-specific options.

        Returns:
            A renderer-specific figure object.
        """
        ...

    def export(
        self,
        figure: FigureResult,
        filepath: str,
        export_format: ExportFormat,
    ) -> None:
        """
        Export figure to a file.

        Args:
            figure: The figure object to export.
            filepath: Destination file path.
            export_format: Output format (HTML, PNG, PDF, SVG).
        """
        ...

    def to_html(self, figure: FigureResult) -> str:
        """
        Convert figure to HTML string for embedding.

        Args:
            figure: The figure object to convert.

        Returns:
            HTML string representation of the figure.
        """
        ...

