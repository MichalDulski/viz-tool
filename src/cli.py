"""Command Line Interface using Typer and Rich."""

from enum import Enum
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from src.engine import compare_datasets, load_data, unpivot_data
from src.graphs import ChartType, ExportFormat, get_renderer, list_renderers

app = typer.Typer(no_args_is_help=True)
console = Console()


class ChartTypeOption(str, Enum):
    """CLI enum for chart type selection."""

    bar = "bar"
    line = "line"
    scatter = "scatter"
    histogram = "histogram"
    pie = "pie"


class LayoutOption(str, Enum):
    """CLI enum for network layout selection."""

    spring = "spring"
    circular = "circular"
    kamada_kawai = "kamada_kawai"
    shell = "shell"
    random = "random"


@app.callback()
def callback() -> None:
    """Data visualization CLI tool."""
    pass


@app.command()
def compare(file1: str, file2: str, key: str = "id") -> None:
    """
    Compare two datasets and show differences in the terminal.

    Args:
        file1: Path to the first dataset file.
        file2: Path to the second dataset file.
        key: Column name to join datasets on (default: id).
    """
    with console.status("[bold green]Loading data..."):
        df1 = load_data(file1)
        df2 = load_data(file2)
        result = compare_datasets(df1, df2, key)
    table = Table(title=f"Comparison: {file1} vs {file2}")
    for col_name in result.columns:
        style = "bold red" if "diff" in col_name else "white"
        table.add_column(col_name, style=style)
    for row in result.head(20).iter_rows():
        table.add_row(*[str(x) for x in row])
    console.print(table)
    console.print(f"[dim]Showing top 20 of {len(result)} rows[/dim]")


@app.command()
def chart(
    file: str = typer.Argument(..., help="Path to data file (CSV, JSON, Parquet)"),
    chart_type: ChartTypeOption = typer.Option(
        ChartTypeOption.bar, "--type", "-t", help="Type of chart to create"
    ),
    x: str = typer.Option(..., "--x", "-x", help="Column name for x-axis"),
    y: list[str] = typer.Option(..., "--y", "-y", help="Column name(s) for y-axis"),
    output: str = typer.Option(
        "chart.html", "--output", "-o", help="Output file path"
    ),
    title: str = typer.Option(None, "--title", help="Chart title"),
    color: str = typer.Option(None, "--color", "-c", help="Column for color grouping"),
    renderer: str = typer.Option(
        "plotly", "--renderer", "-r", help="Renderer to use"
    ),
    id_cols: str = typer.Option(
        None, "--id-cols", help="Comma-separated identifier columns for unpivot"
    ),
    value_start: int = typer.Option(
        None, "--value-start", help="Start index for value columns (0-based, inclusive)"
    ),
    value_end: int = typer.Option(
        None, "--value-end", help="End index for value columns (exclusive, defaults to last column)"
    ),
    var_name: str = typer.Option(
        "variable", "--var-name", help="Name for the unpivoted variable column"
    ),
    value_name: str = typer.Option(
        "value", "--value-name", help="Name for the unpivoted value column"
    ),
) -> None:
    """
    Create a statistical chart from data file.

    Examples:
        viz chart data.csv --type bar --x category --y value --output chart.html
        viz chart data.csv --type scatter --x col1 --y col2 --color group

    Unpivot wide-format data (two modes):
        # Mode 1: Specify id columns, rest become values
        viz chart wide.csv --type line --id-cols "Name,Code" \\
            --var-name Year --value-name Population --x Year --y Population --color Name

        # Mode 2: Specify value column start index, rest of columns become values
        viz chart wide.csv --type line --value-start 4 \\
            --var-name Year --value-name Population --x Year --y Population --color Name
    """
    with console.status("[bold green]Loading data..."):
        df = load_data(file)
    has_id_cols = id_cols is not None
    has_value_start = value_start is not None
    is_unpivot_requested = has_id_cols or has_value_start
    if is_unpivot_requested:
        with console.status("[bold yellow]Unpivoting data..."):
            id_columns = [col.strip() for col in id_cols.split(",")] if id_cols else None
            df = unpivot_data(
                df=df,
                id_columns=id_columns,
                value_columns_start=value_start,
                value_columns_end=value_end,
                variable_name=var_name,
                value_name=value_name,
            )
    output_path = Path(output)
    export_format = _get_export_format(output_path)
    chart_type_enum = ChartType(chart_type.value)
    with console.status("[bold blue]Creating chart..."):
        graph_renderer = get_renderer(renderer)
        fig = graph_renderer.create_chart(
            df=df,
            chart_type=chart_type_enum,
            x=x,
            y=y,
            title=title,
            color=color,
        )
        graph_renderer.export(fig, str(output_path), export_format)
    console.print(f"[green]✓[/green] Chart saved to: [bold]{output_path}[/bold]")


@app.command()
def network(
    file: str = typer.Argument(..., help="Path to edge list file (CSV, JSON, Parquet)"),
    source: str = typer.Option(..., "--source", "-s", help="Column name for source nodes"),
    target: str = typer.Option(..., "--target", "-t", help="Column name for target nodes"),
    output: str = typer.Option(
        "network.html", "--output", "-o", help="Output file path"
    ),
    weight: str = typer.Option(None, "--weight", "-w", help="Column for edge weights"),
    title: str = typer.Option(None, "--title", help="Graph title"),
    layout: LayoutOption = typer.Option(
        LayoutOption.spring, "--layout", "-l", help="Layout algorithm"
    ),
    renderer: str = typer.Option(
        "plotly", "--renderer", "-r", help="Renderer to use"
    ),
) -> None:
    """
    Create a network graph from edge list data.

    The input file should contain at least two columns representing
    source and target nodes for each edge.

    Examples:
        viz network edges.csv --source from --target to --output graph.html
        viz network edges.csv --source a --target b --weight w --layout circular
    """
    with console.status("[bold green]Loading data..."):
        df = load_data(file)
    output_path = Path(output)
    export_format = _get_export_format(output_path)
    with console.status("[bold blue]Creating network graph..."):
        graph_renderer = get_renderer(renderer)
        fig = graph_renderer.create_network(
            df=df,
            source=source,
            target=target,
            weight=weight,
            title=title,
            layout=layout.value,
        )
        graph_renderer.export(fig, str(output_path), export_format)
    console.print(f"[green]✓[/green] Network graph saved to: [bold]{output_path}[/bold]")


@app.command()
def renderers() -> None:
    """List available graph renderers."""
    available = list_renderers()
    console.print("[bold]Available renderers:[/bold]")
    for name in available:
        console.print(f"  • {name}")


def _get_export_format(path: Path) -> ExportFormat:
    """Determine export format from file extension."""
    suffix = path.suffix.lower()
    format_map = {
        ".html": ExportFormat.HTML,
        ".png": ExportFormat.PNG,
        ".pdf": ExportFormat.PDF,
        ".svg": ExportFormat.SVG,
    }
    if suffix not in format_map:
        raise typer.BadParameter(
            f"Unsupported output format: {suffix}. "
            f"Supported: {', '.join(format_map.keys())}"
        )
    return format_map[suffix]


if __name__ == "__main__":
    app()
