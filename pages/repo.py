import streamlit as st
import pandas as pd
from tools import filter, snowflake
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode
from styles.formatting import format_numbers
import plotly.express as px

pd.options.mode.chained_assignment = None

filter.build_date_filter()

if "repo_df" not in st.session_state:
    df = st.session_state["repo_df"] = snowflake.query("SELECT closing_date, lbu_code, fund_code, account_code, issuer, security_name, net_mv FROM funnelweb WHERE bbg_asset_type = 'Repo Liability';")
else:
    df = st.session_state["repo_df"]

current_date = st.session_state['Valuation Date']
compare_date = st.session_state['Comparison Date']

df = df[(df['CLOSING_DATE'].dt.date == current_date) | (df['CLOSING_DATE'].dt.date == compare_date)]
df['CLOSING_DATE'] = df['CLOSING_DATE'].dt.strftime('%Y-%m-%d')

display_names = { "CLOSING_DATE": "Closing Date", "LBU_CODE": "LBU Code", "FUND_CODE": "Fund Code", "ACCOUNT_CODE": "Account Code", "ISSUER": "Issuer", "SECURITY_NAME": "Security Name", "NET_MV": "Net MV" }

df.columns = [display_names[col] if col in display_names else col for col in df.columns]

gb = GridOptionsBuilder.from_dataframe(df)

gb.configure_default_column(
    resizable=True,
    filterable=True,
    editable=False,
)

for column in df.columns.tolist():
    gb.configure_column(field=column)

gb.configure_column(field="Net MV", valueFormatter=format_numbers())
other_options = {'suppressColumnVirtualisation': True}
gb.configure_grid_options(**other_options)
go = gb.build()
go['grandTotalRow'] = True
    
custom_css = {
        ".ag-cell": {"font-size": "90%"},
        ".ag-theme-streamlit": {"--ag-cell-horizontal-border": "none"},
        ".ag-header-cell": {"color": "white", "background-color": "rgb(232,119,34)", "--ag-header-cell-hover-background-color": "rgb(246,179,128)"},
        ".ag-header-cell-resize": {"display": "none"}
    }

with st.expander("Raw Data", True):
    with st.container(height=300):
        AgGrid(df, gridOptions=go, theme='streamlit', height=700, allow_unsafe_jscode=True, custom_css=custom_css, columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS)

df_bar = df[['Closing Date', 'LBU Code', 'Issuer', 'Net MV']]
df_bar = df_bar.groupby(['Closing Date', 'LBU Code', 'Issuer']).agg({'Net MV': 'sum'}).reset_index()
st.dataframe(df_bar)
fig = px.bar(df_bar, x='Closing Date', y='Net MV', color='Issuer')
st.plotly_chart(fig)