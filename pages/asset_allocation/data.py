import streamlit as st
from streamlit import session_state as ss
import pandas as pd
from db.data.fx import get_fx_rate
from utils.download import create_download_button

def verify_and_load_data():
    """Verify user selections and load data if all checks pass"""
    if not ss.get('selected_funds'):
        st.warning("Please select at least one fund.")
        st.stop()
    
    if not st.button('Load Data'):
        st.stop()
        
    fund_codes = ss['selected_funds']
    
    # Get and process the data
    df = _prepare_asset_allocation_data(fund_codes)
    
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def _prepare_asset_allocation_data(fund_codes):
    """Process and validate the asset allocation data"""
    # Get raw data
    df = _get_data()
    
    # Filter and check data
    df_filtered = df[df['FUND_CODE'].isin(fund_codes)]
    
    if len(df_filtered) == 0:
        st.error('No data available for the selected funds on these dates!')
        st.stop()
        
    # Store filtered data in session state for use by other components
    
    return df_filtered

def _get_data():
    current_date = ss.selected_date
    comparison_date = ss.selected_comparison_date
    
    df = _get_asset_allocation_data(current_date, comparison_date)
    
    return df
    
@st.cache_data(ttl=3600, show_spinner=False)
def _get_asset_allocation_data(current_date, comparison_date):
    current_date_string = current_date.strftime('%Y-%m-%d')
    comparison_date_string = comparison_date.strftime('%Y-%m-%d')
    
    sql = f"SELECT * FROM asset_allocation_new WHERE closing_date IN ('{current_date_string}', '{comparison_date_string}');"
    
    df = ss.snowflake.query(sql)
        
    return df

def filter_and_group_data(df, current_date, comparison_date, level):
    group_columns = ['OUTPUT_ORDER', 'LEVEL', 'ASSET_TYPE']
    
    # Filter current and comparison data
    df_current = df[(df['CLOSING_DATE'].dt.date == current_date) & (df['LEVEL'] <= level)]
    df_compare = df[(df['CLOSING_DATE'].dt.date == comparison_date) & (df['LEVEL'] <= level)]
    
    # Get numeric columns for aggregation
    other_columns = [col for col in df_current.columns 
                    if col not in group_columns 
                    and not pd.api.types.is_datetime64_any_dtype(df_current[col]) 
                    and not pd.api.types.is_string_dtype(df_current[col])]
    agg_dict = {col: 'sum' for col in other_columns}
    
    # Group current data
    df_current = df_current.groupby(group_columns).agg(agg_dict).reset_index()
    
    # Group comparison data
    df_compare = df_compare[['OUTPUT_ORDER', 'LEVEL', 'ASSET_TYPE', 'Clean MV']]
    df_compare = df_compare.groupby(group_columns).agg({'Clean MV': 'sum'}).reset_index()
    df_compare.rename(columns={'Clean MV': 'Previous Clean MV'}, inplace=True)
    
    # Merge datasets
    return pd.merge(df_current, df_compare, on=group_columns, how='outer').fillna(0)

def _calculate_percentages_and_changes(df):
    """Calculate percentages and changes between current and previous values"""
    # Calculate SAA percentage
    df['SAA(%)'] = df['SAA(%)'] / df[df['OUTPUT_ORDER'] == 0]['SAA(%)'][0] * 100
    
    # Calculate market value percentages
    df['Clean MV %'] = (df['Clean MV'] / df['Clean MV'].max()) * 100
    df['Previous Clean MV %'] = (df['Previous Clean MV'] / df['Previous Clean MV'].max()) * 100
    
    # Calculate changes
    df['MV Δ'] = df['Clean MV'] - df['Previous Clean MV']
    df['MV Δ %'] = df['Clean MV %'] - df['Previous Clean MV %']
    df['SAA Δ %'] = df['Clean MV %'] - df['SAA(%)']
    
    return df

def _apply_fx_rates(df, current_fx_rate, comparison_fx_rate):
    """Apply FX rates to monetary values"""
    # Apply comparison FX rate
    df['Previous Clean MV'] = df['Previous Clean MV'] * comparison_fx_rate
    
    # Apply current FX rate to relevant columns
    fx_rate_columns = [
        'Clean MV', 'Clean MV (Duration)', 'DV01 (mns)', 'DV50 (mns)', 
        'DVn50 (mns)', 'CS01 (mns)', 'Clean MV (Credits)', 
        'DV01 (Credits) (mns)', 'CS01 (Credits) (mns)', 'Clean MV (WARF)', 
        'Clean MV (1 in 200)', 'VAL01 (mns)'
    ]
    
    for column in fx_rate_columns:
        df[column] = df[column] * current_fx_rate
    
    return df

def _calculate_weighted_values(df):
    """Calculate weighted values based on market values"""
    weighted_columns = {
        "Duration (Sumproduct)": "Clean MV (Duration)",
        "Convexity (Sumproduct)": "Clean MV (Duration)",
        "YTM (Credits) (Sumproduct)": "Clean MV (Credits)",
        "Credit Spread (Credits) (Sumproduct)": "Clean MV (Credits)",
        "Duration (Credits) (Sumproduct)": "Clean MV (Credits)",
        "Convexity (Credits) (Sumproduct)": "Clean MV (Credits)",
        "WARF (Sumproduct)": "Clean MV (WARF)",
        "Time Until Maturity (Sumproduct)": "Clean MV (Duration)"
    }
    
    for key, value in weighted_columns.items():
        new_col = key.replace(" (Sumproduct)", "")
        df[new_col] = (df[key] / df[value]).fillna(0)
    
    return df, weighted_columns

def _reorder_columns(df, weighted_columns):
    """Reorder columns in the desired sequence"""
    cols = df.columns.tolist()
    
    # Reorder main columns
    key_cols = ['Previous Clean MV', 'Previous Clean MV %', 'MV Δ', 'MV Δ %', 
                'Clean MV %', 'SAA Δ %']
    target_positions = [3, 4, 5, 6, 8, 10]
    
    for col, pos in zip(key_cols, target_positions):
        cols.insert(pos, cols.pop(cols.index(col)))
    
    # Reorder weighted columns
    for key in weighted_columns:
        new_col = key.replace(" (Sumproduct)", "")
        cols.insert(cols.index(key), cols.pop(cols.index(new_col)))
        cols.pop(cols.index(key))
    
    return df[cols]

@st.cache_data(ttl=3600, show_spinner=False)
def process_data(df):
    """Process asset allocation data with calculations and formatting"""
    # Get parameters
    current_date = ss.selected_date
    comparison_date = ss.selected_comparison_date
    level = float(ss.selected_level)
    currency = ss.selected_currency
    current_fx_rate = get_fx_rate(currency, current_date)
    comparison_fx_rate = get_fx_rate(currency, comparison_date)
    
    # Process data in steps
    df = filter_and_group_data(df, current_date, comparison_date, level)
    df = _calculate_percentages_and_changes(df)
    df = _apply_fx_rates(df, current_fx_rate, comparison_fx_rate)
    df, weighted_columns = _calculate_weighted_values(df)
    df = _reorder_columns(df, weighted_columns)
    
    # Final formatting
    df = df.sort_values(by='OUTPUT_ORDER', ascending=True)
    df.rename(columns={
        'OUTPUT_ORDER': 'Order',
        'LEVEL': 'Level',
        'ASSET_TYPE': 'Asset Type'
    }, inplace=True)
    
    return df

def generate_download_file(df):
    current_date = ss.selected_date
    comparison_date = ss.selected_comparison_date
    level = float(ss.selected_level)
    currency = ss.selected_currency
    fund_codes = ss['selected_funds']
    
    file_name = 'asset_allocation_data'
    key = f'{file_name}_{current_date}_{comparison_date}_{level}_{currency}_{"/".join(fund_codes)}'
    create_download_button(df, file_name, key, 'Asset Allocation Data', add_time=True)