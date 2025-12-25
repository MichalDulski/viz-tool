"""Web GUI using Streamlit."""

import streamlit as st

from src.engine import apply_lookup, compare_datasets, drop_columns, exclude_values, filter_data, load_data, unpivot_data
from src.graphs import ChartType, get_renderer, list_renderers

st.set_page_config(layout="wide", page_title="Data Viz Tool")

st.title("📊 Data Visualization Tool")

# Sidebar for renderer selection
with st.sidebar:
    st.header("Settings")
    available_renderers = list_renderers()
    selected_renderer = st.selectbox(
        "Graph Renderer",
        options=available_renderers,
        index=0,
        help="Select the rendering backend for charts",
    )

# Main tabs
tab_compare, tab_visualize, tab_network = st.tabs(
    ["📈 Compare", "📊 Visualize", "🔗 Network"]
)

with tab_compare:
    st.header("Dataset Comparison")
    col1, col2 = st.columns(2)
    with col1:
        file_a = st.file_uploader(
            "Upload Dataset A", type=["csv", "json"], key="compare_a"
        )
    with col2:
        file_b = st.file_uploader(
            "Upload Dataset B", type=["csv", "json"], key="compare_b"
        )
    join_key = st.text_input("Join Key Column Name", value="id")
    if file_a and file_b:
        try:
            df1 = load_data(file_a)
            df2 = load_data(file_b)
        except Exception as e:
            st.error(f"Error loading files: {e}")
            st.stop()
        st.subheader("Comparison Result")
        try:
            result = compare_datasets(df1, df2, join_key)
            st.data_editor(
                result.to_pandas(),
                use_container_width=True,
                num_rows="dynamic",
            )
            numeric_cols = [c for c in result.columns if "diff" in c]
            if numeric_cols:
                st.bar_chart(result.to_pandas(), x=join_key, y=numeric_cols)
        except Exception as e:
            st.error(f"Error during comparison: {e}")

with tab_visualize:
    st.header("Chart Visualization")
    chart_file = st.file_uploader(
        "Upload Data File", type=["csv", "json"], key="chart_file"
    )
    if chart_file:
        try:
            df_original = load_data(chart_file)
        except Exception as e:
            st.error(f"Error loading file: {e}")
            st.stop()
        st.subheader("Data Preview")
        st.dataframe(df_original.to_pandas().head(10), use_container_width=True)
        original_columns = list(df_original.columns)
        is_unpivot_enabled = st.checkbox(
            "Unpivot wide-format data",
            value=False,
            help="Transform columns into rows (e.g., for time series data spread across columns)",
        )
        df = df_original
        if is_unpivot_enabled:
            st.subheader("Unpivot Configuration")
            unpivot_mode = st.radio(
                "Unpivot Mode",
                options=["Specify ID columns", "Specify value column range"],
                horizontal=True,
                help="Choose how to specify which columns to unpivot",
            )
            id_columns_selected = None
            value_start_idx = None
            value_end_idx = None
            if unpivot_mode == "Specify ID columns":
                id_columns_selected = st.multiselect(
                    "Identifier Columns",
                    options=original_columns,
                    default=list(original_columns[:2]) if len(original_columns) >= 2 else list(original_columns),
                    help="Columns to keep as identifiers. All other columns become values.",
                )
            else:
                value_start_idx = st.number_input(
                    "Value Columns Start Index",
                    min_value=0,
                    max_value=len(original_columns) - 1,
                    value=min(4, len(original_columns) - 1),
                    help="Start index for value columns (0-based). All columns from this index onward become values.",
                )
                use_custom_end = st.checkbox(
                    "Specify custom end index",
                    value=False,
                    help="By default, all columns from start to end are included as values",
                )
                if use_custom_end:
                    value_end_idx = st.number_input(
                        "Value Columns End Index",
                        min_value=int(value_start_idx) + 1,
                        max_value=len(original_columns),
                        value=len(original_columns),
                        help="End index for value columns (exclusive)",
                    )
            name_col1, name_col2 = st.columns(2)
            with name_col1:
                var_name_input = st.text_input(
                    "Variable Column Name",
                    value="variable",
                    help="Name for the column containing original column names",
                )
            with name_col2:
                value_name_input = st.text_input(
                    "Value Column Name",
                    value="value",
                    help="Name for the column containing the values",
                )
            try:
                df = unpivot_data(
                    df=df_original,
                    id_columns=id_columns_selected if id_columns_selected else None,
                    value_columns_start=int(value_start_idx) if value_start_idx is not None else None,
                    value_columns_end=int(value_end_idx) if value_end_idx is not None else None,
                    variable_name=var_name_input,
                    value_name=value_name_input,
                )
                st.subheader("Unpivoted Data Preview")
                st.dataframe(df.to_pandas().head(10), use_container_width=True)
            except Exception as e:
                st.error(f"Error unpivoting data: {e}")
                df = df_original
        current_columns = list(df.columns)
        with st.expander("📋 Lookup Mapping (replace codes with labels)", expanded=False):
            lookup_file = st.file_uploader(
                "Upload Lookup File",
                type=["csv", "json"],
                key="lookup_file",
                help="CSV/JSON file containing code-to-label mappings",
            )
            if lookup_file:
                try:
                    lookup_df = load_data(lookup_file)
                    lookup_columns = list(lookup_df.columns)
                    st.dataframe(lookup_df.to_pandas().head(5), use_container_width=True)
                    lookup_col1, lookup_col2, lookup_col3 = st.columns(3)
                    with lookup_col1:
                        lookup_source_column = st.selectbox(
                            "Column to Replace",
                            options=current_columns,
                            index=0,
                            help="Column in main data containing codes to replace",
                            key="lookup_source",
                        )
                    with lookup_col2:
                        lookup_code_column = st.selectbox(
                            "Code Column (lookup)",
                            options=lookup_columns,
                            index=0,
                            help="Column in lookup file containing codes",
                            key="lookup_code",
                        )
                    with lookup_col3:
                        default_label_idx = 1 if len(lookup_columns) > 1 else 0
                        lookup_label_column = st.selectbox(
                            "Label Column (lookup)",
                            options=lookup_columns,
                            index=default_label_idx,
                            help="Column in lookup file containing labels",
                            key="lookup_label",
                        )
                    if st.button("Apply Lookup", key="apply_lookup"):
                        try:
                            df = apply_lookup(
                                df=df,
                                lookup_df=lookup_df,
                                source_column=lookup_source_column,
                                code_column=lookup_code_column,
                                label_column=lookup_label_column,
                            )
                            # Store the lookup mapping for filter display
                            lookup_mapping = dict(zip(
                                lookup_df[lookup_code_column].to_list(),
                                lookup_df[lookup_label_column].to_list()
                            ))
                            if "lookup_mappings" not in st.session_state:
                                st.session_state["lookup_mappings"] = {}
                            st.session_state["lookup_mappings"][lookup_source_column] = lookup_mapping

                            st.session_state["df_with_lookup"] = df
                            st.success("Lookup applied successfully!")
                            st.dataframe(df.to_pandas().head(10), use_container_width=True)
                        except Exception as e:
                            st.error(f"Error applying lookup: {e}")
                except Exception as e:
                    st.error(f"Error loading lookup file: {e}")
            if "df_with_lookup" in st.session_state:
                df = st.session_state["df_with_lookup"]
                current_columns = list(df.columns)
        with st.expander("🔍 Filter Data (keep values)", expanded=False):
            filter_column = st.selectbox(
                "Filter Column",
                options=current_columns,
                index=0,
                key="filter_column",
                help="Select column to filter on",
            )
            unique_values = df[filter_column].unique().to_list()
            unique_values_str = [str(v) for v in unique_values]

            # Check if this column has a lookup mapping
            lookup_mappings = st.session_state.get("lookup_mappings", {})
            if filter_column in lookup_mappings:
                # Create display options showing both code and label
                reverse_mapping = {v: k for k, v in lookup_mappings[filter_column].items()}
                display_options = []
                for value in unique_values_str:
                    original_code = reverse_mapping.get(value, value)
                    display_options.append(f"{original_code} - {value}")
                filter_display_options = display_options
                # Create mapping from display option back to actual value
                display_to_value = dict(zip(display_options, unique_values_str))
            else:
                filter_display_options = unique_values_str
                display_to_value = dict(zip(unique_values_str, unique_values_str))

            filter_values = st.multiselect(
                "Values to Keep",
                options=filter_display_options,
                default=[],
                help="Select values to keep (leave empty to keep all). Shows 'Code - Label' for lookup columns.",
                key="filter_values",
            )
            # Convert display options back to actual values for filtering
            actual_filter_values = [display_to_value[opt] for opt in filter_values]
            if st.button("Apply Filter", key="apply_filter") and actual_filter_values:
                try:
                    df = filter_data(df=df, column=filter_column, values=actual_filter_values)
                    st.session_state["df_filtered"] = df
                    st.success(f"Filtered to {len(df)} rows")
                    st.dataframe(df.to_pandas().head(10), use_container_width=True)
                except Exception as e:
                    st.error(f"Error filtering data: {e}")
            if "df_filtered" in st.session_state:
                df = st.session_state["df_filtered"]
                current_columns = list(df.columns)
        with st.expander("🚫 Exclude Row Values", expanded=False):
            exclude_column = st.selectbox(
                "Exclude Column",
                options=current_columns,
                index=0,
                key="exclude_column",
                help="Select column to exclude values from",
            )
            exclude_unique_values = df[exclude_column].unique().to_list()
            exclude_unique_values_str = [str(v) for v in exclude_unique_values]

            # Check if this column has a lookup mapping
            lookup_mappings = st.session_state.get("lookup_mappings", {})
            if exclude_column in lookup_mappings:
                # Create display options showing both code and label
                reverse_mapping = {v: k for k, v in lookup_mappings[exclude_column].items()}
                exclude_display_options = []
                for value in exclude_unique_values_str:
                    original_code = reverse_mapping.get(value, value)
                    exclude_display_options.append(f"{original_code} - {value}")
                exclude_display_to_value = dict(zip(exclude_display_options, exclude_unique_values_str))
            else:
                exclude_display_options = exclude_unique_values_str
                exclude_display_to_value = dict(zip(exclude_unique_values_str, exclude_unique_values_str))

            exclude_values_selected = st.multiselect(
                "Values to Exclude",
                options=exclude_display_options,
                default=[],
                help="Select row values to remove (e.g., 'Total', 'Unknown'). Shows 'Code - Label' for lookup columns.",
                key="exclude_values",
            )
            # Convert display options back to actual values for exclusion
            actual_exclude_values = [exclude_display_to_value[opt] for opt in exclude_values_selected]
            if st.button("Apply Exclusion", key="apply_exclude") and actual_exclude_values:
                try:
                    df = exclude_values(df=df, column=exclude_column, values=actual_exclude_values)
                    st.session_state["df_excluded"] = df
                    st.success(f"Excluded values, {len(df)} rows remaining")
                    st.dataframe(df.to_pandas().head(10), use_container_width=True)
                except Exception as e:
                    st.error(f"Error excluding values: {e}")
            if "df_excluded" in st.session_state:
                df = st.session_state["df_excluded"]
                current_columns = list(df.columns)
        with st.expander("🗑️ Drop Columns (ignore columns)", expanded=False):
            columns_to_drop = st.multiselect(
                "Columns to Drop",
                options=current_columns,
                default=[],
                help="Select columns to ignore/remove from the data (e.g., 'Total', 'Subtotal')",
                key="drop_columns",
            )
            if st.button("Drop Columns", key="apply_drop") and columns_to_drop:
                try:
                    df = drop_columns(df=df, columns=columns_to_drop)
                    st.session_state["df_dropped"] = df
                    st.success(f"Dropped {len(columns_to_drop)} column(s)")
                    st.dataframe(df.to_pandas().head(10), use_container_width=True)
                except Exception as e:
                    st.error(f"Error dropping columns: {e}")
            if "df_dropped" in st.session_state:
                df = st.session_state["df_dropped"]
                current_columns = list(df.columns)
        columns = current_columns
        col1, col2, col3 = st.columns(3)
        with col1:
            chart_type_str = st.selectbox(
                "Chart Type",
                options=["bar", "line", "scatter", "histogram", "pie"],
                index=0,
            )
        with col2:
            x_column = st.selectbox("X-Axis Column", options=columns, index=0)
        with col3:
            y_options = [c for c in columns if c != x_column]
            y_column = st.selectbox(
                "Y-Axis Column",
                options=y_options,
                index=0 if y_options else None,
            )
        col4, col5 = st.columns(2)
        with col4:
            color_column = st.selectbox(
                "Color By (optional)",
                options=["None"] + list(columns),
                index=0,
            )
        with col5:
            chart_title = st.text_input("Chart Title (optional)", value="")
        facet_columns = st.multiselect(
            "Facet By (dropdown selector)",
            options=columns,
            default=[],
            help="Select one or more columns for combined dropdown (e.g., Country | Year)",
        )
        if st.button("Generate Chart", type="primary"):
            try:
                renderer = get_renderer(selected_renderer)
                chart_type = ChartType(chart_type_str)
                fig = renderer.create_chart(
                    df=df,
                    chart_type=chart_type,
                    x=x_column,
                    y=y_column,
                    title=chart_title if chart_title else None,
                    color=color_column if color_column != "None" else None,
                    facet_columns=facet_columns if facet_columns else None,
                )
                st.plotly_chart(fig, use_container_width=True, height=600)
                html_content = renderer.to_html(fig)
                st.download_button(
                    label="Download as HTML",
                    data=html_content,
                    file_name="chart.html",
                    mime="text/html",
                )
            except Exception as e:
                st.error(f"Error creating chart: {e}")

with tab_network:
    st.header("Network Graph")
    network_file = st.file_uploader(
        "Upload Edge List File", type=["csv", "json"], key="network_file"
    )
    if network_file:
        try:
            df = load_data(network_file)
        except Exception as e:
            st.error(f"Error loading file: {e}")
            st.stop()
        st.subheader("Data Preview")
        st.dataframe(df.to_pandas().head(10), use_container_width=True)
        columns = list(df.columns)
        col1, col2, col3 = st.columns(3)
        with col1:
            source_col = st.selectbox(
                "Source Column", options=columns, index=0, key="net_source"
            )
        with col2:
            target_options = [c for c in columns if c != source_col]
            target_col = st.selectbox(
                "Target Column",
                options=target_options,
                index=0 if target_options else None,
                key="net_target",
            )
        with col3:
            weight_options = ["None"] + [
                c for c in columns if c not in [source_col, target_col]
            ]
            weight_col = st.selectbox(
                "Weight Column (optional)",
                options=weight_options,
                index=0,
                key="net_weight",
            )
        col4, col5 = st.columns(2)
        with col4:
            layout_option = st.selectbox(
                "Layout Algorithm",
                options=["spring", "circular", "kamada_kawai", "shell", "random"],
                index=0,
            )
        with col5:
            network_title = st.text_input(
                "Graph Title (optional)", value="", key="net_title"
            )
        if st.button("Generate Network Graph", type="primary"):
            try:
                renderer = get_renderer(selected_renderer)
                fig = renderer.create_network(
                    df=df,
                    source=source_col,
                    target=target_col,
                    weight=weight_col if weight_col != "None" else None,
                    title=network_title if network_title else None,
                    layout=layout_option,
                )
                st.plotly_chart(fig, use_container_width=True, height=600)
                html_content = renderer.to_html(fig)
                st.download_button(
                    label="Download as HTML",
                    data=html_content,
                    file_name="network.html",
                    mime="text/html",
                )
            except Exception as e:
                st.error(f"Error creating network graph: {e}")
