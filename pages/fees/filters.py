import streamlit as st
from streamlit import session_state as ss
import pandas as pd
from datetime import datetime
from db.data.data_shipment import get_funnelweb_dates
        
def build_month_end_filters():
    dates = list(get_funnelweb_dates())
        
    month_end_dates = sorted({min([date for date in dates if date.month == month and date.year == year]) 
                          for year in set(date.year for date in dates) 
                          for month in set(date.month for date in dates if date.year == year)})
    
    month_end_dates.reverse()
    
    month_end_dates_filtered = [date for date in month_end_dates if date > datetime(2024,12,31)]
    
    date_dict = {
        (datetime(date.year, date.month - 1, 1).strftime('%b %Y') if date.month > 1 
         else datetime(date.year - 1, 12, 1).strftime('%b %Y')): date
        for date in month_end_dates_filtered
    }
    
    max_date = max(date_dict.values())
    default_date = next((key for key, value in date_dict.items() if value == max_date), None)
    
    selected_date_name = st.selectbox('Month', list(date_dict.keys()), key='selected_month_end', index=list(date_dict.keys()).index(default_date))
    
    selected_date = ss.selected_date = date_dict[selected_date_name]
    
    # Get the 5 months prior to the selected_date
    selected_months = [date.to_pydatetime().date() for date in month_end_dates if date <= selected_date][:6]
    ss.selected_dates = selected_months
    
def build_fees_filters(df):
    lbus = df['LBU_CODE'].unique().tolist()
    managers = df['MANAGER'].unique().tolist()
    asset_types = df['ASSET_TYPE'].unique().tolist()
    
    lbus = st.multiselect('LBU', lbus, default=lbus, key='selected_lbu')
    managers = st.multiselect('Manager', managers, default=managers, key='selected_manager')
    asset_types = st.multiselect('Asset Type', asset_types, default=asset_types, key='selected_asset_type')

    filtered_df = df[(df['LBU_CODE'].isin(lbus)) & (df['MANAGER'].isin(managers)) & (df['ASSET_TYPE'].isin(asset_types))]
    
    return filtered_df

def build_pivot_filter(modes):
    pivot_mode = st.segmented_control('Pivot Mode', list(modes.keys()), key='pivot_mode', default=list(modes.keys())[0])
    return modes[pivot_mode]

def build_period_filter():
    periods = {'Monthly': 12, 'Quarterly': 4, 'Yearly': 1}
    
    period_mode = st.segmented_control('Period', list(periods.keys()), key='period_mode', default='Monthly')
    return periods[period_mode]