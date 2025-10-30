import streamlit as st
from streamlit import session_state as ss
import pandas as pd
from numba import njit
import numpy as np

def verify_to_load():
    """Verify user selections and load data if all checks pass"""
    load = False
    empty = False
    #ss.pre_loaded = False
    
    same_start_date = ss.start_date == ss.previous_start_date
    same_end_date = ss.end_date == ss.previous_end_date
    same_columns = ss.selected_columns == ss.previous_selected_columns
    same_values = ss.selected_values == ss.previous_selected_values
    same_funds = ss.selected_funds == ss.previous_selected_funds
    
    if len(ss.selected_columns) == 0 or len(ss.selected_values) == 0:
        st.warning('Please select at least on column and one value to load the data!')
        empty = True
    elif same_start_date and same_end_date and same_columns and same_values and same_funds:
        load = True
    elif st.button('Load data'):
        load = True

    if empty or not load:
        st.stop()
        
    ss.previous_selected_columns = ss.selected_columns
    ss.previous_selected_values = ss.selected_values
    ss.previous_selected_mode = ss.selected_mode
    ss.previous_selected_Funds = ss.selected_funds

def get_data(config, bar):
    """Get average cost and position data for start and end period"""
    start_date = ss.start_date
    end_date = ss.end_date

    start_average_costs = _get_average_costs(start_date)
    bar.progress(30, "Getting data...")
    end_average_costs = _get_average_costs(end_date)
    bar.progress(40, "Getting data...")
    
    fund_codes = ss.selected_funds
    
    df = _get_positions(config, start_date, end_date, start_average_costs, end_average_costs, fund_codes)
    bar.progress(60, "Getting data...")
    
    ss.previous_start_date = start_date
    ss.previous_end_date = end_date
    
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def _get_average_costs(date):
    """Get average costs for all positions as of a specific date"""
    average_cost_sql = f"""
        WITH position_ids AS (
            SELECT DISTINCT position_id 
            FROM funnelweb 
            WHERE closing_date = '{date}' AND 
            (is_bbg_fi = true or bbg_asset_type = 'Equity')
        ), 
        first_dates AS (
            SELECT f.position_id, min(closing_date) AS first_price_date 
            FROM funnelweb f, position_ids p 
            WHERE f.position_id = p.position_id AND 
            clean_price != 0 
            GROUP BY f.position_id
        ) 
        SELECT f.position_id, f.security_name, clean_price, first_price_date 
        FROM funnelweb f 
        INNER JOIN first_dates fd ON f.position_id = fd.position_id 
        AND f.closing_date = fd.first_price_date;
    """
    
    ac_df = ss.snowflake.query(average_cost_sql)
    first_prices = ac_df.set_index('POSITION_ID')['CLEAN_PRICE'].to_dict()
    
    transactions_sql = f"""
        WITH position_ids AS (
            SELECT DISTINCT position_id 
            FROM funnelweb 
            WHERE closing_date = '{date}' AND 
            (is_bbg_fi = true or bbg_asset_type = 'Equity')
        ), 
        history_data AS (
            SELECT f.position_id, closing_date, position, 
            clean_price AS price, COALESCE(LAG(position) OVER (PARTITION BY f.position_id ORDER BY closing_date), 0) AS previous_position, 
            COALESCE(LAG(price) OVER (PARTITION BY f.position_id ORDER BY closing_date), price) AS previous_price, 
            position - previous_position AS position_change 
            FROM funnelweb f, position_ids p 
            WHERE f.position_id = p.position_id 
            ORDER BY position_id, closing_date
        ) 
        SELECT position_id, closing_date, position, 
        previous_price AS price, position_change 
        FROM history_data 
        WHERE position_change != 0 
        ORDER BY position_id, closing_date;
    """
    
    t_df = ss.snowflake.query(transactions_sql)
        
    position_ids, position_id_map = t_df['POSITION_ID'].factorize()
    position_changes = t_df['POSITION_CHANGE'].to_numpy(dtype=np.float64)
    positions = t_df['POSITION'].to_numpy(dtype=np.float64)
    prices = t_df['PRICE'].to_numpy(dtype=np.float64)
    
    first_prices_keys = np.array([position_id_map.get_loc(k) for k in first_prices.keys()], dtype=np.int64)
    first_prices_values = np.array(list(first_prices.values()), dtype=np.float64)
    
    average_costs_array = _compute_average_costs(position_ids, position_changes, positions, prices, first_prices_keys, first_prices_values)
    
    average_costs = dict(zip(t_df['POSITION_ID'].unique(), average_costs_array))
    
    return average_costs

@njit
def _compute_average_costs(position_ids, position_changes, positions, prices, first_prices_keys, first_prices_values):
    """Compute average costs for positions using transaction data"""
    average_costs = np.zeros(np.max(position_ids) + 1)
    total_cost = 0.0
    total_position = 0.0
    prev_position_id = -1
    first_transaction = False
    
    for i in range(len(position_ids)):
        position_id = position_ids[i]
        position_change = position_changes[i]
        position = positions[i]
        purchase_price = prices[i]
        
        if position_id != prev_position_id:
            if prev_position_id != -1:
                
                if total_cost != 0 and total_position != 0:
                    average_costs[prev_position_id] = total_cost / total_position
                else:
                    average_costs[prev_position_id] = 0.0

            total_cost = 0.0
            position_change = position
            first_transaction = True
        
        
        if position_change > 0 or first_transaction:
            if first_transaction and purchase_price == 0:
                for j in range(len(first_prices_keys)):
                    if first_prices_keys[j] == position_id:
                        purchase_price = first_prices_values[j]
                        break

            purchase_cost = purchase_price * position_change
            total_cost += purchase_cost
        
        else:
            if total_position != 0:
                total_cost += (total_cost / total_position) * position_change

        prev_position_id = position_id
        total_position = position
        first_transaction = False
        
    return average_costs

@st.cache_data(ttl=3600, show_spinner=False)
def _get_positions(config, start_date, end_date, start_average_costs, end_average_costs, fund_codes):
    """Get position data for start and end date, patched with average costs and other overrides"""
    sql = _build_sql(config, start_date, end_date, fund_codes)
    df = ss.snowflake.query(sql)
    
    fx_sql = f"SELECT valuation_date, fx, rate FROM supp.fx_rates WHERE valuation_date IN ('{start_date}', '{end_date}');"
    fx_df = ss.snowflake.query(fx_sql)
    
    df = _patch_data(df, fx_df, start_average_costs, end_average_costs)
    
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def _build_sql(config, start_date, end_date, fund_codes):
    """Build SQL query to get position data for start and end date"""
    fund_codes_string = "', '".join(fund_codes)
    
    default_condition = "position * unit * IFF(mtge_factor > 0, mtge_factor, 1) * IFF(principal_factor > 0, principal_factor, 1)"

    notional_usd_conditions = {"fwd_asset_type = 'Accreting notes'": f"sw_rec_notl_amt / rate",
                    "bbg_asset_type IN ('Multi-Leg Deal', 'Foreign Exchange Forward', 'Non Deliverable Swap', 'OIS Swap', 'Amort. Swap')": f"IFF(derivs_dollar_notional IS NULL, 0, derivs_dollar_notional)",
                    "bbg_asset_type IN ('Warrant', 'Index Option')": "position * unit * strike / rate"}

    notional_usd_case_sql = "CASE  \n" + '  \n'.join(f'WHEN {key} THEN {value}' for key, value in notional_usd_conditions.items()) + f"  \nELSE {default_condition} / rate" + "  \nEND AS notional_usd"

    fx_rate_sql = f"WITH fx_rates AS (SELECT fx, rate FROM supp.fx_rates WHERE valuation_date = '{end_date}')"

    sql = f"""{fx_rate_sql}  
    SELECT {", ".join(config.IDENTIFIER_COLUMNS)},  
    {", ".join(config.STATIC_COLUMNS)},  
    {", ".join(config.CHARACTERISTIC_COLUMNS)},
    {", ".join([f"{value} AS {key}" for key, value in config.FORMULA_COLUMNS.items()])},
    {notional_usd_case_sql} 
    FROM funnel.funnelweb AS fw
    LEFT JOIN fx_rates AS f1 ON fw.currency = f1.fx
    WHERE closing_date IN (\'{start_date}\', \'{end_date}\') 
    AND bbg_asset_type != 'Repo Liability'
    AND fund_code IN ('{fund_codes_string}')
    ORDER BY closing_date;"""
    
    return sql

def _patch_data(df, fx_df, start_average_costs, end_average_costs):
    """Patch data with average costs, FX rates, and other overrides"""
    # Change date to string
    df['CLOSING_DATE'] = pd.to_datetime(df['CLOSING_DATE']).dt.strftime('%Y-%m-%d')
    
    # Apply average cost dictionary to dataframe
    start_date_mask = df['CLOSING_DATE'] == ss.start_date_string
    end_date_mask = df['CLOSING_DATE'] == ss.end_date_string

    df['AVERAGE_COST'] = np.where(
        start_date_mask & df['POSITION_ID'].isin(start_average_costs),
        df['POSITION_ID'].map(start_average_costs),
        np.where(
            end_date_mask & df['POSITION_ID'].isin(end_average_costs),
            df['POSITION_ID'].map(end_average_costs),
            np.nan
        )
    )
        
    # Fix notional usd for equities
    df.rename(columns={'NOTIONAL_USD': 'NOTIONAL_USD_OLD'}, inplace=True)
    df['NOTIONAL_USD'] = df['NOTIONAL_USD_OLD']
    
    equity_mask = df['BBG_ASSET_TYPE'] == 'Equity'
    gbp_mask = df['CURRENCY'] == 'GBP'

    df.loc[equity_mask, 'NOTIONAL_USD'] = (
        df.loc[equity_mask, 'POSITION'] *
        df.loc[equity_mask, 'UNIT'] *
        df.loc[equity_mask, 'AVERAGE_COST'] /
        df.loc[equity_mask, 'RATE'] /
        np.where(gbp_mask.loc[equity_mask], 100, 1)
    )
    
    # Adjust notional for derivatives
    derivs = ['Multi-Leg Deal', 'Foreign Exchange Forward', 'Non Deliverable Swap', 'OIS Swap', 'Amort. Swap']
    deriv_mask = df['BBG_ASSET_TYPE'].isin(derivs) & (df['CLOSING_DATE'] == ss.start_date_string)

    fx_start = fx_df[fx_df['VALUATION_DATE'] == ss.start_date_string].set_index('FX')['RATE'].to_dict()
    fx_end = fx_df[fx_df['VALUATION_DATE'] == ss.end_date_string].set_index('FX')['RATE'].to_dict()

    def get_fx_rate(currency):
        return fx_start.get(currency, 1), fx_end.get(currency, 1)

    fx_rates = df.loc[deriv_mask, 'SW_REC_CRNCY'].apply(lambda c: get_fx_rate(c))
    start_rates = fx_rates.apply(lambda x: x[0])
    end_rates = fx_rates.apply(lambda x: x[1])

    df.loc[deriv_mask, 'NOTIONAL_USD'] = (
        df.loc[deriv_mask, 'NOTIONAL_USD'] * start_rates / end_rates
    )
     
    # Fill L3 asset type if blank
    df['L3_ASSET_TYPE'] = np.where(df['L3_ASSET_TYPE'] == 'None', df['L2_ASSET_TYPE'], df['L3_ASSET_TYPE'])

    # Send cash to cash account
    df['FWD_ASSET_TYPE'] = np.where(df['BBG_ASSET_TYPE'] == 'Cash', 'Cash', df['FWD_ASSET_TYPE'])

    # Use L3 asset type for derivatives
    df['FWD_ASSET_TYPE'] = np.where(df['L1_ASSET_TYPE'] == 'Derivatives', df['L3_ASSET_TYPE'], df['FWD_ASSET_TYPE'])

    # Send interim T bills to cash
    tbill_mask = (df['BBG_ASSET_TYPE'] == 'Treasury') & (df['FWD_ASSET_TYPE'] != 'Sovereign Bonds')
    df.loc[tbill_mask, 'FWD_ASSET_TYPE'] = 'Cash'

    # Merge PineBridge custodies
    df['MANAGER'] = np.where(df['MANAGER'].str.contains('Pinebridge', na=False), 'Pinebridge', df['MANAGER'])

    return df