from utils.interface.menu import menu
from utils.snowflake.funnelweb import get_funnelweb_dates, get_asset_allocation
import streamlit as st
from utils.filter.filter import build_lbu_filter, build_date_filter_buttons, build_fx_filter, build_level_filter
from streamlit import session_state as ss
from utils.snowflake.snowflake import query
import pandas as pd
from utils.interface.grid import AgGridBuilder
from classes.fx import get_fx_rate
from utils.interface.download import create_download_button

menu('pages/asset_allocation.py')

with st.expander('Filters', True):
    dates = get_funnelweb_dates()

    build_date_filter_buttons('Valuation Date', dates, key='selected_date')
    build_date_filter_buttons('Comparison Date', dates, key='selected_comparison_date', date=ss['selected_date'])
    build_lbu_filter()
    build_fx_filter()
    build_level_filter()

fund_codes = ss['selected_funds']
current_date = ss['selected_date']
comparison_date = ss['selected_comparison_date']
level = float(ss['selected_level'])
current_fx_rate = get_fx_rate(ss['currencies'], ss['selected_currency'], current_date)
comparison_fx_rate = get_fx_rate(ss['currencies'], ss['selected_currency'], comparison_date)

if len(fund_codes) == 0:
    st.warning('Please select at least one fund')
    st.stop()

with st.spinner('Loading your data'):
    df = get_asset_allocation()
    
    df = df[df['FUND_CODE'].isin(fund_codes)]
    df_current = df[(df['CLOSING_DATE'].dt.date == current_date) & (df['LEVEL'] <= level)]
    df_compare = df[(df['CLOSING_DATE'].dt.date == comparison_date) & (df['LEVEL'] <= level)]

    group_columns = ['OUTPUT_ORDER', 'LEVEL', 'ASSET_TYPE']
    other_columns = [col for col in df_current.columns if col not in group_columns and not pd.api.types.is_datetime64_any_dtype(df_current[col]) and not pd.api.types.is_string_dtype(df_current[col])]
    
    agg_dict = {col: 'sum' for col in other_columns}
    df_current = df_current.groupby(group_columns).agg(agg_dict).reset_index()

    df_compare = df_compare[['OUTPUT_ORDER', 'LEVEL', 'ASSET_TYPE', 'Clean MV']]
    df_compare = df_compare.groupby(['OUTPUT_ORDER', 'LEVEL', 'ASSET_TYPE']).agg({'Clean MV': 'sum'}).reset_index()
    df_compare.rename(columns={'Clean MV': 'Previous Clean MV'}, inplace=True)

    df_grouped = pd.merge(df_current, df_compare, on=['OUTPUT_ORDER', 'LEVEL', 'ASSET_TYPE'], how='outer').fillna(0)

    df_grouped['SAA(%)'] = df_grouped['SAA(%)'] / df_grouped[df_grouped['OUTPUT_ORDER'] == 0]['SAA(%)'][0] * 100
    df_grouped['Clean MV %'] = (df_grouped['Clean MV'] / df_grouped['Clean MV'].max()) * 100
    df_grouped['Previous Clean MV %'] = (df_grouped['Previous Clean MV'] / df_grouped['Previous Clean MV'].max()) * 100
    df_grouped['MV Δ'] = df_grouped['Clean MV'] - df_grouped['Previous Clean MV']
    df_grouped['MV Δ %'] = df_grouped['Clean MV %'] - df_grouped['Previous Clean MV %']
    df_grouped['SAA Δ %'] = df_grouped['Clean MV %'] - df_grouped['SAA(%)']

    df_grouped['Previous Clean MV'] = df_grouped['Previous Clean MV'] * comparison_fx_rate
    
    fx_rate_columns = ['Clean MV', 'Clean MV (Duration)', 'DV01 (mns)', 'DV50 (mns)', 'DVn50 (mns)', 'CS01 (mns)', 'Clean MV (Credits)', 'DV01 (Credits) (mns)', 'CS01 (Credits) (mns)', 'Clean MV (WARF)', 'Clean MV (1 in 200)', 'VAL01 (mns)']

    for column in fx_rate_columns:
        df_grouped[column] = df_grouped[column] * current_fx_rate

    weighted_columns = {"Duration (Sumproduct)": "Clean MV (Duration)", "Convexity (Sumproduct)": "Clean MV (Duration)", "YTM (Credits) (Sumproduct)": "Clean MV (Credits)", "Credit Spread (Credits) (Sumproduct)": "Clean MV (Credits)", "Duration (Credits) (Sumproduct)": "Clean MV (Credits)", "Convexity (Credits) (Sumproduct)": "Clean MV (Credits)", "WARF (Sumproduct)": "Clean MV (WARF)", "Time Until Maturity (Sumproduct)": "Clean MV (Duration)" }

    for key, value in weighted_columns.items():
        df_grouped[key.replace(" (Sumproduct)", "")] = (df_grouped[key] / df_grouped[value]).fillna(0)
        
    cols = df_grouped.columns.tolist()
    cols.insert(3, cols.pop(cols.index('Previous Clean MV')))
    cols.insert(4, cols.pop(cols.index('Previous Clean MV %')))
    cols.insert(5, cols.pop(cols.index('MV Δ')))
    cols.insert(6, cols.pop(cols.index('MV Δ %')))
    cols.insert(8, cols.pop(cols.index('Clean MV %')))
    cols.insert(10, cols.pop(cols.index('SAA Δ %')))

    for key in weighted_columns.keys():
        cols.insert(cols.index(key), cols.pop(cols.index(key.replace(" (Sumproduct)", ""))))
        cols.pop(cols.index(key))
    
    df_grouped = df_grouped[cols]

    df_grouped = df_grouped.sort_values(by='OUTPUT_ORDER', ascending=True)

    df_grouped.rename(columns={'OUTPUT_ORDER': 'Order', 'LEVEL': 'Level', 'ASSET_TYPE': 'Asset Type'}, inplace=True)

    grid = AgGridBuilder(df_grouped)

    grid.add_columns(['Order', 'Level'], False, None, '')
    grid.add_column('Asset Type', None, {'border-right': '1px solid rgb(232,119,34)'})

    ignore_columns = ['Order', 'Level', 'Asset Type']
    conditional_formatting_columns = ['MV Δ %', 'SAA Δ %']

    for column in df_grouped.columns.tolist():
        if column in ignore_columns:
            continue
        elif column in conditional_formatting_columns:
            grid.add_column(column)
        else:
            grid.add_column(column, cell_style=None)

    grid.show_grid()

    create_download_button(df_grouped, 'asset_allocation', add_time=True)