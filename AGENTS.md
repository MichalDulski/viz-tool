# AGENTS.md - Project Context for AI Assistants

## Project Overview

**viz-tool** is a CLI-first data visualization and comparison tool built with Python. It provides both a terminal interface (CLI) and a web GUI for comparing datasets, creating statistical charts, and visualizing network graphs.

**Tech Stack:**

- **Polars** - High-performance DataFrame library for data processing
- **Typer + Rich** - CLI framework with beautiful terminal output
- **Streamlit** - Web-based GUI
- **Plotly** - Interactive chart and graph visualization
- **NetworkX** - Network graph data structures and algorithms
- **Kaleido** - Static image export (PNG, PDF, SVG)
- **uv** - Fast Python package manager
- **Podman/Docker** - Containerization (zero local Python dependencies required)

## Architecture

The application follows a layered architecture with clear separation of concerns:

- **Presentation Layer** - User interfaces (CLI, Web GUI)
- **Business Logic Layer** - Data processing and transformations
- **Infrastructure Layer** - Rendering and export adapters (swappable implementations)

```
┌──────────────────────────────────────────────────────────────────┐
│                     Presentation Layer                           │
│  ┌─────────────────────┐     ┌─────────────────────────┐         │
│  │  cli.py             │     │  web.py                 │         │
│  │  (Typer + Rich)     │     │  (Streamlit)            │         │
│  │  Terminal Interface │     │  Browser Interface      │         │
│  └──────────┬──────────┘     └───────────┬─────────────┘         │
│             │                            │                       │
│             └────────────┬───────────────┘                       │
│                          ▼                                       │
├──────────────────────────────────────────────────────────────────┤
│                     Business Logic Layer                         │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  engine.py                                                 │  │
│  │  - load_data(): File format detection & loading            │  │
│  │  - compare_datasets(): Data joins & diff calculations      │  │
│  │  - unpivot_data(): Wide-to-long format transformation      │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│                     Infrastructure Layer                         │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  graphs/ (Export & Rendering Package)                      │  │
│  │  - GraphRenderer Protocol (abstract interface)             │  │
│  │  - PlotlyRenderer (concrete implementation)                │  │
│  │  - Factory pattern for swappable backends                  │  │
│  │                                                            │  │
│  │  Responsibility: Takes processed data, renders to output   │  │
│  │  formats (HTML, PNG, PDF, SVG). No business logic here.    │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
viz-tool/
├── AGENTS.md              # This file - AI assistant context
├── pyproject.toml         # Dependencies
├── Dockerfile             # Container with Chromium for image export
├── compose.yaml           # Services: gui (port 8501), cli
├── data/                  # Data files directory
│   ├── sales_jan.csv      # Sample dataset A (long format)
│   ├── sales_feb.csv      # Sample dataset B (long format)
│   └── demography.csv     # Sample wide-format dataset (for unpivot)
└── src/
    ├── __init__.py
    ├── engine.py          # Business Logic: data loading, transformations
    ├── cli.py             # Presentation: CLI interface (Typer + Rich)
    ├── web.py             # Presentation: Web GUI (Streamlit)
    └── graphs/            # Infrastructure: rendering & export adapters
        ├── __init__.py    # Public API exports
        ├── types.py       # ChartType, ExportFormat enums
        ├── protocol.py    # GraphRenderer Protocol definition
        ├── factory.py     # Renderer factory (get_renderer, register_renderer)
        └── plotly_renderer.py  # Plotly implementation
```

## Key Files

### src/engine.py

Core data processing module using Polars.

**Functions:**

- `load_data(filepath: str) -> pl.DataFrame` - Auto-detects file format (CSV, JSON, Parquet) and loads into a Polars DataFrame
- `compare_datasets(df_a: pl.DataFrame, df_b: pl.DataFrame, join_key: str) -> pl.DataFrame` - Performs outer join on two datasets and calculates difference columns for all numeric fields
- `unpivot_data(df, id_columns, value_columns_start, value_columns_end, variable_name, value_name) -> pl.DataFrame` - Transforms wide-format data to long format (melt/unpivot operation)
- `apply_lookup(df, lookup_df, source_column, code_column, label_column) -> pl.DataFrame` - Replaces codes with labels using a lookup table
- `filter_data(df, column, values) -> pl.DataFrame` - Filters rows where column value is in the given set (keep only)
- `exclude_values(df, column, values) -> pl.DataFrame` - Excludes rows where column value is in the given set (remove)
- `drop_columns(df, columns) -> pl.DataFrame` - Drops specified columns from the DataFrame

**unpivot_data Modes:**

The function supports two mutually exclusive modes for specifying columns:

1. **Specify ID columns** (`id_columns`): All other columns become value columns
2. **Specify value column range** (`value_columns_start`, optionally `value_columns_end`): All other columns become ID columns

If `value_columns_end` is omitted, defaults to the last column (common case for time-series data).

### src/graphs/ (Package) - Infrastructure Layer

Export and rendering infrastructure with pluggable backends. This layer is responsible for taking already-processed DataFrames and rendering them to various output formats. It contains no business logic - only visualization and export concerns.

**Key Components:**

- `GraphRenderer` (Protocol) - Abstract interface defining the contract for renderers
- `PlotlyRenderer` - Concrete implementation using Plotly + NetworkX
- `get_renderer(name: str)` - Factory function to instantiate renderers
- `register_renderer(name: str, cls)` - Register custom renderer implementations
- `ChartType` - Enum: BAR, LINE, SCATTER, HISTOGRAM, PIE
- `ExportFormat` - Enum: HTML, PNG, PDF, SVG

**GraphRenderer Protocol Methods:**

```python
def create_chart(df, chart_type, x, y, title, color, facet_column, **kwargs) -> FigureResult
def create_network(df, source, target, weight, title, layout, **kwargs) -> FigureResult
def export(figure, filepath, export_format) -> None
def to_html(figure) -> str
```

**Faceted Charts:**

When `facet_column` is provided, `create_chart` generates an interactive chart with a dropdown menu to switch between facet values. This is useful for comparing the same chart across different groups (e.g., countries, years).

### src/cli.py

Terminal interface using Typer framework with Rich for formatting.

**Commands:**

- `compare FILE1 FILE2 --key KEY` - Compare two datasets, outputs a Rich table with diff columns highlighted in red
- `chart FILE --type TYPE --x COL --y COL [--output FILE] [--color COL] [--renderer NAME]` - Create statistical charts (bar, line, scatter, histogram, pie)
- `network FILE --source COL --target COL [--output FILE] [--weight COL] [--layout ALGO]` - Create network graphs from edge list data
- `renderers` - List available graph renderer backends

**Chart Command - Unpivot Options:**

The `chart` command supports on-the-fly unpivoting for wide-format data:

| Option          | Description                                                     |
| --------------- | --------------------------------------------------------------- |
| `--id-cols`     | Comma-separated identifier columns (rest become values)         |
| `--value-start` | Start index for value columns (0-based, rest become IDs)        |
| `--value-end`   | End index for value columns (optional, defaults to last column) |
| `--var-name`    | Name for the unpivoted variable column (default: "variable")    |
| `--value-name`  | Name for the unpivoted value column (default: "value")          |

Use either `--id-cols` OR `--value-start` (mutually exclusive modes).

**Chart Command - Lookup Options:**

| Option               | Description                            |
| -------------------- | -------------------------------------- |
| `--lookup`           | Path to lookup/mapping CSV file        |
| `--lookup-column`    | Column in main data to apply lookup to |
| `--lookup-code-col`  | Code column name in lookup file        |
| `--lookup-label-col` | Label column name in lookup file       |

**Chart Command - Filter Options:**

| Option           | Description                                                     |
| ---------------- | --------------------------------------------------------------- |
| `--filter`       | Filter expression as `COL:VAL1,VAL2,...` (keep only these rows) |
| `--exclude`      | Exclude expression as `COL:VAL1,VAL2,...` (remove these rows)   |
| `--drop-columns` | Comma-separated column names to ignore/drop entirely            |

`--filter` and `--exclude` can be used multiple times for different columns.

**Chart Command - Facet Options:**

| Option    | Description                                       |
| --------- | ------------------------------------------------- |
| `--facet` | Column for creating interactive dropdown selector |

### src/web.py

Streamlit-based web GUI running on port 8501.

**Features:**

- **Compare Tab**: Dual file upload, configurable join key, diff visualization
- **Visualize Tab**: Statistical charts with column selectors, chart type picker, unpivot support for wide-format data
- **Network Tab**: Network graph visualization from edge lists
- Sidebar renderer selector (extensible for future backends)
- Interactive Plotly charts with download buttons (HTML export)

**Visualize Tab - Unpivot Mode:**

Enable "Unpivot wide-format data" checkbox to transform columns into rows before charting. Supports two modes:

- Specify identifier columns (multi-select)
- Specify value column start index (with optional custom end)

**Visualize Tab - Lookup Mapping:**

Expand the "Lookup Mapping" section to replace codes with labels from a second file:

- Upload a lookup CSV file with code-to-label mappings
- Select the column to replace in main data
- Select the code and label columns in the lookup file
- Click "Apply Lookup" to transform

**Visualize Tab - Filter Data:**

Expand the "Filter Data (keep values)" section to keep only specific values:

- Select a column to filter on
- Choose values to keep (multi-select)
- Click "Apply Filter" to filter

**Visualize Tab - Exclude Row Values:**

Expand the "Exclude Row Values" section to remove rows with specific values:

- Select a column to filter on
- Choose row values to remove (multi-select)
- Click "Apply Exclusion" to remove matching rows

**Visualize Tab - Drop Columns:**

Expand the "Drop Columns" section to ignore entire columns:

- Select columns to drop (e.g., "Total", "Subtotal")
- Click "Drop Columns" to remove them from the data

**Visualize Tab - Faceted Charts:**

Select a "Facet By" column to create an interactive chart with a dropdown selector to switch between groups (e.g., different countries or years).

## Running the Application

**Prerequisites:** Only Podman (or Docker) required. No local Python installation needed.

### CLI Mode

```bash
cd viz-tool

# Compare datasets
podman compose run --rm cli compare data/sales_jan.csv data/sales_feb.csv --key id

# Create a bar chart (HTML - interactive)
podman compose run --rm cli chart data/sales_jan.csv --type bar --x region --y amount -o data/chart.html

# Create a scatter plot (PNG - static)
podman compose run --rm cli chart data/sales_jan.csv --type scatter --x id --y amount -o data/scatter.png

# Create a network graph
podman compose run --rm cli network data/edges.csv --source from --target to -o data/network.html

# List available renderers
podman compose run --rm cli renderers

# Unpivot wide-format data (Mode 1: specify ID columns)
podman compose run --rm cli chart data/demography.csv --type line \
  --id-cols "Country Name,Country Code" \
  --var-name Year --value-name Population \
  --x Year --y Population --color "Country Name" \
  -o data/population.html

# Unpivot wide-format data (Mode 2: specify value column start index)
podman compose run --rm cli chart data/demography.csv --type line \
  --value-start 4 \
  --var-name Year --value-name Population \
  --x Year --y Population --color "Country Name" \
  -o data/population.html

# Apply lookup mapping (replace codes with labels)
podman compose run --rm cli chart data/expenditure.csv --type pie \
  --lookup data/codes.csv --lookup-column "Expenditure Code" \
  --lookup-code-col code --lookup-label-col label \
  --x "Expenditure Code" --y "OBS value" \
  -o data/spending.html

# Filter data by specific values (keep only these)
podman compose run --rm cli chart data/expenditure.csv --type bar \
  --filter "Country:BG,DE,DK" --filter "Year:2020" \
  --x "Expenditure Code" --y "OBS value" \
  -o data/filtered.html

# Exclude specific row values (remove rows where Category is "Total")
podman compose run --rm cli chart data/expenditure.csv --type pie \
  --exclude "Expenditure Code:Total,Unknown" \
  --x "Expenditure Code" --y "OBS value" \
  -o data/no_total.html

# Drop entire columns (ignore "Total" column from the data)
podman compose run --rm cli chart data/expenditure.csv --type bar \
  --drop-columns "Total,Subtotal" \
  --x "Expenditure Code" --y "OBS value" \
  -o data/no_total_column.html

# Create faceted chart with dropdown selector
podman compose run --rm cli chart data/expenditure.csv --type pie \
  --filter "Year:2020" --facet Country \
  --x "Expenditure Code" --y "OBS value" \
  -o data/by_country.html
```

### GUI Mode

```bash
cd viz-tool
podman compose up gui
# Open http://localhost:8501
```

### Development (Live Reload)

Both services mount `./src` as a volume, so code changes are reflected immediately:

- CLI: Just re-run the command
- GUI: Click "Rerun" in the Streamlit interface

## Container Configuration

### Dockerfile

- Base image: `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` (uv pre-installed)
- **Chromium** installed for Kaleido static image export (PNG, PDF, SVG)
- `PYTHONPATH=/app` set for module discovery
- `UV_COMPILE_BYTECODE=1` for faster startup
- Dependencies installed via `uv pip install --system -r pyproject.toml`

### compose.yaml Services

- **gui**: Streamlit on port 8501 with live reload volumes
- **cli**: Python entrypoint with data volume mounts

**Note:** Export files to `data/` directory to persist them (mounted volume).

## Data Formats

### Tabular Data (Charts & Comparison)

Supports CSV, JSON, and Parquet files:

```csv
id,amount,region
1,100,US
2,150,EU
```

### Edge List Data (Network Graphs)

Network graphs expect edge list format with source and target columns:

```csv
source,target,weight
A,B,1
B,C,2
A,C,3
```

### Wide-Format Data (Unpivot Support)

Wide-format data has values spread across columns (e.g., time series with years as columns):

```csv
Country Name,Country Code,Series Name,Series Code,2013 [YR2013],2014 [YR2014],2015 [YR2015]
Bulgaria,BGR,"Population, total",SP.POP.TOTL,7160005,7073572,6984225
Hungary,HUN,"Population, total",SP.POP.TOTL,9872734,9833038,9797755
```

Use the unpivot feature to transform this into long format for visualization:

| Country Name | Year          | Population |
| ------------ | ------------- | ---------- |
| Bulgaria     | 2013 [YR2013] | 7160005    |
| Bulgaria     | 2014 [YR2014] | 7073572    |
| Hungary      | 2013 [YR2013] | 9872734    |

## Code Style Guidelines

- Python 3.12+ required
- Type hints on all function signatures
- JSDoc-style docstrings for public functions
- Polars preferred over pandas for data operations
- Protocol pattern for abstractions (enables swappable implementations)

**Layer Responsibilities:**

- **Presentation** (`cli.py`, `web.py`) - User interaction, input validation, output formatting
- **Business Logic** (`engine.py`) - Data processing, transformations, calculations
- **Infrastructure** (`graphs/`) - Rendering and export only, no business logic

## Extending the Tool

### Adding a New Graph Renderer

1. Create `src/graphs/my_renderer.py` implementing the `GraphRenderer` protocol
2. Register in factory or at runtime:

```python
from src.graphs import register_renderer
from src.graphs.my_renderer import MyRenderer

register_renderer("my_renderer", MyRenderer)
```

3. Use via CLI: `--renderer my_renderer`
4. No changes needed to CLI or web code

### Adding New Chart Types

1. Add value to `ChartType` enum in `src/graphs/types.py`
2. Implement the chart creation in each renderer (e.g., `PlotlyRenderer`)
3. Update CLI `ChartTypeOption` enum in `cli.py`

### Adding New Data Processing Functions

1. Add function to `src/engine.py`
2. Import and use in both `cli.py` and `web.py`
3. Keep presentation logic separate from data logic

### Adding New CLI Commands

1. Add new function decorated with `@app.command()` in `cli.py`
2. Use Rich for terminal output formatting

### Adding New GUI Features

1. Modify `src/web.py`
2. Use Streamlit components (st.\*, st.plotly_chart, etc.)
3. Convert Polars DataFrames to pandas for Streamlit rendering: `df.to_pandas()`
