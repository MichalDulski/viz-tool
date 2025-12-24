"""Shared types for graph visualization module."""

from enum import Enum
from typing import Any


class ChartType(Enum):
    """Enumeration of supported chart types."""

    BAR = "bar"
    LINE = "line"
    SCATTER = "scatter"
    HISTOGRAM = "histogram"
    PIE = "pie"


class ExportFormat(Enum):
    """Enumeration of supported export formats."""

    HTML = "html"
    PNG = "png"
    PDF = "pdf"
    SVG = "svg"


# FigureResult is a type alias for renderer-specific figure objects.
# Each renderer implementation wraps its native figure type.
# Examples: plotly.graph_objects.Figure, altair.Chart, matplotlib.Figure
FigureResult = Any

