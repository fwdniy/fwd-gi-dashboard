from utils.snowflake.snowflake import query
from datetime import datetime
import pandas as pd
from streamlit import session_state as ss

def get_funnelweb_dates() -> list[datetime]:
    if 'funnelweb_dates' in ss:
        return ss['funnelweb_dates']

    query_string: str = 'SELECT DISTINCT closing_date FROM funnelweb WHERE closing_date >= \'2021-12-31\' ORDER BY closing_date;'
    df: pd.DataFrame = query(query_string)

    dates: list[datetime] = df['CLOSING_DATE'].unique()
    ss['funnelweb_dates'] = dates
    
    return dates

def get_asset_allocation(current_date, comparison_date) -> pd.DataFrame:    
    current_date_string = current_date.strftime('%Y-%m-%d')
    comparison_date_string = comparison_date.strftime('%Y-%m-%d')
    
    query_string: str = f"SELECT * FROM asset_allocation_new WHERE closing_date IN ('{current_date_string}', '{comparison_date_string}');"
    
    if query_string == ss.asset_allocation_sql:
        return ss.asset_allocation
    
    df: pd.DataFrame = query(query_string)
    
    ss['asset_allocation_sql']
    ss['asset_allocation'] = df
    
    return df
