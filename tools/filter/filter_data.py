import streamlit as st
from tools import snowflake

def get_lbu_data():
    if "lbus_df" in st.session_state:
        return st.session_state["lbus_df"]
    
    st.session_state["lbus_df"] = lbus_df = snowflake.query(f"SELECT l.group_name, f.lbu, f.type, f.short_name, l.bloomberg_name, l.lbu_group FROM supp.fund AS f LEFT JOIN supp.lbu AS l ON l.name = f.lbu;", ['GROUP_NAME', 'LBU', 'TYPE', 'SHORT_NAME'])

    return lbus_df