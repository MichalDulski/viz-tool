"""Factory for creating graph renderer instances."""

from typing import TYPE_CHECKING

from .plotly_renderer import PlotlyRenderer

if TYPE_CHECKING:
    from .protocol import GraphRenderer

# Registry of available renderer implementations
_RENDERERS: dict[str, type["GraphRenderer"]] = {
    "plotly": PlotlyRenderer,
}


def get_renderer(name: str = "plotly") -> "GraphRenderer":
    """
    Factory function to get a renderer instance by name.

    Args:
        name: Name of the renderer to instantiate (default: plotly).

    Returns:
        An instance of the requested renderer.

    Raises:
        ValueError: If the renderer name is not registered.
    """
    if name not in _RENDERERS:
        available = list(_RENDERERS.keys())
        raise ValueError(f"Unknown renderer: {name}. Available: {available}")
    return _RENDERERS[name]()


def register_renderer(name: str, renderer_class: type["GraphRenderer"]) -> None:
    """
    Register a new renderer implementation.

    Use this function to add custom renderer implementations at runtime.

    Args:
        name: Unique name for the renderer.
        renderer_class: Class implementing the GraphRenderer protocol.
    """
    _RENDERERS[name] = renderer_class


def list_renderers() -> list[str]:
    """
    List all registered renderer names.

    Returns:
        List of available renderer names.
    """
    return list(_RENDERERS.keys())

