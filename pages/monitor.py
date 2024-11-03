import streamlit as st
import pandas as pd
from tools import filter, snowflake
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, ColumnsAutoSizeMode
from styles.formatting import format_numbers, conditional_formatting
from streamlit_tree_select import tree_select
import plotly.express as px
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
from io import BytesIO
import base64

with st.expander("Filters"):
    filter.build_date_filter()
    filter.build_lbu_tree()

current_date = st.session_state['Valuation Date'].strftime('%Y-%m-%d')
compare_date = st.session_state['Comparison Date'].strftime('%Y-%m-%d')
lbu_selection = st.session_state['lbu_tree_data']

fund_codes = str(lbu_selection).replace("[", "").replace("]", "")

query = f"SELECT security_name, effective_maturity AS maturity, sum(net_mv) AS net_mv, avg(clean_price) AS price, avg(credit_spread_bp) AS credit_spread, sum(dv01_000) AS dv01, sum(cs01_000) AS cs01, avg(duration) AS duration, avg(ytm) AS ytm, avg(convexity) AS convexity FROM funnel.funnelweb WHERE closing_date = '{current_date}' AND fund_code IN ({fund_codes}) AND l1_asset_type = 'Debt Investments' GROUP BY security_name, effective_maturity;"
df = snowflake.query(query)

# Extract the date part
df['MATURITY'] = pd.to_datetime(df['MATURITY']).dt.date

with st.expander("Box Plots"):
    # Sample data
    fig = px.box(df, x='CREDIT_SPREAD', points="all", hover_data=['SECURITY_NAME', 'MATURITY', 'NET_MV', 'PRICE'], title="Credit Spread Box Plot")
    st.plotly_chart(fig)

    fig = px.box(df, x='YTM', points="all", hover_data=['SECURITY_NAME', 'MATURITY', 'NET_MV', 'PRICE'], title="YTM Box Plot")
    st.plotly_chart(fig)

    fig = px.box(df, x='DURATION', points="all", hover_data=['SECURITY_NAME', 'MATURITY', 'NET_MV', 'PRICE'], title="Duration Box Plot")
    st.plotly_chart(fig)

    fig = px.box(df, x='CONVEXITY', points="all", hover_data=['SECURITY_NAME', 'MATURITY', 'NET_MV', 'PRICE'], title="Convexity Box Plot")
    st.plotly_chart(fig)

    fig = px.box(df, x='DV01', points="all", hover_data=['SECURITY_NAME', 'MATURITY', 'NET_MV', 'PRICE'], title="DV01 Box Plot")
    st.plotly_chart(fig)

    fig = px.box(df, x='CS01', points="all", hover_data=['SECURITY_NAME', 'MATURITY', 'NET_MV', 'PRICE'], title="CS01 Box Plot")
    st.plotly_chart(fig)

query = f"""
WITH sum_cs AS (SELECT security_name, sum(credit_spread_bp) AS credit_spread FROM funnelweb WHERE closing_date BETWEEN '{compare_date}' AND '{current_date}' AND is_bbg_fi = true  GROUP BY security_name), 
day_cs AS (SELECT closing_date, security_name, avg(credit_spread_bp) AS credit_spread FROM funnelweb WHERE closing_date BETWEEN '{compare_date}' AND '{current_date}' AND is_bbg_fi = true GROUP BY closing_date, security_name ORDER BY security_name, closing_date)
SELECT day_cs.security_name, day_cs.closing_date, day_cs.credit_spread FROM sum_cs LEFT JOIN day_cs ON sum_cs.security_name = day_cs.security_name WHERE sum_cs.credit_spread <> 0 
AND sum_cs.security_name NOT IN (WITH counts AS (SELECT security_name, account_code, clean_price, count(id) AS count_id FROM funnelweb WHERE closing_date BETWEEN '{compare_date}' AND '{current_date}' AND is_bbg_fi = true GROUP BY security_name, account_code, clean_price ORDER BY security_name, account_code, clean_price) SELECT DISTINCT security_name FROM counts WHERE count_id >= 20);
"""

query = f"""WITH spreads AS (SELECT bbgid_v2, closing_date, avg(clean_price) AS price, avg(credit_spread_bp) AS credit_spread 
FROM funnelweb 
WHERE closing_date BETWEEN '2023-12-29' AND '2024-11-01' 
AND bbgid_V2 IN (SELECT DISTINCT bbgid_v2 FROM funnelweb WHERE closing_date = '2024-11-01' AND is_bbg_fi = true AND (bbg_asset_type NOT IN ('Bond Option', 'Repo Liability', 'Money Market') OR (bbg_asset_type = 'Money Market' AND clean_price <> 100)) AND cic NOT LIKE '%51')
AND bbgid_v2 NOT IN (WITH data AS (SELECT bbgid_v2, count(distinct clean_price) AS distinct_prices, (max(closing_date) - min(closing_date)) / 30 holding_months FROM funnelweb WHERE closing_date BETWEEN '2023-12-29' AND '2024-11-01' AND is_bbg_fi = true AND (bbg_asset_type NOT IN ('Bond Option', 'Repo Liability', 'Money Market') OR (bbg_asset_type = 'Money Market' AND clean_price <> 100)) GROUP BY bbgid_v2 ORDER BY bbgid_v2)
SELECT bbgid_v2 FROM data WHERE distinct_prices + 1 < FLOOR(holding_months))
GROUP BY bbgid_v2, closing_date ORDER BY bbgid_v2, closing_date),
names AS (SELECT DISTINCT security_name, bbgid_v2 FROM funnelweb WHERE closing_date = '2024-11-01')
SELECT names.security_name, names.bbgid_v2, closing_date, price, credit_spread FROM spreads, names WHERE spreads.bbgid_v2 = names.bbgid_v2;"""

df = snowflake.query(query)

credit_spread_diff = df.groupby('SECURITY_NAME').apply(lambda x: x.loc[x['CLOSING_DATE'].idxmax(), 'CREDIT_SPREAD'] - x.loc[x['CLOSING_DATE'].idxmin(), 'CREDIT_SPREAD'])
df['CLOSING_DATE'] = df['CLOSING_DATE'].dt.strftime('%Y-%m-%d')
df = df.pivot(index='SECURITY_NAME', columns='CLOSING_DATE', values='CREDIT_SPREAD').reset_index()
df['credit_spread_diff'] = credit_spread_diff.values
df = df.sort_values(by='credit_spread_diff', ascending=False)
df = df.head(50)
   

# Add sparklines to the dataframe
df['trend'] = df.apply(lambda row: [{"date": col, "value": row[col]} for col in df.columns[1:-1] if pd.notna(row[col])], axis=1)

df = df[['SECURITY_NAME', 'credit_spread_diff', 'trend']]

# Display the dataframe in Streamlit using AG Grid
st.title("Credit Spread Analysis")

gb = GridOptionsBuilder.from_dataframe(df)
    
gb.configure_default_column(resizable=True, filterable=True, editable=False, flex=1, minWidth=170)
gb.configure_grid_options(autoGroupColumnDef={'cellRendererParams': { 'suppressCount': 'true'}, 'pinned': 'left'}, suppressAggFuncInHeader=True, groupDisplayType='multipleColumns')

gb.configure_column('SECURITY_NAME', header_name='Security Name', pinned="left")
gb.configure_column('credit_spread_diff', header_name='Credit Spread Delta')
gb.configure_column('trend', header_name='Trend', cellRenderer='agSparklineCellRenderer', cellRendererParams={'sparklineOptions': { 'type': 'line', 'xKey': 'date', 'yKey': 'value'}})

go = gb.build()

height = 630

custom_css = {
        ".ag-cell": {"font-size": "90%"},
        ".ag-theme-streamlit": {"--ag-cell-horizontal-border": "none"},
        ".ag-header-cell": {"color": "white", "background-color": "rgb(232,119,34)", "--ag-header-cell-hover-background-color": "rgb(246,179,128)"},
        ".ag-header-cell-resize": {"display": "none"},
        ".ag-header-group-cell.ag-header-group-cell-with-group": {"display": "flex", "justify-content": "flex-end"},
        ".ag-header-group-cell.ag-header-group-cell-with-group[aria-expanded='true']": {"display": "flex", "justify-content": "flex-start"},
}

AgGrid(df, gridOptions=go, height=height, theme='streamlit', allow_unsafe_jscode=True, custom_css=custom_css)
