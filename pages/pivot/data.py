import streamlit as st
from streamlit import session_state as ss

def verify_to_load():
    checks = [
        (len(ss.selected_funds) == 0, "Please select at least one fund."),
        (len(ss.selected_columns) == 0, "Please select at least one column."),
        (len(ss.selected_values) == 0, "Please select at least one value.")
    ]

    load = False

    if st.button('Load Data'):
        load = True
        for condition, message in checks:
            if condition:
                st.warning(message)
                load = False

    if not load:
            st.stop()


def _build_query(selected_columns, selected_values, fund_codes, current_date, comparison_date):    
    mv_list = [column for column in selected_values if 'MV' in column]

    if len(mv_list) == 0:
        selected_values.append('NET_MV')

    sql = f'SELECT CLOSING_DATE, {", ".join(selected_columns)}, {", ".join(selected_values)} FROM funnel.funnelweb WHERE fund_code IN ({fund_codes}) AND closing_date IN (\'{current_date}\', \'{comparison_date}\') ORDER BY closing_date DESC;'
    
    with st.expander('SQL Statement'):
        st.write(sql)
        
    return sql

def get_data(config):
    columns = config.COLUMNS
    values = config.VALUES
    
    selected_columns = [columns[column] for column in ss['selected_columns']]
    selected_values = [values[column] for column in ss['selected_values']]

    fund_codes = str(ss['selected_funds']).replace('[', '').replace(']', '')
    current_date = ss['selected_date']
    comparison_date = ss['selected_comparison_date']
    
    sql = _build_query(selected_columns, selected_values, fund_codes, current_date, comparison_date)
    df = ss.snowflake.query(sql)
    
    return df