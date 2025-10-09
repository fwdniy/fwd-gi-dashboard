import streamlit as st
from streamlit import session_state as ss
import pandas as pd
from .grid import build_grid

def _build_query():
    fund_codes = ss.selected_funds
    fund_codes_string = "', '".join(fund_codes)
    current_date = ss.selected_date
    comparison_date = ss.selected_comparison_date

    sql = (
        f"SELECT CLOSING_DATE, LBU_CODE, ISSUER, L3_ASSET_TYPE, ACCOUNT_CODE, SECURITY_NAME, "
        f"NET_MV / 1000000 AS NET_MV "
        f"FROM funnel.funnelweb "
        f"WHERE bbg_asset_type = 'Repo Liability' "
        f"AND fund_code IN ('{fund_codes_string}') "
        f"AND closing_date IN ('{current_date}', '{comparison_date}') "
        f"ORDER BY closing_date DESC;"
    )
    
    return sql

def load_data():
    sql = _build_query()
    df = ss.snowflake.query(sql)

    # Format and group data
    df['CLOSING_DATE'] = pd.to_datetime(df['CLOSING_DATE']).dt.strftime('%Y-%m-%d')
    df = df.groupby(
        ['CLOSING_DATE', 'LBU_CODE', 'ISSUER', 'L3_ASSET_TYPE', 'ACCOUNT_CODE', 'SECURITY_NAME']
    ).sum().reset_index()

    # Split data into current and previous dates
    unique_dates = df['CLOSING_DATE'].unique()
    if len(unique_dates) < 2:
        st.warning("Insufficient data for comparison.")
        return df

    comparison_date, current_date = unique_dates[:2]
    c_df = df[df['CLOSING_DATE'] == current_date]
    p_df = df[df['CLOSING_DATE'] == comparison_date]

    # Display grids
    st.write('Current Date Repos')
    build_grid(c_df)

    st.write('Previous Date Repos')
    build_grid(p_df)

    return df