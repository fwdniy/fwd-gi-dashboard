import streamlit as st
from streamlit import session_state as ss

@st.cache_data(show_spinner=False)
def get_curves():
    sql = (
        "SELECT valuation_date, curve, fx, tenor, rate "
        "FROM supp.curve_rates r, supp.curve_name c "
        "WHERE valuation_date >= '2021-12-31' "
        "AND r.curve = c.name "
        "ORDER BY valuation_date, curve, tenor;"
    )

    df = ss.snowflake.query(sql)

    return df