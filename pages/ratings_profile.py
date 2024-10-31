import streamlit as st
import pandas as pd
from tools import filter, snowflake
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, ColumnsAutoSizeMode
from styles.formatting import format_numbers, conditional_formatting
from streamlit_tree_select import tree_select

values = ['CLEAN_MV_USD', 'NET_MV']

default_values = ['NET_MV']

with st.expander("Filters"):
    filter.build_date_filter()
    filter.build_lbu_tree()