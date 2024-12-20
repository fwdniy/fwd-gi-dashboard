import pandas as pd
import streamlit as st
from tools.snowflake.snowflake import get_schema, convert_columns
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, ColumnsAutoSizeMode
import streamlit.components as components
from tools import filter, snowflake
from styles.formatting import format_numbers, conditional_formatting

with st.expander("Filters"):
    filter.build_date_filter()
    filter.build_lbu_tree()
    filter.build_currency_filter()
    filter.build_level_filter()

current_date = st.session_state['Valuation Date']
compare_date = st.session_state['Comparison Date']
lbu_selection = st.session_state['lbu_tree_data']

fund_codes = str(lbu_selection).replace("[", "").replace("]", "")

if fund_codes == '':
    st.write('No funds selected!')
    st.stop()

level = st.session_state['level']

with st.spinner('Loading your data...'):
    #region Prepare Data

    #region Get Data

    if 'asset_allocation_df' in st.session_state:
        df = st.session_state['asset_allocation_df']
    else:
        query = f"SELECT * FROM asset_allocation_new"
        conn = st.session_state["conn"]
        df = st.session_state['asset_allocation_df'] = snowflake.query(query)
        df['LBU_FILTER'] = False

    #endregion

    #region Filter Data
    
    df = df[df['FUND_CODE'].isin(lbu_selection)]   
    df_current = df[(df['CLOSING_DATE'].dt.date == current_date) & (df['LEVEL'] <= level)]
    df_compare = df[(df['CLOSING_DATE'].dt.date == compare_date) & (df['LEVEL'] <= level)]
    
    #endregion

    #region Merge Data

    group_columns = ['OUTPUT_ORDER', 'LEVEL', 'ASSET_TYPE']
    other_columns = [col for col in df_current.columns if col not in group_columns and not pd.api.types.is_datetime64_any_dtype(df_current[col]) and not pd.api.types.is_string_dtype(df_current[col])]
    
    agg_dict = {col: 'sum' for col in other_columns}
    df_current = df_current.groupby(group_columns).agg(agg_dict).reset_index()

    df_compare = df_compare[['OUTPUT_ORDER', 'LEVEL', 'ASSET_TYPE', 'Clean MV']]
    df_compare = df_compare.groupby(['OUTPUT_ORDER', 'LEVEL', 'ASSET_TYPE']).agg({'Clean MV': 'sum'}).reset_index()
    df_compare.rename(columns={'Clean MV': 'Previous Clean MV'}, inplace=True)

    df_grouped = pd.merge(df_current, df_compare, on=['OUTPUT_ORDER', 'LEVEL', 'ASSET_TYPE'], how='outer').fillna(0)

    #endregion

    #region Add % Columns

    df_grouped['SAA(%)'] = df_grouped['SAA(%)'] / df_grouped[df_grouped['OUTPUT_ORDER'] == 0]['SAA(%)'][0] * 100
    df_grouped['Clean MV %'] = (df_grouped['Clean MV'] / df_grouped['Clean MV'].max()) * 100
    df_grouped['Previous Clean MV %'] = (df_grouped['Previous Clean MV'] / df_grouped['Previous Clean MV'].max()) * 100
    df_grouped['MV Δ'] = df_grouped['Clean MV'] - df_grouped['Previous Clean MV']
    df_grouped['MV Δ %'] = df_grouped['Clean MV %'] - df_grouped['Previous Clean MV %']
    df_grouped['SAA Δ %'] = df_grouped['Clean MV %'] - df_grouped['SAA(%)']

    #endregion

    #region Apply FX Rate

    df_grouped['Previous Clean MV'] = df_grouped['Previous Clean MV'] * float(st.session_state['fx_rate_compare'])
    
    fx_rate_columns = ['Clean MV', 'Clean MV (Duration)', 'DV01 (mns)', 'DV50 (mns)', 'DVn50 (mns)', 'CS01 (mns)', 'Clean MV (Credits)', 'DV01 (Credits) (mns)', 'CS01 (Credits) (mns)', 'Clean MV (WARF)', 'Clean MV (1 in 200)', 'VAL01 (mns)']

    for column in fx_rate_columns:
        df_grouped[column] = df_grouped[column] * float(st.session_state['fx_rate_current'])
    
    #endregion

    #region Calculate Weighted Averages

    weighted_columns = {"Duration (Sumproduct)": "Clean MV (Duration)", "Convexity (Sumproduct)": "Clean MV (Duration)", "YTM (Credits) (Sumproduct)": "Clean MV (Credits)", "Credit Spread (Credits) (Sumproduct)": "Clean MV (Credits)", "Duration (Credits) (Sumproduct)": "Clean MV (Credits)", "Convexity (Credits) (Sumproduct)": "Clean MV (Credits)", "WARF (Sumproduct)": "Clean MV (WARF)", "Time Until Maturity (Sumproduct)": "Clean MV (Duration)" }

    for key, value in weighted_columns.items():
        df_grouped[key.replace(" (Sumproduct)", "")] = (df_grouped[key] / df_grouped[value]).fillna(0)

    #endregion

    #region Move Columns

    cols = df_grouped.columns.tolist()
    cols.insert(3, cols.pop(cols.index('Previous Clean MV')))
    cols.insert(4, cols.pop(cols.index('Previous Clean MV %')))
    cols.insert(5, cols.pop(cols.index('MV Δ')))
    cols.insert(6, cols.pop(cols.index('MV Δ %')))
    cols.insert(8, cols.pop(cols.index('Clean MV %')))
    cols.insert(10, cols.pop(cols.index('SAA Δ %')))

    for key in weighted_columns.keys():
        cols.insert(cols.index(key), cols.pop(cols.index(key.replace(" (Sumproduct)", ""))))
        cols.pop(cols.index(key))
    
    df_grouped = df_grouped[cols]

    #endregion

    df_grouped = df_grouped.sort_values(by='OUTPUT_ORDER', ascending=True)
    #endregion

    #region Build Grid

    #region Prepare Column Data

    gb = GridOptionsBuilder.from_dataframe(df_grouped)

    gb.configure_default_column(
        resizable=True,
        filterable=True,
        editable=False,
    )

    gb.configure_column(field='OUTPUT_ORDER', header_name="Order", pinned="left", filterable=False)
    gb.configure_column(field='LEVEL', header_name="Level", pinned="left")
    gb.configure_column(field='ASSET_TYPE', header_name="Asset Type", cellStyle={'border-right': '1px solid rgb(232,119,34)'}, pinned="left", filterable=True)

    ignore_columns = ['OUTPUT_ORDER', 'LEVEL', 'ASSET_TYPE']
    conditional_formatting_columns = ['MV Δ %', 'SAA Δ %']

    for column in df_grouped.columns.tolist():
        if column in ignore_columns:
            continue
        elif column in conditional_formatting_columns:
            gb.configure_column(field=column, valueFormatter=format_numbers(), cellStyle=conditional_formatting())
        else:
            gb.configure_column(field=column, valueFormatter=format_numbers())
    
    go = gb.build()

    #endregion

    #region Autofit

    min_height = 10
    asset_types = df_grouped.shape[0] if df_grouped.shape[0] > min_height else min_height
    height = 10 + 30 * asset_types
    column_defs = go["columnDefs"]

    for col_def in column_defs:
        col_name = col_def["field"]
        max_len = int(df_grouped[col_name].astype(str).str.len().max())
        col_def["width"] = max_len

    #endregion

    custom_css = {
        ".ag-cell": {"font-size": "90%"},
        ".ag-theme-streamlit": {"--ag-cell-horizontal-border": "none"},
        ".ag-header-cell": {"color": "white", "background-color": "rgb(232,119,34)", "--ag-header-cell-hover-background-color": "rgb(246,179,128)"},
        ".ag-header-cell-resize": {"display": "none"}
    }

    AgGrid(df_grouped, height=height, gridOptions=go, theme='streamlit', allow_unsafe_jscode=True, custom_css=custom_css)

    #endregion

    

st.toast('Data loaded!', icon="✅")