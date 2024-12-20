from utils.interface.menu import menu
from utils.snowflake.funnelweb import get_funnelweb_dates
import streamlit as st
from utils.filter.filter import build_lbu_filter, build_date_filter_buttons
from datetime import datetime
from streamlit import session_state as ss
from utils.snowflake.snowflake import query
import pandas as pd
from utils.interface.grid import AgGridBuilder

menu('Funnelweb Pivot')

columns = {'LBU Group': 'LBU_GROUP', 'LBU Code': 'LBU_CODE', 'FWD Asset Type': 'FWD_ASSET_TYPE'}
values = {'Net MV': 'NET_MV', 'Clean MV': 'CLEAN_MV_USD', 'Credit Spread': 'CREDIT_SPREAD_BP'}

def load_data():
    def check_columns_values():
        selected_columns = ss['selected_columns']
        selected_values = ss['selected_values']
        selected_funds = ss['selected_funds']

        if len(selected_columns) == 0 or len(selected_values) == 0:
            st.warning('Please select at least one column and one value!')
            ss['sql_statement'] = ''
            return True
        
        if len(selected_funds) == 0: 
            st.warning('Please select at least one fund!')
            ss['sql_statement'] = ''
            return True

        return False
    
    def build_query():
        selected_columns = ss['selected_columns']
        selected_values = ss['selected_values']
        fund_codes = str(ss['selected_funds']).replace('[', '').replace(']', '')
        current_date = ss['selected_date']
        comparison_date = ss['selected_comparison_date']

        query_string = f'SELECT CLOSING_DATE, {", ".join(selected_columns)}, {", ".join(selected_values)} FROM funnel.funnelweb WHERE fund_code IN ({fund_codes}) AND closing_date IN (\'{current_date}\', \'{comparison_date}\');'
        
        with st.expander('SQL Statement'):
            st.write(query_string)
            
        return query_string

    def query_data(query_string):
        if query_string == ss['sql_statement']:
            return ss['query_df']
        
        with st.spinner('Fetching your requested data...'):
            df = ss['query_df'] = query(query_string)

        ss['sql_statement'] = query_string

        return df
    
    def build_grid(df: pd.DataFrame):
        df['CLOSING_DATE'] = pd.to_datetime(df['CLOSING_DATE']).dt.strftime('%Y-%m-%d')

        selected_columns = ss['selected_columns']
        selected_values = ss['selected_values']

        grid = AgGridBuilder(df)
        grid.add_options(group_total=False)
        grid.add_columns(selected_columns, value_formatter=None)
        grid.add_values(selected_values)
        grid.set_pivot_column()
        grid.show_grid()

    load = False

    if st.button('Load Data'):
        load = True
    
    empty = check_columns_values()

    if empty or not load:
        return

    query_string = build_query()

    df = query_data(query_string)
    
    build_grid(df)

    st.toast('Loaded info!', icon='🎉')

with st.expander('Filters', True):
    dates = get_funnelweb_dates()

    build_date_filter_buttons('Valuation Date', dates, key='selected_date')
    build_date_filter_buttons('Comparison Date', dates, key='selected_comparison_date', date=ss['selected_date'])
    build_lbu_filter()

    selected_columns = st.multiselect('Columns', columns.keys())
    selected_values = st.multiselect('Values', values.keys())

    ss['selected_columns'] = [columns[column] for column in selected_columns]
    ss['selected_values'] = [values[value] for value in selected_values]

load_data()