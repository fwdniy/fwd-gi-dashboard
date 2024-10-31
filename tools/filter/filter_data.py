import streamlit as st
from tools import snowflake
from classes.lbu import LbuGroup
from datetime import datetime

def get_lbu_data():
    if "lbus_df" in st.session_state:
        return
    
    st.session_state["lbus_df"] = df = snowflake.query(f"SELECT l.group_name, f.lbu, f.type, f.short_name, l.bloomberg_name, l.lbu_group, f.sub_lbu FROM supp.fund AS f LEFT JOIN supp.lbu AS l ON l.name = f.lbu WHERE l.bloomberg_name <> 'LT' ORDER BY group_name, lbu, sub_lbu, type, short_name;", ['GROUP_NAME', 'LBU', 'TYPE', 'SHORT_NAME', 'SUB_LBU'])

    lbus = []
    for index, row in df.iterrows():
        lbu_group = row["LBU_GROUP"]
        index = next((i for i, group in enumerate(lbus) if group.lbu_group_code == lbu_group), -1)

        if index == -1:
            lbus.append(LbuGroup(row))
        else:
            lbus[index].add(row)

    st.session_state["lbus"] = lbus

def get_date_data():
    if "dates_df" in st.session_state:
        return

    st.session_state["dates_df"] = df = snowflake.query("SELECT DISTINCT closing_date FROM funnel.funnelweb WHERE closing_date >= '2021-12-31';", ['CLOSING_DATE'])
    st.session_state["max_date"] = datetime.date(max(df['CLOSING_DATE']))
    st.session_state["min_date"] = datetime.date(min(df['CLOSING_DATE']))
    st.session_state["default_compare_date"] = datetime.date(max(df[df['CLOSING_DATE'].dt.year == datetime.date(max(df["CLOSING_DATE"])).year - 1]['CLOSING_DATE']))

def get_currency_data():
    if "fxs_df" in st.session_state:
        return
    
    df = snowflake.query("SELECT valuation_date, fx, rate FROM funnel.fx_view;", ['VALUATION_DATE', 'FX'])
    df['VALUATION_DATE'] = df['VALUATION_DATE'].dt.date

    st.session_state["fxs_df"] = df