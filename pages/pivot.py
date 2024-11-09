import streamlit as st
from tools import filter, snowflake
from streamlit_tree_select import tree_select
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, ColumnsAutoSizeMode
from styles.formatting import format_numbers, conditional_formatting

def build_filters():
    columns = ['LBU_GROUP', 'LBU_CODE', 'FUND_TYPE', 'FUND_CODE', 'MANAGER', 'ACCOUNT_CODE', 'BBG_ASSET_TYPE', 'FWD_ASSET_TYPE', 'L1_ASSET_TYPE', 'L2_ASSET_TYPE', 'L3_ASSET_TYPE', 'L4_ASSET_TYPE', 'FINAL_RATING', 'COUNTRY_REPORT', 'ISSUER', 'CAST_PARENT_NAME', 'INDUSTRY', 'INDUSTRY_SECTOR', 'INDUSTRY_GROUP', 'IS_HGA']
    security_identifiers = ['SECURITY_NAME', 'BBGID_V2', 'ISIN', 'FIGI']
    values = ['NET_MV', 'CLEAN_MV_USD']#, 'WARF', 'YTM', 'CREDIT_SPREAD_BP', 'DV01_000', 'CONVEXITY', 'CS01_000', 'DURATION', 'GIECA_CS_STRESSED_VALUE_1_IN_200', 'GIECA_EQUITY_STRESSED_VALUE_1_IN_200', 'GIECA_IR_STRESSED_VALUE_1_IN_200']

    with st.expander("Filters"):
        filter.build_date_filter(True)
        filter.build_lbu_tree()
        filter.build_vanilla_tree('Columns', columns, columns, checked=False)
        filter.build_vanilla_tree('Values', values, values, checked=False)

    selected_columns = st.session_state['tree_selected_columns']
    #selected_values = st.session_state['tree_selected_values']

    if len(selected_columns['columns_tree']['checked']) > 4:
        st.error('Please do not select more than 4 columns! If required, please pivot using Funnelweb instead...')

def query_data():
    run = False

    if st.button('Load'):
        run = True

    if not run:
        return

    height = 630

    columns = st.session_state['tree_selected_columns']['columns_tree']['checked']
    values = st.session_state['tree_selected_values']['values_tree']['checked']
    current_date = st.session_state['Valuation Date']
    lbu_selection = st.session_state['lbu_tree_data']
    fund_codes = str(lbu_selection).replace("[", "").replace("]", "")

    if len(columns) == 0:
        st.error('Please select at least 1 column!')
        return

    if len(values) == 0:
        st.error('Please select at least 1 value!')
        return

    query = f'SELECT {", ".join(columns)}, {", ".join(values)} FROM funnel.funnelweb WHERE fund_code IN ({fund_codes}) AND closing_date = \'{current_date}\';'
    #st.write(query)

    with st.spinner('Fetching your requested data...'):
        df = snowflake.query(query)
    df = df.groupby(columns).agg({key: 'sum' for key in values}).reset_index()

    custom_css = {
        ".ag-cell": {"font-size": "90%"},
        ".ag-theme-streamlit": {"--ag-cell-horizontal-border": "none"},
        ".ag-header-cell": {"color": "white", "background-color": "rgb(232,119,34)", "--ag-header-cell-hover-background-color": "rgb(246,179,128)"},
        ".ag-header-cell-resize": {"display": "none"},
        ".ag-header-group-cell.ag-header-group-cell-with-group": {"display": "flex", "justify-content": "flex-end"},
        ".ag-header-group-cell.ag-header-group-cell-with-group[aria-expanded='true']": {"display": "flex", "justify-content": "flex-start"},
    }

    gb = GridOptionsBuilder.from_dataframe(df)

    gb.configure_default_column(resizable=True, filterable=True, editable=False, flex=1, minWidth=170)

    gb.configure_grid_options(pivotMode=True, autoGroupColumnDef={'cellRendererParams': { 'suppressCount': 'true'}, 'pinned': 'left'}, groupDefaultExpanded=-1, suppressAggFuncInHeader=True, pivotDefaultExpanded=-1, pivotRowTotals='left', groupIncludeTotalFooter=True)

    for column in columns:
        gb.configure_column(column, pinned="left", rowGroup=True)
    
    for column in values:
        gb.configure_column(column, aggFunc='sum')


    for column in values:
        gb.configure_column(column, aggFunc='sum', header_name=column, valueFormatter=format_numbers())

    go = gb.build()
    
    AgGrid(df, gridOptions=go, height=height, theme='streamlit', allow_unsafe_jscode=True, custom_css=custom_css)

build_filters()
query_data()