import streamlit as st
from streamlit import session_state as ss
import pandas as pd
from db.data.fx import get_fx_rate
from db.data.data_shipment import get_lbu_data

def calculate_fees(df, config):
    fees_df = config.FEES
    custom_fees_df = config.CUSTOM_MANAGER_DATA
    
    # Calculate tiered fees
    tiered_df = fees_df[fees_df['CALC_MODE_ID'] == 2]
    
    for _, row in tiered_df.iterrows():        
        mv = _calculate_mv(df, fees_df, row['LBU_CODE'], row['MANAGER'], row['ASSET_TYPE'], row['MANAGER_MV_MODE_ID'])
        fee = _calculate_tiered_fee(mv, row['CALC_MODE_ARGS_DICT'])
    
        fees_df.loc[fees_df['ID_x'] == row['ID_x'], 'FEE_BPS'] = fee
    
    fees_df = _calculate_blackrock_fee(df, fees_df, custom_fees_df)
    
    results_df = _calculate_fees_mv(df, fees_df)

    return results_df

def _calculate_mv(df, fees_df, lbu, manager, asset_type, mv_mode_id, securities=[]):
    df = df[(df['MANAGER'] == manager) & (df['LBU_CODE'] == lbu)]
    df = _filter_dates(df, mv_mode_id)
    fees_df = fees_df[(fees_df['MANAGER'] == manager) & (fees_df['LBU_CODE'] == lbu)]
    manager_asset_types = fees_df['ASSET_TYPE'].unique()
    
    filtered_df = _filter_asset_type(df, asset_type, manager_asset_types)
    
    if securities != []:
        filtered_df = filtered_df[filtered_df['BBGID_V2'].isin(securities)]
    
    if mv_mode_id == 2.0 or mv_mode_id == 4.0:
        mv = filtered_df.groupby('CLOSING_DATE')['NET_MV'].sum().mean() / 1_000_000
    elif mv_mode_id == 3.0:
        mv = filtered_df.groupby('CLOSING_DATE')['NET_MV'].sum().mean() / 1_000_000 / 3
        
    return mv
    
def _filter_asset_type(df, asset_type, manager_asset_types):
    if asset_type == 'All':
        return df
    elif asset_type == 'Other':
        return df[~df['FWD_ASSET_TYPE'].isin(manager_asset_types)]
    else:
        return df[df['FWD_ASSET_TYPE'] == asset_type]
    
def _filter_dates(df, mv_mode_id):
    # N/A
    if mv_mode_id == 1.0:
        return df
    # Monthly
    elif mv_mode_id == 2.0 or mv_mode_id == 4.0:
        dates = ss.selected_dates[:2]
        return df[df['CLOSING_DATE'].isin(dates)]
    # Quarterly
    elif mv_mode_id == 3.0:
        quarter_dates = ss.selected_dates[:3]
        p_quarter_dates = ss.selected_dates[3:]

        df.loc[df['CLOSING_DATE'].isin(quarter_dates), 'CLOSING_DATE'] = 'This Quarter'
        df.loc[df['CLOSING_DATE'].isin(p_quarter_dates), 'CLOSING_DATE'] = 'Last Quarter'
        
        return df
    else:
        return df
    
def _calculate_tiered_fee(mv, tier_dict, category = ''):
    currency = tier_dict['currency']
    fx_rate = get_fx_rate(currency, ss.selected_date.to_pydatetime())
    
    mv *= fx_rate
    
    sumproduct = 0
    
    if category == '':
        aums = tier_dict['tiers']['aum']
        fees = tier_dict['tiers']['fee']
    else:
        aums = tier_dict['tiers'][category]['aum']
        fees = tier_dict['tiers'][category]['fee']

    remaining_mv = mv
    
    for i in range(0, len(aums)):
        aum = aums[i]
        
        if aum == 0:
            aum = remaining_mv
        
        fee_mv = min(remaining_mv, aum)
        sumproduct += fee_mv * fees[i]
        remaining_mv -= fee_mv
        
        if mv <= 0:
            break
        
    fee = sumproduct / mv

    return fee

def _calculate_blackrock_fee(df, fees_df, securities_df):
    blackrock_fees = fees_df[(fees_df['MANAGER'] == 'BlackRock') & (fees_df['LBU_CODE'] == 'HK')].iloc[0]
    blackrock_tiers_dict = blackrock_fees['CALC_MODE_ARGS_DICT']
    blackrock_tiers = blackrock_tiers_dict['tiers'].keys()
    blackrock_mv_mode = blackrock_fees['MANAGER_MV_MODE_ID']
    
    securities_df = securities_df[securities_df['MANAGER_ID'] == 4]

    df = df[df['L1_ASSET_TYPE'] != 'Derivatives']

    total_mv = _calculate_mv(df, fees_df, 'HK', 'BlackRock', 'All', blackrock_mv_mode)
    remaining_mv = total_mv
    sumproduct = 0
    
    for key in blackrock_tiers:
        securities = list(securities_df[securities_df['CATEGORY'] == key]['VALUE2'])
        
        if securities == []:
            mv = remaining_mv
        else:
            mv = _calculate_mv(df, fees_df, 'HK', 'BlackRock', 'All', blackrock_mv_mode, securities=securities)
        
        fee = _calculate_tiered_fee(mv, blackrock_tiers_dict, key)
        
        sumproduct += fee * mv
        remaining_mv -= mv
        
    fee = sumproduct / total_mv
    
    fees_df.loc[fees_df['ID_x'] == blackrock_fees['ID_x'], 'FEE_BPS'] = fee
    
    return fees_df

def _calculate_fees_mv(df, fees_df):
    categories_df = df[(df['MANAGER'] != 'FWD') & (df['L1_ASSET_TYPE'] != 'Derivatives') & (df['FWD_ASSET_TYPE'] != 'Other Assets')]
    categories = categories_df[['LBU_CODE', 'MANAGER', 'FWD_ASSET_TYPE']].drop_duplicates()
    
    mvs = {}
    fees = {}
    
    for _, row in categories.iterrows():
        lbu = row['LBU_CODE']
        manager = row['MANAGER']
        asset_type = row['FWD_ASSET_TYPE']
        manager_df = fees_df[(fees_df['MANAGER'] == manager) & (fees_df['LBU_CODE'] == lbu) & (fees_df['ASSET_TYPE'] == asset_type)]
        identifier = f"{lbu}/{manager}/{asset_type}"
        
        if len(manager_df) == 1:
            fee = manager_df.iloc[0]['FEE_BPS']
        elif len(manager_df) == 0:
            manager_df = fees_df[(fees_df['MANAGER'] == manager) & (fees_df['LBU_CODE'] == lbu)]
            fees_dict = manager_df.set_index('ASSET_TYPE')['FEE_BPS'].to_dict()
            
            if asset_type == 'Cash' and len(manager_df) == 1:
                fee = manager_df.iloc[0]['FEE_BPS']
            elif 'Others' in fees_dict:
                fee = fees_dict['Others']
            elif 'All' in fees_dict:
                fee = fees_dict['All']
            else:
                continue
        else:
            continue
        
        mv_mode_id = manager_df.iloc[0]['MANAGER_MV_MODE_ID']
        
        mv = _calculate_mv(df, fees_df, lbu, manager, asset_type, mv_mode_id)

        if pd.isna(mv):
            continue

        mvs[identifier] = mv
        fees[identifier] = fee
        
    results_df = pd.DataFrame({
        'LBU_CODE': [k.split('/')[0] for k in mvs.keys()],
        'MANAGER': [k.split('/')[1] for k in mvs.keys()],
        'ASSET_TYPE': [k.split('/')[2] for k in mvs.keys()],
        'NET_MV': list(mvs.values()),
        'FEE_BPS': [fees[k] for k in mvs.keys()]
    })
    
    # Convert to bps for fees and display in thousands
    results_df['FEE_K'] = results_df['NET_MV'] * results_df['FEE_BPS'] / 10_000 * 1_000
    
    lbus = get_lbu_data()
    lbu_group_dict = lbus.set_index('BLOOMBERG_NAME')['GROUP_NAME'].to_dict()
    lbu_group_dict['MC'] = lbu_group_dict['HK']
    results_df['LBU_GROUP_NAME'] = results_df['LBU_CODE'].map(lbu_group_dict)
    lbu_code_dict = lbus.set_index('BLOOMBERG_NAME')['LBU'].to_dict()
    lbu_code_dict['HK'] = lbus[(lbus['BLOOMBERG_NAME'] == 'HK') & (~lbus['SHORT_NAME'].str.contains('Macau', na=False))].iloc[0]['SUB_LBU']
    lbu_code_dict['MC'] = lbus[lbus['SHORT_NAME'].str.contains('Macau', na=False)].iloc[0]['SUB_LBU']
    results_df['LBU_CODE_NAME'] = results_df['LBU_CODE'].map(lbu_code_dict)
    
    results_df = results_df[['LBU_GROUP_NAME', 'LBU_CODE_NAME', 'LBU_CODE', 'MANAGER', 'ASSET_TYPE', 'NET_MV', 'FEE_BPS', 'FEE_K']]

    return results_df