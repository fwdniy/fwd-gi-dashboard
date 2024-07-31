import pandas as pd
import streamlit as st
from datetime import datetime
import numpy as np
from tools.snowflake.snowflake import get_schema, convert_columns
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, ColumnsAutoSizeMode
import streamlit.components as components
from tools import filter, snowflake

filter.build_date_filter()
filter.build_lbu_filter()
filter.build_currency_filter()
filter.build_level_filter()

current_date = st.session_state['Valuation Date']
compare_date = st.session_state['Comparison Date']
lbu_selection = st.session_state['LBU Group / LBU / Fund Type / Fund']
lbu_column_mapping = {"LBU_GROUP": "LBU_GROUP", "LBU": "LBU_CODE", "FUND_TYPE": "FUND_TYPE", "FUND": "FUND_CODE"}

with st.spinner('Loading your data...'):
    if 'asset_allocation_df' in st.session_state:
        df = st.session_state['asset_allocation_df']
    else:
        query = f"SELECT * FROM asset_allocation_new"
        conn = st.session_state["conn"]
        df = st.session_state['asset_allocation_df'] = snowflake.query(query)
        df['LBU_FILTER'] = False

    current_df = df[df['CLOSING_DATE'].dt.date == current_date]
    compare_df = df[df['CLOSING_DATE'].dt.date == compare_date]

    for selection in lbu_selection:
        selection.filter(current_df, lbu_column_mapping)
    
    current_df = current_df[current_df['LBU_FILTER'] == True]

    del current_df['LBU_FILTER']

    st.write(current_df)