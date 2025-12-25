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


def apply_lookup(
    df: pl.DataFrame,
    lookup_df: pl.DataFrame,
    source_column: str,
    code_column: str,
    label_column: str,
) -> pl.DataFrame:
    """
    Replace codes with labels using a lookup table.

    Joins the main DataFrame with a lookup DataFrame to replace code values
    with their corresponding labels. The original column is replaced with
    the label values while keeping the original column name.

    Args:
        df: Source DataFrame containing codes to be replaced.
        lookup_df: Lookup DataFrame containing code-to-label mappings.
        source_column: Column name in df containing codes to replace.
        code_column: Column name in lookup_df containing the codes.
        label_column: Column name in lookup_df containing the labels.

    Returns:
        A DataFrame with codes replaced by labels in the source column.

    Raises:
        ValueError: If any of the specified columns do not exist.
    """
    if source_column not in df.columns:
        raise ValueError(f"Source column '{source_column}' not found in data")
    if code_column not in lookup_df.columns:
        raise ValueError(f"Code column '{code_column}' not found in lookup")
    if label_column not in lookup_df.columns:
        raise ValueError(f"Label column '{label_column}' not found in lookup")
    lookup_subset = lookup_df.select([code_column, label_column]).unique()
    result = df.join(
        lookup_subset,
        left_on=source_column,
        right_on=code_column,
        how="left",
    )
    result = result.with_columns(
        pl.when(pl.col(label_column).is_not_null())
        .then(pl.col(label_column))
        .otherwise(pl.col(source_column))
        .alias(source_column)
    )
    columns_to_drop = [label_column]
    if code_column != source_column and code_column in result.columns:
        columns_to_drop.append(code_column)
    return result.drop(columns_to_drop)


def filter_data(
    df: pl.DataFrame,
    column: str,
    values: list[str],
) -> pl.DataFrame:
    """
    Filter DataFrame rows by column values.

    Keeps only rows where the specified column's value is in the given set
    of allowed values.

    Args:
        df: Source DataFrame to filter.
        column: Column name to filter on.
        values: List of values to keep.

    Returns:
        A filtered DataFrame containing only matching rows.

    Raises:
        ValueError: If the column does not exist in the DataFrame.
    """
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found in data")
    return df.filter(pl.col(column).cast(pl.Utf8).is_in(values))


def exclude_values(
    df: pl.DataFrame,
    column: str,
    values: list[str],
) -> pl.DataFrame:
    """
    Exclude rows with specific column values from DataFrame.

    Removes rows where the specified column's value is in the given set
    of values to exclude.

    Args:
        df: Source DataFrame to filter.
        column: Column name to filter on.
        values: List of values to exclude.

    Returns:
        A filtered DataFrame with matching rows removed.

    Raises:
        ValueError: If the column does not exist in the DataFrame.
    """
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found in data")
    return df.filter(~pl.col(column).cast(pl.Utf8).is_in(values))


def drop_columns(
    df: pl.DataFrame,
    columns: list[str],
) -> pl.DataFrame:
    """
    Drop specified columns from DataFrame.

    Removes entire columns from the DataFrame, useful for ignoring
    columns like "Total" or metadata columns when visualizing.

    Args:
        df: Source DataFrame.
        columns: List of column names to drop.

    Returns:
        A DataFrame with specified columns removed.

    Raises:
        ValueError: If any column does not exist in the DataFrame.
    """
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"Columns not found: {', '.join(missing)}")
    return df.drop(columns)

