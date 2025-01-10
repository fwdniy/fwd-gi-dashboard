from utils.interface.menu import menu
from utils.snowflake.funnelweb import get_funnelweb_dates
import streamlit as st
from utils.filter.filter import build_lbu_filter, build_date_filter_buttons
from streamlit import session_state as ss
from utils.snowflake.snowflake import query
import pandas as pd
from utils.interface.grid import AgGridBuilder
import plotly.express as px

menu('pages/repo.py')

def load_data():
    def query_data():
        fund_codes = str(ss['selected_funds']).replace('[', '').replace(']', '')
        current_date = ss['selected_date']
        comparison_date = ss['selected_comparison_date']

        query_string = f'SELECT CLOSING_DATE, LBU_CODE, ISSUER, L3_ASSET_TYPE, ACCOUNT_CODE, SECURITY_NAME, NET_MV FROM funnel.funnelweb WHERE bbg_asset_type = \'Repo Liability\' AND fund_code IN ({fund_codes}) AND closing_date IN (\'{current_date}\', \'{comparison_date}\') ORDER BY closing_date DESC;'
            
        return query_string
    
    def build_grid(df: pd.DataFrame):        
        grid = AgGridBuilder(df)
        columns = list(df.columns)
        
        grid.add_columns([column for column in columns if column != 'NET_MV'], False, None)
        grid.add_values(['NET_MV'], ['Net MV'])
        
        grid.show_grid((len(df) + 1)*30)
    
    query_string = query_data()

    with st.spinner('Fetching your requested data...'):
        df = ss['query_df'] = query(query_string)
        
    df['CLOSING_DATE'] = pd.to_datetime(df['CLOSING_DATE']).dt.strftime('%Y-%m-%d')
    df['NET_MV'] = df['NET_MV'] / 1000000
    
    df = df.groupby(['CLOSING_DATE', 'LBU_CODE', 'ISSUER', 'L3_ASSET_TYPE', 'ACCOUNT_CODE', 'SECURITY_NAME']).sum().reset_index()
    
    comparison_date = df['CLOSING_DATE'].unique()[0]
    current_date = df['CLOSING_DATE'].unique()[1]
    
    c_df = df[df['CLOSING_DATE'] == current_date]
    p_df = df[df['CLOSING_DATE'] == comparison_date]    
    
    st.write('Current Date Repos')
    build_grid(c_df)
    
    st.write('Previous Date Repos')
    build_grid(p_df)
    
    chart_df = df.groupby(['ISSUER', 'CLOSING_DATE', 'L3_ASSET_TYPE']).sum('NET_MV').reset_index()
    
    chart_df['NET_MV_ROUNDED'] = chart_df['NET_MV'].round(0)
    facet_col = 'L3_ASSET_TYPE'
    
    st.pills('L3 Asset Type', ['Split', 'Unsplit'], key='l3_asset_type_split')
    
    if ss['l3_asset_type_split'] == 'Split':
        facet_col = None
    
    fig = px.bar(chart_df, x='ISSUER', y='NET_MV', color='CLOSING_DATE', barmode='group', facet_col=facet_col,
                 hover_data={'NET_MV_ROUNDED': False, 'CLOSING_DATE': True, 'ISSUER': True, 'L3_ASSET_TYPE': True, 'NET_MV': True},
                 text='NET_MV_ROUNDED',
                 labels={'ISSUER': 'Issuer Name', 'NET_MV': 'Net MV', 'CLOSING_DATE': 'Closing Date', 'L3_ASSET_TYPE': 'L3 Asset Type'})

    st.plotly_chart(fig, use_container_width=True)

with st.expander('Filters', True):
    dates = get_funnelweb_dates()
    build_date_filter_buttons('Valuation Date', dates, key='selected_date')
    build_date_filter_buttons('Comparison Date', dates, key='selected_comparison_date', date=ss['selected_date'])
    build_lbu_filter()
    
load_data()