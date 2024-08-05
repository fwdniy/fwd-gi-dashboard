import streamlit as st
import pandas as pd
from tools import filter, snowflake
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, ColumnsAutoSizeMode
from styles.formatting import format_numbers, conditional_formatting

filter.build_date_filter()

columns = ['LBU_GROUP', 'LBU_CODE', 'L1_ASSET_TYPE', 
               'L2_ASSET_TYPE', 'L3_ASSET_TYPE', 'L4_ASSET_TYPE', 
               'FINAL_RATING', 'INDUSTRY_SECTOR', 'INDUSTRY_GROUP', 
               'INDUSTRY', 'MANAGER']
    
default_columns = ['LBU_GROUP', 'L1_ASSET_TYPE']

values = ['CLEAN_MV_USD', 'NET_MV']

default_values = ['NET_MV']

display_names = {'CLOSING_DATE': 'Closing Date', 'LBU_GROUP': 'LBU Group', 'LBU_CODE': 'LBU Code', 'L1_ASSET_TYPE': 'L1 Asset Type', 
            'L2_ASSET_TYPE': 'L2 Asset Type', 'L3_ASSET_TYPE': 'L3 Asset Type', 'L4_ASSET_TYPE': 'L4 Asset Type', 
            'FINAL_RATING': 'Final Rating', 'INDUSTRY_SECTOR': 'Industry Sector', 'INDUSTRY_GROUP': 'Industry Group', 
            'INDUSTRY': 'Industry', 'MANAGER': 'Manager', 'CLEAN_MV_USD': 'Clean MV', 'NET_MV': 'Net MV'}

selected_columns = filter.build_custom_cascader([display_names[column] for column in columns], [display_names[column] for column in default_columns], 'Columns', 'breakdown_columns')
selected_values = filter.build_custom_cascader([display_names[column] for column in values], [display_names[column] for column in default_values], 'Values', 'breakdown_values')

column_string = ", ".join([key.lower() for key, value in display_names.items() if value in selected_columns])
value_string = "SUM(" + '), SUM('.join([key.lower() for key, value in display_names.items() if value in selected_values]) + ")"
query = f"SELECT closing_date, {column_string}, {value_string} FROM funnel.funnelweb GROUP BY closing_date, {column_string} ORDER BY closing_date, {column_string};"

if len(selected_columns) > 0 and len(selected_values) > 0:
    with st.spinner('Loading your data...'):
        if "breakdown_query" not in st.session_state:
            st.session_state["breakdown_query"] = query

        if query != st.session_state["breakdown_query"] or "breakdown_df" not in st.session_state:
            df = st.session_state["breakdown_df"] = snowflake.query(query)
        else:
            df = st.session_state["breakdown_df"]

        current_date = st.session_state['Valuation Date']
        compare_date = st.session_state['Comparison Date']

        df = df[(df['CLOSING_DATE'].dt.date == current_date) | (df['CLOSING_DATE'].dt.date == compare_date)]
        df['CLOSING_DATE'] = pd.to_datetime(df['CLOSING_DATE'], unit='s').dt.strftime('%Y-%m-%d')
        df.rename(columns=lambda x: x[4:-1] if x.startswith('SUM(') and x.endswith(')') else x, inplace=True)
        df.rename(columns=lambda x: display_names[x] if x in display_names.keys() else x, inplace=True)

        with st.expander("Column Filters"):
            for column in selected_columns:
                unique_values = list(df[column].unique())
                selected_column_values = filter.build_custom_cascader(unique_values, unique_values, column, f'breakdown_columns_{column}')
                
                if len(selected_column_values) == 0:
                    selected_column_values = unique_values
                    
                df = df[df[column].isin(selected_column_values)]
        
        st.write(query)

        gb = GridOptionsBuilder.from_dataframe(df)

        gb.configure_default_column(
            resizable=True,
            filterable=True,
            editable=False,
        )

        for column in selected_columns:
            gb.configure_column(field=column, rowGroup=True, hide=True)

        gb.configure_column(field=display_names['CLOSING_DATE'], pivot=True)

        for value in selected_values:
            gb.configure_column(field=value, aggFunc= "sum", valueFormatter=format_numbers(divide_by=1000000))

        go = gb.build()
        go['pivotMode'] = True
        go['groupDisplayType'] = 'multipleColumns'
        go['groupDefaultExpanded'] = 1
        go['grandTotalRow'] = True

        custom_css = {
            ".ag-cell": {"font-size": "90%"},
            ".ag-theme-streamlit": {"--ag-cell-horizontal-border": "none"},
            ".ag-header-cell": {"color": "white", "background-color": "rgb(232,119,34)", "--ag-header-cell-hover-background-color": "rgb(246,179,128)"},
            ".ag-header-group-cell": {"color": "white", "background-color": "rgb(232,119,34)", "--ag-header-cell-hover-background-color": "rgb(246,179,128)"},
            ".ag-header-viewport": {"color": "white", "background-color": "rgb(232,119,34)"},
            ".ag-header-cell-resize": {"display": "none"}
        }

        AgGrid(df, gridOptions=go, theme='streamlit', height=700, allow_unsafe_jscode=True, custom_css=custom_css)