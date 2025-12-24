"""Core data processing engine using Polars."""

from io import BytesIO
from typing import BinaryIO

import polars as pl


def load_data(source: str | BinaryIO) -> pl.DataFrame:
    """
    Reads CSV, JSON, or Parquet automatically based on file extension.

    Supports both file paths (for CLI) and file-like objects (for Streamlit).
    
    Args:
        source: Path to the data file or a file-like object with a .name attribute.
        
    Returns:
        A Polars DataFrame containing the loaded data.
        
    Raises:
        ValueError: If the file format is unsupported.
    """
    if isinstance(source, str):
        filename = source
        file_source = source
    else:
        filename = getattr(source, "name", "")
        file_source = BytesIO(source.read())
    filename_lower = filename.lower()
    if filename_lower.endswith(".csv"):
        return pl.read_csv(file_source)
    elif filename_lower.endswith(".json"):
        return pl.read_json(file_source)
    elif filename_lower.endswith(".parquet"):
        return pl.read_parquet(file_source)
    else:
        raise ValueError(f"Unsupported format: {filename}")


def compare_datasets(df_a: pl.DataFrame, df_b: pl.DataFrame, join_key: str) -> pl.DataFrame:
    """
    Creates a complex comparison table by joining two datasets.
    
    Joins two datasets on the specified key and calculates differences
    for all numeric columns.
    
    Args:
        df_a: First DataFrame to compare.
        df_b: Second DataFrame to compare.
        join_key: Column name to join on.
        
    Returns:
        A DataFrame containing joined data with difference columns.
    """
    # suffix="_b" distinguishes the second dataset columns
    joined = df_a.join(df_b, on=join_key, how="outer", suffix="_b")
    # Find numeric columns to calculate diffs
    numeric_cols = [
        col for col in df_a.columns
        if col in df_b.columns and df_a[col].dtype in (pl.Int64, pl.Float64)
        and col != join_key
    ]
    # Add difference columns dynamically
    expressions = [pl.all()]
    for col in numeric_cols:
        # Diff = Value A - Value B
        diff_expr = (pl.col(col) - pl.col(f"{col}_b")).alias(f"{col}_diff")
        expressions.append(diff_expr)
    return joined.select(expressions)


def unpivot_data(
    df: pl.DataFrame,
    id_columns: list[str] | None = None,
    value_columns_start: int | None = None,
    value_columns_end: int | None = None,
    variable_name: str = "variable",
    value_name: str = "value",
) -> pl.DataFrame:
    """
    Transform wide-format data to long format by unpivoting columns.

    Converts columns into rows, creating two new columns: one for the original
    column names (variable) and one for the values.

    Supports two mutually exclusive modes:
    - Specify id_columns: remaining columns become value columns
    - Specify value_columns_start (and optionally end): remaining columns become id columns

    Args:
        df: Source DataFrame in wide format.
        id_columns: Column names to keep as identifiers. If provided, all other
            columns are treated as value columns.
        value_columns_start: Start index for value columns (0-based, inclusive).
        value_columns_end: End index for value columns (exclusive). If None,
            defaults to the last column.
        variable_name: Name for the new column containing original column names.
        value_name: Name for the new column containing the values.

    Returns:
        A DataFrame in long format with unpivoted data.

    Raises:
        ValueError: If neither id_columns nor value_columns_start is provided,
            or if column indices are invalid.
    """
    all_columns = df.columns
    has_id_cols = id_columns is not None and len(id_columns) > 0
    has_value_start = value_columns_start is not None
    if not has_id_cols and not has_value_start:
        raise ValueError(
            "Must provide either id_columns or value_columns_start"
        )
    if has_value_start:
        if value_columns_end is None:
            value_columns_end = len(all_columns)
        if value_columns_start < 0 or value_columns_end > len(all_columns):
            raise ValueError(
                f"Column indices out of range. DataFrame has {len(all_columns)} columns."
            )
        if value_columns_start >= value_columns_end:
            raise ValueError("value_columns_start must be less than value_columns_end")
        value_columns = all_columns[value_columns_start:value_columns_end]
        if not has_id_cols:
            id_columns = [col for col in all_columns if col not in value_columns]
    else:
        value_columns = [col for col in all_columns if col not in id_columns]
    return df.unpivot(
        on=value_columns,
        index=id_columns,
        variable_name=variable_name,
        value_name=value_name,
    )

