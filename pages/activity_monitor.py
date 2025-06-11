import streamlit as st
from streamlit import session_state as ss
import pandas as pd
import numpy as np
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode

from utils.interface.menu import menu
from utils.snowflake.funnelweb import get_funnelweb_dates
from utils.filter.filter import build_lbu_filter, build_date_filter_buttons, build_multi_select_filter
from utils.snowflake.snowflake import query
from utils.interface.grid import AgGridBuilder, format_numbers, conditional_formatting

menu('pages/activity_monitor.py')

#Filter fields
FILTER_COLUMNS = {'LBU Group': 'LBU_GROUP', 'Fund Code': 'FUND_CODE', 'Account Code': 'ACCOUNT_CODE', 'Final Rating': 'FINAL_RATING', 'Final Rating Letter': 'FINAL_RATING_LETTER', 'Country': 'COUNTRY_REPORT', 'Manager': 'MANAGER', 'Maturity Range': 'MATURITY_RANGE', 'FWD Asset Type': 'FWD_ASSET_TYPE', 'L1 Asset Type': 'L1_ASSET_TYPE', 'L2 Asset Type': 'L2_ASSET_TYPE', 'L3 Asset Type': 'L3_ASSET_TYPE', 'BBG Asset Type': 'BBG_ASSET_TYPE', 'Currency': 'CURRENCY', 'Security Name': 'SECURITY_NAME'}
FILTER_VALUES = {'Net MV': 'NET_MV', 'Notional': 'NOTIONAL_USD', 'Duration': 'DURATION', 'WARF': 'WARF'}
FILTER_VALUES_SUM = {'NET_MV': 1000000, 'NOTIONAL_USD': 1000000}
FILTER_VALUES_WA = ['DURATION', 'WARF']
TRANSACTIONS_MODES = ['NET_MV', 'NOTIONAL_USD']

# Query fields
IDENTIFIER_COLUMNS = ['closing_date', 'position_id', 'security_name', 'bbgid_v2', 'lbu_group', 'lbu_code', 'fund_code', 'account_code']
STATIC_COLUMNS = ['country_report', 'manager', 'fwd_asset_type', 'l1_asset_type', 'l2_asset_type', 'l3_asset_type', 'bbg_asset_type', 'currency', 'maturity', 'securitized_credit_type', 'sw_rec_crncy']
CHARACTERISTIC_COLUMNS = ['net_mv', 'duration', 'final_rating', 'final_rating_letter', 'maturity_range', 'mtge_factor', 'principal_factor', 'last_trade_date', 'position', 'unit', 'rate', 'warf']
FORMULA_COLUMNS = {'currency_pair': 'IFF(sw_pay_crncy IS NULL OR sw_rec_crncy IS NULL, NULL, sw_pay_crncy || \'/\' || sw_rec_crncy)'}

def initialize_variables(label, default):
    if label in ss:
        return ss[label]
    
    return default

ss['df'] = initialize_variables('df', None)
ss['selected_rows'] = initialize_variables('selected_rows', None)
ss['previous_selected_columns'] = initialize_variables('previous_selected_columns', [])
ss['previous_selected_values'] = initialize_variables('previous_selected_values', [])
ss['previous_selected_mode'] = initialize_variables('previous_selected_mode', '')
ss['previous_start_date'] = initialize_variables('previous_start_date', None)
ss['previous_end_date'] = initialize_variables('previous_end_date', None)
ss['average_cost_dict'] = initialize_variables('average_cost_dict', {})
ss['position_change_sql'] = initialize_variables('position_change_sql', '')
ss['saa_group_dict'] = initialize_variables('saa_group_dict', {})

def build_filters():
    """
    Build filters for the activity monitor page. This includes LBU, date, column and value filters.
    """
    
    with st.expander('Filters', True):
        dates = get_funnelweb_dates()

        build_date_filter_buttons('Valuation Date', dates, key='selected_date')
        build_date_filter_buttons('Comparison Date', dates, key='selected_comparison_date', date=ss['selected_date'])
        
        build_multi_select_filter('Columns', FILTER_COLUMNS, 'selected_columns', ['LBU Group', 'FWD Asset Type'], True)
        build_multi_select_filter('Values', FILTER_VALUES, 'selected_values', ['Notional', 'Net MV'], True)
        
        if all(item in ss['selected_values_converted'] for item in TRANSACTIONS_MODES):
            st.pills('Transactions Mode', [key for key in FILTER_VALUES if FILTER_VALUES[key] in TRANSACTIONS_MODES], selection_mode='single', default=[key for key in FILTER_VALUES if FILTER_VALUES[key] == TRANSACTIONS_MODES[0]], key='selected_mode')
            ss['selected_mode_converted'] = FILTER_VALUES[ss['selected_mode']]
        
    # Assign dates
    ss.start_date = ss['selected_comparison_date']
    ss.start_date_string = ss['selected_comparison_date_string']
    ss.end_date = ss['selected_date']
    ss.end_date_string = ss['selected_date_string']

def verify_load():        
    """
    Verifies whether the program should load data or not. This is based on the selected columns and values and if it was preloaded already.
    """
    load = False
    empty = False
    ss.preloaded = False

    # Not enough parameters selected
    if len(ss.selected_columns) == 0 or len(ss.selected_values) == 0:
        st.warning('Please select at least one column and one value!')
        ss['sql_statement'] = ''
        empty = True
    # All parameters are the same
    elif ss.start_date == ss.previous_start_date and ss.end_date == ss.previous_end_date and ss.selected_columns == ss.previous_selected_columns and ss.selected_values == ss.previous_selected_values:
        load = True
        if ss.selected_mode == ss.previous_selected_mode:
            ss.preloaded = True
    # Button to click, only shows when enough parameters are selected
    elif st.button('Load data'):
        load = True
        ss.preloaded = False

    if empty or not load:
        st.stop()
        
    ss.previous_selected_columns = ss.selected_columns
    ss.previous_selected_values = ss.selected_values
    ss.previous_selected_mode = ss.selected_mode

def get_data(bar):
    """
    Get all position data from Snowflake or from cache
    """
    
    ss.average_cost_dict['start'] = _get_average_costs(True)
    bar.progress(10, text="Getting data..")
    ss.average_cost_dict['end'] = _get_average_costs(False)
    bar.progress(20, text="Getting data..")
    df = _get_positions()
    
    ss.previous_start_date = ss.start_date
    ss.previous_end_date = ss.end_date
    ss.df = df

def _get_average_costs(select_start_date):        
    """
    Get average costs for each position up to that date
    Args:
        select_start_date (bool): If True, get average cost for start date, else get average cost for end date
    """
    
    #region Initialization and check existing in self
    
    if select_start_date:
        mode = 'start'
        date = ss.start_date
        comparison_date = ss.previous_start_date
    else:
        mode = 'end'
        date = ss.end_date
        comparison_date = ss.previous_end_date
    
    if comparison_date == date and mode in ss.average_cost_dict.keys():
        return ss.average_cost_dict[mode]
    
    #endregion
    
    #region Get Initial Prices
    
    average_cost_sql = f"WITH position_ids AS (SELECT DISTINCT position_id FROM funnelweb WHERE closing_date = '{date}' AND (is_bbg_fi = true or bbg_asset_type = 'Equity')), first_dates AS (SELECT f.position_id, min(closing_date) AS first_price_date FROM funnelweb f, position_ids p WHERE f.position_id = p.position_id AND clean_price != 0 GROUP BY f.position_id) SELECT f.position_id, f.security_name, clean_price, first_price_date FROM funnelweb f INNER JOIN first_dates fd ON f.position_id = fd.position_id AND f.closing_date = fd.first_price_date;"
    average_cost_df = query(average_cost_sql)
    first_prices = average_cost_df.set_index('POSITION_ID')['CLEAN_PRICE'].to_dict()
    
    #endregion
    
    #region Get all transactions
    
    transactions_sql = f"WITH position_ids AS (SELECT DISTINCT position_id FROM funnelweb WHERE closing_date = '{date}' AND (is_bbg_fi = true or bbg_asset_type = 'Equity')), history_data AS (SELECT f.position_id, closing_date, position, clean_price AS price, COALESCE(LAG(position) OVER (PARTITION BY f.position_id ORDER BY closing_date), 0) AS previous_position, COALESCE(LAG(price) OVER (PARTITION BY f.position_id ORDER BY closing_date), price) AS previous_price, position - previous_position AS position_change FROM funnelweb f, position_ids p WHERE f.position_id = p.position_id ORDER BY position_id, closing_date) SELECT position_id, closing_date, position, previous_price AS price, position_change FROM history_data WHERE position_change != 0 ORDER BY position_id, closing_date;"
    transactions_df = query(transactions_sql)
    
    #endregion
    
    #region Compute Average Cost
    
    average_costs = {}
    prev_position_id = None
    total_cost = 0
    first_transaction = True

    # Computes cost if increased position, stays the same if position is decreased
    for index, row in transactions_df.iterrows():
        position_id = row['POSITION_ID']
        position_change = row['POSITION_CHANGE']
        position = row['POSITION']
        purchase_price = row['PRICE']
        
        if position_id == '7303366916549640553':
            print()
        
        if position_id != prev_position_id:
            if prev_position_id != None:
                if total_cost == 0 or total_position == 0:
                    average_costs[prev_position_id] = 0
                else:
                    average_costs[prev_position_id] = total_cost / total_position
                    
                total_cost = 0
            
            if position != position_change:
                position_change = position
            
            first_transaction = True
            
        if position_change > 0 or first_transaction:
            if first_transaction and purchase_price == 0 and position_id in first_prices.keys():
                purchase_price = first_prices[position_id]
            
            purchase_cost = purchase_price * position_change
            total_cost += purchase_cost
        else:
            total_cost += total_cost / total_position * position_change
        
        prev_position_id = position_id
        total_position = position
        first_transaction = False
    
    average_costs[prev_position_id] = total_cost / total_position
    
    return average_costs
    
    #endregion

def _get_positions():
    """
    Get positions from Snowflake for start and end date
    """
    
    sql = _build_sql()
    
    if sql == ss.position_change_sql:
        return ss.position_change_df
    
    df = query(sql)
    
    fx_sql = _build_fx_sql()
    fx_df = query(fx_sql)
           
    df = _patch_data(df, fx_df)
        
    ss.position_change_sql = sql
    ss.position_change_df = df
    ss.preloaded = False
    
    return df

def _build_sql():
    """
    Build SQL query to get positions from Snowflake
    """
    
    start_date = ss.start_date
    end_date = ss.end_date
    
    default_condition = "position * unit * IFF(mtge_factor > 0, mtge_factor, 1) * IFF(principal_factor > 0, principal_factor, 1)"

    notional_usd_conditions = {"fwd_asset_type = 'Accreting notes'": f"sw_rec_notl_amt / rate",
                    "bbg_asset_type IN ('Multi-Leg Deal', 'Foreign Exchange Forward', 'Non Deliverable Swap', 'OIS Swap', 'Amort. Swap')": f"IFF(derivs_dollar_notional IS NULL, 0, derivs_dollar_notional)",
                    "bbg_asset_type IN ('Warrant', 'Index Option')": "position * unit * strike / rate"}

    notional_usd_case_sql = "CASE  \n" + '  \n'.join(f'WHEN {key} THEN {value}' for key, value in notional_usd_conditions.items()) + f"  \nELSE {default_condition} / rate" + "  \nEND AS notional_usd"

    fx_rate_sql = f"WITH fx_rates AS (SELECT fx, rate FROM supp.fx_rates WHERE valuation_date = '{end_date}')"

    sql = f"""{fx_rate_sql}  
    SELECT {", ".join(IDENTIFIER_COLUMNS)},  
    {", ".join(STATIC_COLUMNS)},  
    {", ".join(CHARACTERISTIC_COLUMNS)},
    {", ".join([f"{value} AS {key}" for key, value in FORMULA_COLUMNS.items()])},
    {notional_usd_case_sql} 
    FROM funnel.funnelweb AS fw
    LEFT JOIN fx_rates AS f1 ON fw.currency = f1.fx
    WHERE closing_date IN (\'{start_date}\', \'{end_date}\')
    ORDER BY closing_date;"""
    
    return sql

def _build_fx_sql():
    sql = f"SELECT valuation_date, fx, rate FROM supp.fx_rates WHERE valuation_date IN ('{ss.start_date}', '{ss.end_date}');"
    return sql

def _get_fx_rate(fx_df, date, fx):
    """
    Get FX rate for a specific date and FX pair
    """
    
    rate = fx_df[(fx_df['VALUATION_DATE'] == date) & (fx_df['FX'] == fx)]
    
    if not rate.empty:
        return rate.iloc[0]['RATE']
    
    return 1

def _patch_data(df, fx_df):
    """
    Converts closing date, calculates average cost, fixes notional USD for equities, applies L2 asset type to L3 asset type if blank, and merges all PineBridge custodies under one.
    """
    
    average_cost_dict = ss.average_cost_dict
    
    # Change date to string
    df['CLOSING_DATE'] = pd.to_datetime(df['CLOSING_DATE']).dt.strftime('%Y-%m-%d')
        
    # Apply average cost dictionary to dataframe
    df['AVERAGE_COST'] = df.apply(lambda row: average_cost_dict['start'][row['POSITION_ID']] if (row['POSITION_ID'] in average_cost_dict['start'] and row['CLOSING_DATE'] == ss.start_date_string) else (average_cost_dict['end'][row['POSITION_ID']] if (row['POSITION_ID'] in average_cost_dict['end'] and row['CLOSING_DATE'] == ss.end_date_string) else None), axis = 1)
    
    derivs = ['Multi-Leg Deal', 'Foreign Exchange Forward', 'Non Deliverable Swap', 'OIS Swap', 'Amort. Swap']

    # Fix notional usd for equities
    df.rename(columns={'NOTIONAL_USD': 'NOTIONAL_USD_OLD'}, inplace=True)
    df['NOTIONAL_USD'] = df.apply(lambda row: (row["POSITION"] * row["UNIT"] * row['AVERAGE_COST'] / row["RATE"] / (100 if row["CURRENCY"] == 'GBP' else 1)) if row['BBG_ASSET_TYPE'] == 'Equity' else row['NOTIONAL_USD_OLD'], axis=1)
    df['NOTIONAL_USD'] = df.apply(lambda row: (row['NOTIONAL_USD'] * _get_fx_rate(fx_df, ss.start_date_string, row['SW_REC_CRNCY']) / _get_fx_rate(fx_df, ss.end_date_string, row['SW_REC_CRNCY'])) if (row['BBG_ASSET_TYPE'] in derivs and row['CLOSING_DATE'] == ss.start_date_string) else row['NOTIONAL_USD'], axis=1)
    
    # Apply L2 asset type to L3 asset type is blank
    df['L3_ASSET_TYPE'] = df.apply(lambda row: row['L2_ASSET_TYPE'] if row['L3_ASSET_TYPE'] == 'None' else row['L3_ASSET_TYPE'], axis=1)
    # Send cash to cash account
    df['FWD_ASSET_TYPE'] = df.apply(lambda row: 'Cash' if row['BBG_ASSET_TYPE'] == 'Cash' else row['FWD_ASSET_TYPE'], axis=1)
    # Use L3 asset type for derivatives
    df['FWD_ASSET_TYPE'] = df.apply(lambda row: row['L3_ASSET_TYPE'] if row['L1_ASSET_TYPE'] == 'Derivatives' else row['FWD_ASSET_TYPE'], axis=1)
    # Send interim T bills to cash
    df['FWD_ASSET_TYPE'] = df.apply(lambda row: 'Cash' if (row['BBG_ASSET_TYPE'] == 'Treasury' and row['FWD_ASSET_TYPE'] != 'Sovereign Bonds') else row['FWD_ASSET_TYPE'], axis=1)
    
    # Merge all PineBridge custodies under one
    df['MANAGER'] = df.apply(lambda row: 'Pinebridge' if 'Pinebridge' in row['MANAGER'] else row['MANAGER'], axis=1)

    return df

#region Build Transactions

def compute_transactions():
    """
    Computes transactions for the selected date range. This includes purchases, addition to existing positions, sales, partial sales, prepayments.
    """
    
    if ss.preloaded:
        return
    
    df = ss.df
    
    #region Identify Transactions
    
    start_df = df[df['CLOSING_DATE'] == ss.start_date_string]
    end_df = df[df['CLOSING_DATE'] == ss.end_date_string]
    start_positions = start_df['POSITION_ID']
    end_positions = end_df['POSITION_ID']
    
    increase_columns = {}
    decrease_columns = {}
    
    def _compute_held_positions():
        """
        Computes held positions, including partial purchase / sales of existing positions and positions with changes in notional from prepayment.
        """
        
        held_positions = list(set(start_positions) & set(end_positions))
        
        start_held_df = start_df[start_df['POSITION_ID'].isin(held_positions)]
        end_held_df = end_df[end_df['POSITION_ID'].isin(held_positions)]
        
        # Calculate positions with difference in notional, whether it be from increasing / decreasing the position or from prepayment
        diff_df = pd.merge(start_held_df.filter(['POSITION_ID', 'SECURITY_NAME', 'BBG_ASSET_TYPE', 'FWD_ASSET_TYPE', 'NOTIONAL_USD', 'MTGE_FACTOR', 'PRINCIPAL_FACTOR', 'LAST_TRADE_DATE', 'POSITION']), end_held_df.filter(['POSITION_ID', 'NOTIONAL_USD', 'MTGE_FACTOR', 'PRINCIPAL_FACTOR', 'LAST_TRADE_DATE', 'POSITION']), on='POSITION_ID', suffixes=('_START', '_END'))
        diff_df['NOTIONAL_USD_CHANGE'] = diff_df['NOTIONAL_USD_END'] - diff_df['NOTIONAL_USD_START']
        diff_df['MTGE_FACTOR_CHANGE'] = diff_df['MTGE_FACTOR_END'] - diff_df['MTGE_FACTOR_START']
        diff_df['PRINCIPAL_FACTOR_CHANGE'] = diff_df['PRINCIPAL_FACTOR_END'] - diff_df['PRINCIPAL_FACTOR_START']
        diff_df = diff_df[(diff_df['NOTIONAL_USD_START'] != diff_df['NOTIONAL_USD_END']) & ((diff_df['LAST_TRADE_DATE_START'] != diff_df['LAST_TRADE_DATE_END']) | (diff_df['POSITION_START'] != diff_df['POSITION_END']) | (diff_df['MTGE_FACTOR_CHANGE'] != 0) | (diff_df['PRINCIPAL_FACTOR_CHANGE'] != 0) | (diff_df['BBG_ASSET_TYPE'] == 'Foreign Exchange Forward') | (diff_df['FWD_ASSET_TYPE'] == 'Accreting notes'))]
        
        # Positions added
        increased_df = diff_df[diff_df['NOTIONAL_USD_END'] > diff_df['NOTIONAL_USD_START']]
        increased_positions = dict(zip(increased_df['POSITION_ID'], increased_df['NOTIONAL_USD_CHANGE']))
        increase_columns["ADDITION"] = increased_positions
        
        # Positions sold partially
        decreased_df = diff_df[(diff_df['NOTIONAL_USD_END'] < diff_df['NOTIONAL_USD_START']) & (diff_df['MTGE_FACTOR_CHANGE'] == 0) & (diff_df['PRINCIPAL_FACTOR_CHANGE'] == 0)]
        decreased_positions = dict(zip(decreased_df['POSITION_ID'], -decreased_df['NOTIONAL_USD_CHANGE']))
        decrease_columns["SOLD PARTIALLY"] = decreased_positions
        
        # Positions with principal paid back
        prepay_df = diff_df[(diff_df['MTGE_FACTOR_CHANGE'] != 0) | (diff_df['PRINCIPAL_FACTOR_CHANGE'] != 0)]
        prepay_positions = dict(zip(prepay_df['POSITION_ID'], -prepay_df['NOTIONAL_USD_CHANGE']))
        decrease_columns["PREPAYMENTS"] = prepay_positions

    def _compute_sold_positions():
        """
        Computes sold positions, including positions that have matured and positions that have been sold entirely.
        """
        missing_positions = list(set(start_positions) - set(end_positions))
        missing_df = start_df[start_df['POSITION_ID'].isin(missing_positions)]

        # Positions that have run off
        matured_df = missing_df[missing_df['MATURITY'].dt.date <= ss.end_date]
        matured_positions = list(matured_df['POSITION_ID'])
        decrease_columns["MATURITIES"] = matured_positions
        
        # Positions that are sold entirely
        sold_df = missing_df[(missing_df['MATURITY'].isna()) | (missing_df['MATURITY'].dt.date > ss.end_date)]
        sold_positions = list(sold_df['POSITION_ID'])
        decrease_columns["SOLD ENTIRELY"] = sold_positions

    def _compute_new_positions():
        """
        Computes new positions, including purchases and positions that have been added to.
        """
        new_df = end_df[end_df['POSITION_ID'].isin(list(set(end_positions) - set(start_positions)))]
        new_positions = list(new_df['POSITION_ID'])
        increase_columns["PURCHASES"] = new_positions
        
    _compute_held_positions()
    _compute_sold_positions()
    _compute_new_positions()

    #endregion

    #region Build Transaction Columns
                        
    df = _build_transaction_columns(df, increase_columns, 1000000)
    df = _build_transaction_columns(df, decrease_columns, -1000000)

    ss.transaction_columns = [{"headerName": "Net Purchases", "children": _build_transaction_children(increase_columns)}, {"headerName": "Net Sales", "children": _build_transaction_children(decrease_columns)}, {"headerName": "Net Purchases / Sales", "children": _build_net_purchases_sales(increase_columns, decrease_columns)}]
    
    ss.transaction_column_headers = _build_transaction_headers(ss.transaction_columns)
    ss.df = df
    
    #endregion

def _build_transaction_columns(df, columns, divisor):
    """
    Build transaction columns for the grid. This includes purchases, addition to existing positions, sales, partial sales, prepayments.

    Args:
        columns (dict): THe columns to apply the logic to
        divisor (float): The divisor to divide the notionals by
    """
    
    transaction_mode = ss['selected_mode_converted']
    
    for key, value in columns.items():        
        if type(value) == list and transaction_mode == 'NOTIONAL_USD':
            df[key] = df.apply(lambda row: row["NOTIONAL_USD"] / divisor if row['POSITION_ID'] in value else 0, axis=1)
        elif type(value) == dict and transaction_mode == 'NOTIONAL_USD':
            df[key] = df.apply(lambda row: value[row['POSITION_ID']] / divisor if row['POSITION_ID'] in value.keys() and row['CLOSING_DATE'] == ss.start_date_string else 0, axis=1)
        elif type(value) == list and transaction_mode == 'NET_MV':
            df[key] = df.apply(lambda row: row["NET_MV"] / divisor if row['POSITION_ID'] in value else 0, axis=1)
        elif type(value) == dict and transaction_mode == 'NET_MV':
            df[key] = df.apply(lambda row: (value[row['POSITION_ID']] / row['NOTIONAL_USD'] * row['NET_MV']) / divisor if row['POSITION_ID'] in value.keys() and row['CLOSING_DATE'] == ss.start_date_string else 0, axis=1)
    
    return df
    
def _build_transaction_children(columns):
    """
    Build transaction children for the grid. This includes purchases, addition to existing positions, sales, partial sales, prepayments.
    Args:
        columns (dict): The columns to apply the logic to
    """
    children = []
    for column in columns:
        children.append({"headerName": column.title(), "field": column, "aggFunc": "sum", "valueFormatter": format_numbers()})
    
    delta_columns = "'] + params.data['".join(columns)
    
    deltaValueComparator = """
            function deltaValue(params) {
                return params.data['COLUMNS'];
            }
        """
        
    deltaValueComparator = deltaValueComparator.replace("COLUMNS", delta_columns)
    
    children.append({"headerName": "Total", "valueGetter": JsCode(deltaValueComparator), "aggFunc": "sum", "valueFormatter": format_numbers(), "cellStyle": conditional_formatting(-250, 0, 250)})
        
    return children

def _build_net_purchases_sales(increase_columns, decrease_columns):
    """
    Build net purchases / sales columns for the grid. This includes the total of net purchases and net sales.
    """
    
    delta_columns = "'] + params.data['".join(list(increase_columns.keys()) + list(decrease_columns.keys()))
    
    deltaValueComparator = """
            function deltaValue(params) {
                return parseFloat((params.data['COLUMNS']).toFixed(6));
            }
        """
        
    deltaValueComparator = deltaValueComparator.replace("COLUMNS", delta_columns)
    
    net = [{"headerName": "Total", "valueGetter": JsCode(deltaValueComparator), "aggFunc": "sum", "valueFormatter": format_numbers(), "cellStyle": conditional_formatting(-250, 0, 250)}]
        
    return net

def _build_transaction_headers(transaction_columns):
    """
    Build transaction headers for the grid. This includes the net purchases and net sales.
    """
    transaction_column_headers = {} 
    
    for transaction_type in transaction_columns:
        if 'children' not in transaction_type:
            continue
        
        children = []
        
        for child in transaction_type['children']:
            if 'field' not in child:
                continue
                        
            children.append(child['field'])
            
        transaction_column_headers[transaction_type['headerName']] = children
    
    return transaction_column_headers

#endregion

#region Build Value Columns

def build_value_columns():
    """
    Build value columns for the grid. This includes the start and end date values and the delta value.        
    """
    if ss.preloaded:
        return
    
    selected_values = ss.selected_values_converted
    df = ss.df
    
    start_columns = []
    end_columns = []
    delta_columns = []
    
    for column in selected_values:
        label = [column_name for column_name in FILTER_VALUES if FILTER_VALUES[column_name] == column][0]
        
        if column in FILTER_VALUES_SUM:
            (start_column, end_column, delta_column) = _build_sum_value_column(df, label, column, FILTER_VALUES_SUM[column])
        elif column in FILTER_VALUES_WA:
            (start_column, end_column, delta_column) = _build_weighted_average_value_column(df, label, column)
            
        start_columns.append(start_column)
        end_columns.append(end_column)
        delta_columns.append(delta_column)
            
    ss.value_columns = {ss.start_date_string: start_columns, ss.end_date_string: end_columns, 'Δ Delta': delta_columns}
    
def _build_sum_value_column(df, label, column, divisor):
    """
    Build sum value column for the grid. This includes the start and end date values and the delta value.
    Args:
        label (str): The label for the column
        column (str): The column to apply the logic to
        divisor (float): The divisor to divide the notionals by
    """
    
    df[column + '_START'] = df.apply(lambda row: row[column] / divisor if row['CLOSING_DATE'] == ss.start_date_string else 0, axis=1)
    df[column + '_END'] = df.apply(lambda row: row[column] / divisor if row['CLOSING_DATE'] == ss.end_date_string else 0, axis=1)
    
    start_column = {"headerName": label, "field": column + "_START", "aggFunc": "sum", "valueFormatter": format_numbers()}
    end_column = {"headerName": label, "field": column + "_END", "aggFunc": "sum", "valueFormatter": format_numbers()}
    
    deltaValueComparator = """
        function deltaValue(params) {
            return parseFloat((params.data.COLUMN_END - params.data.COLUMN_START).toFixed(6));
        }
    """
    
    deltaValueComparator = deltaValueComparator.replace("COLUMN", column)
    
    delta_column = {"headerName": label, "valueGetter": JsCode(deltaValueComparator), "aggFunc": "sum", "valueFormatter": format_numbers(), "cellStyle": conditional_formatting(-250, 0, 250)}
    
    return (start_column, end_column, delta_column)

def _build_weighted_average_value_column(df, label, column):
    """
    Build weighted average value column for the grid. This includes the start and end date values and the delta value.
    Args:
        label (str): The label for the column
        column (str): The column to apply the logic to
    """
    
    df[column + '_START'] = df.apply(lambda row: row[column] if row['CLOSING_DATE'] == ss.start_date_string else 0, axis=1)
    df[column + '_END'] = df.apply(lambda row: row[column] if row['CLOSING_DATE'] == ss.end_date_string else 0, axis=1)
    
    valueComparator = """
        function weightedAverage(params) {                        
            let totalWeight = 0;
            let weightedSum = 0;
            
            params.rowNode.allLeafChildren.forEach((value) => {
                let datapoint = value.data["COLUMN"];
                
                if (datapoint != 0) {
                    let weight = value.data["NET_MV"];
                    totalWeight += weight;
                    weightedSum += Math.abs(weight * datapoint) * (value.data["POSITION"] >= 0 ? 1 : -1);
                }
            });

            if (totalWeight > 0) {
                weightedSum /= totalWeight;
            }
            
            return weightedSum;
        }
    """
    
    startComparator = valueComparator.replace("COLUMN", column + "_START")
    endComparator = valueComparator.replace("COLUMN", column + "_END")
    
    start_column = {"headerName": label, "field": column + "_START", "aggFunc": JsCode(startComparator), "valueFormatter": format_numbers()}
    end_column = {"headerName": label, "field": column + "_END", "aggFunc": JsCode(endComparator), "valueFormatter": format_numbers()}
    
    deltaValueComparator = """
        function deltaValue(params) {                    
            let totalWeightStart = 0;
            let weightedSumStart = 0;
            let totalWeightEnd = 0;
            let weightedSumEnd = 0;
            
            params.rowNode.allLeafChildren.forEach((value) => {
                let datapoint = value.data["COLUMN_START"];
                
                if (datapoint != 0) {
                    let weight = value.data["NET_MV"];
                    totalWeightStart += weight;
                    weightedSumStart += Math.abs(weight * datapoint) * (value.data["POSITION"] >= 0 ? 1 : -1);
                }
                
                datapoint = value.data["COLUMN_END"];
                
                if (datapoint != 0) {
                    let weight = value.data["NET_MV"];
                    totalWeightEnd += weight;
                    weightedSumEnd += Math.abs(weight * datapoint) * (value.data["POSITION"] >= 0 ? 1 : -1);
                }
            });

            if (totalWeightStart > 0) {
                weightedSumStart /= totalWeightStart;
            }
            
            if (totalWeightEnd > 0) {
                weightedSumEnd /= totalWeightEnd;
            }
            
            return weightedSumEnd - weightedSumStart;
        }
    """
    
    deltaValueComparator = deltaValueComparator.replace("COLUMN", column)
    
    delta_column = {"headerName": label, "aggFunc": JsCode(deltaValueComparator), "valueFormatter": format_numbers(), "cellStyle": conditional_formatting(-250, 0, 250)}
    
    return (start_column, end_column, delta_column)

#endregion

def build_grid():
    """
    Build grid for the activity monitor page. This includes the grid columns, rows and filters.
    """
    df = ss.df
    selected_columns_converted = ss.selected_columns_converted
    
    value_columns = []  
    
    for date in [ss.start_date_string, ss.end_date_string]:
        for column in ss.value_columns[date]:
            value_columns.append(column['field'])
    
    grid_df = df.groupby(selected_columns_converted)[value_columns + [item for sublist in ss.transaction_column_headers.values() for item in sublist]].sum().reset_index()
    total_df = grid_df.groupby('FWD_ASSET_TYPE')[value_columns + [item for sublist in ss.transaction_column_headers.values() for item in sublist]].sum().reset_index()
    total_df['LBU_GROUP'] = 'Total'
    
    grid_df = pd.concat([grid_df, total_df], axis=0)
    
    grid = AgGridBuilder(grid_df, min_width=100)
    grid.add_options(group_total=None, row_selection={'mode': 'multiRow', 'groupSelects': 'filteredDescendants', 'checkboxLocation': 'autoGroupColumn', 'suppressRowClickSelection': False}, header_name=' / '.join(ss['selected_columns']), group_expanded=0)
    #grid.gb.configure_grid_options(groupDefaultExpanded=1, pivotMode=True, rowSelection={'mode': 'multiRow', 'groupSelects': 'filteredDescendants', 'checkboxLocation': 'autoGroupColumn', 'suppressRowClickSelection': False}, autoGroupColumnDef={'headerName': ' / '.join(ss['selected_columns']),'cellRendererParams': { 'suppressCount': 'true' }, 'pinned': 'left'}, suppressAggFuncInHeader=True, grandTotalRow='bottom')

    customOrderComparatorString = """
        function orderComparator(a, b, nodeA, nodeB) {                
            if (nodeA.id.includes("Total") && !nodeA.id.includes("Total Return") && !nodeB.id.includes("Total")) {
                return 1;
            } else if (!nodeA.id.includes("Total") && nodeB.id.includes("Total") && !nodeB.id.includes("Total Return")) {
                return -1;
            }
            
            let normalOrder = nodeA.aggData['{index}'] > nodeB.aggData['{index}'] ? 1 : -1;
            return normalOrder;
        }
    """

    index = ss.selected_values.index(ss.selected_mode) + 3
    customOrderComparatorString = customOrderComparatorString.replace("{index}", str(index))

    grid.add_columns(selected_columns_converted, value_formatter=None, sort='desc', comparator=customOrderComparatorString)
    
    for key, value in ss.value_columns.items():
        grid.gb.configure_column(key, children=value)
    
    grid.gb.configure_column('Transactions', children=ss.transaction_columns)
        
    grid.show_grid(update_on=[('selectionChanged', 2000)], update_mode="NO_UPDATE")
    
    ss.selected_rows = grid.grid['selected_rows']      

def build_analysis():        
    st.write('Select checkboxes to show details below. Loading may take some time...')
    
    if type(ss.selected_rows) != pd.DataFrame:
        return
            
    filtered_df = _build_filtered_dataframe()
    
    st.write("Click on bars to further filter, click another bar to swap or click white space to remove filters")
    
    (filtered_df, transaction_headers) = _build_transactions_toggle(filtered_df)
    
    #region Merge positions for start and end daate
    
    start_df = filtered_df[filtered_df['CLOSING_DATE'] == ss.start_date_string]
    start_positions = start_df['POSITION_ID']
    end_df = filtered_df[filtered_df['CLOSING_DATE'] == ss.end_date_string]
    end_positions = end_df['POSITION_ID']
    
    held_positions = list(set(start_positions) & set(end_positions))
    
    identifier_columns_upper = [column.upper() for column in IDENTIFIER_COLUMNS]
    identifier_columns_upper.remove('CLOSING_DATE')
    static_columns_upper = [column.upper() for column in STATIC_COLUMNS]
    characteristic_columns_upper = [column.upper() for column in CHARACTERISTIC_COLUMNS]
    characteristic_columns_upper.append('NOTIONAL_USD')
    formula_columns_upper = [column.upper() for column in FORMULA_COLUMNS.keys()]
    
    merged_df = pd.merge(start_df.filter(identifier_columns_upper + static_columns_upper + characteristic_columns_upper + formula_columns_upper + transaction_headers), end_df.filter(identifier_columns_upper + static_columns_upper + characteristic_columns_upper + formula_columns_upper + transaction_headers), on='POSITION_ID', suffixes=('_START', '_END'))
    merged_df = merged_df.drop(columns=[col + '_END' for col in identifier_columns_upper + static_columns_upper + formula_columns_upper if col != 'POSITION_ID'])
    merged_df = merged_df.rename(columns={col + '_START': col for col in identifier_columns_upper + static_columns_upper + formula_columns_upper if col != 'POSITION_ID'})
    
    for col in transaction_headers:
        merged_df[col] = merged_df[col + '_START'] + merged_df[col + '_END']
        merged_df = merged_df.drop(columns=[col + '_START', col + '_END'])
    
    columns_to_keep = identifier_columns_upper + static_columns_upper + characteristic_columns_upper + formula_columns_upper + transaction_headers
    
    sold_df = start_df[~start_df['POSITION_ID'].isin(held_positions)]
    sold_df = sold_df.drop(columns=[col for col in sold_df.columns if col not in columns_to_keep])
    sold_df = sold_df.rename(columns={col: col + '_START' for col in characteristic_columns_upper if col != 'POSITION_ID'})
    
    purchase_df = end_df[~end_df['POSITION_ID'].isin(held_positions)]
    purchase_df = purchase_df.drop(columns=[col for col in purchase_df.columns if col not in columns_to_keep])
    purchase_df = purchase_df.rename(columns={col: col + '_END' for col in characteristic_columns_upper if col != 'POSITION_ID'})
    
    merged_df = pd.merge(purchase_df, merged_df, on=list(purchase_df.columns), how='outer')
    merged_df = pd.merge(sold_df, merged_df, on=list(sold_df.columns), how='outer')
    
    merged_df = _join_saa_group(merged_df)
    
    #endregion
    
    #region Build charts
        
    analysis_columns = ['SAA_GROUP', 'FUND_CODE', 'FINAL_RATING_LETTER', 'COUNTRY_REPORT', 'MANAGER', 'MATURITY_RANGE', 'CURRENCY', 'L3_ASSET_TYPE']
    
    if merged_df['BBG_ASSET_TYPE'].isin(['Foreign Exchange Forward']).any():
        analysis_columns.append('CURRENCY_PAIR')
        
    if merged_df['BBG_ASSET_TYPE'].isin(['Mortgage Backed Security']).any():
        analysis_columns.append('SECURITIZED_CREDIT_TYPE')
    
    for column in analysis_columns:
        if column + '_END' in merged_df.columns:
            merged_df[column] = merged_df.apply(lambda row: row[column + "_END"] if pd.notna(row[column + "_END"]) else row[column + "_START"], axis=1)
            merged_df = merged_df.drop(columns=[column + '_START'])
    
    tab1, tab2, tab3 = st.tabs(["Net Purchases / Sales", "Net Purchases", "Net Sales"])
    
    transaction_column_headers = ss.transaction_column_headers
    
    with tab1:
        grid = AgGridBuilder(merged_df, min_width=100)
        grid.add_chart('stackedBar', analysis_columns, transaction_column_headers['Net Sales'] + transaction_column_headers['Net Purchases'], ' Net Purchases / Sales')
        grid.show_grid(update_mode='NO_UPDATE')
    with tab2:
        grid = AgGridBuilder(merged_df, min_width=100)
        grid.add_chart('stackedBar', analysis_columns, transaction_column_headers['Net Purchases'], ' Net Purchases')
        grid.show_grid(update_mode='NO_UPDATE')
    with tab3:
        grid = AgGridBuilder(merged_df, min_width=100)
        grid.add_chart('stackedBar', analysis_columns, transaction_column_headers['Net Sales'], ' Net Sales', True)
        grid.show_grid(update_mode='NO_UPDATE')
    
    #endregion

def _build_filtered_dataframe():
    selected_rows = ss.selected_rows
    df = ss.df
    selected_columns_converted = ss.selected_columns_converted
    
    unique_pairs = selected_rows[selected_columns_converted].drop_duplicates()
    unique_pairs_str = unique_pairs.apply(lambda row: ': '.join(row.values.astype(str)), axis=1).str.cat(sep=', ')
    st.write("Currently showing analysis for " + unique_pairs_str)
    
    filtered_df = pd.merge(df, unique_pairs, on=selected_columns_converted)
    
    return filtered_df

def _build_transactions_toggle(filtered_df):
    """
    Toggle whether to show positions with transactions only or not.
    """
    transaction_headers = [item for value in ss.transaction_column_headers.values() for item in value]
            
    if st.toggle("Include transactions only", True):
        transactions_positions = filtered_df[filtered_df[transaction_headers].any(axis=1)]['POSITION_ID']
        filtered_df = filtered_df[filtered_df['POSITION_ID'].isin(transactions_positions)]
            
    return (filtered_df, transaction_headers)

def _join_saa_group(df):
    ss.saa_group_dict = saa_group_dict = _build_saa_group_mapping()
    df['SAA_GROUP'] = df.apply(lambda row: saa_group_dict[row['FUND_CODE']], axis=1)
    
    return df
    
def _build_saa_group_mapping():
    if len(ss.saa_group_dict) == 0:
        df = query("SELECT short_name, saa_group, lbu_group FROM supp.fund f, supp.lbu l WHERE f.lbu = l.name;")
    else:
        return ss.saa_group_dict
    
    df['SAA_GROUP'] = df.apply(lambda row: ('Shareholder' if row['LBU_GROUP'] == 'HK' else row['SHORT_NAME']) if row['SAA_GROUP'] == 'None' else row['SAA_GROUP'], axis=1)
    
    saa_group_dict = dict(zip(df['SHORT_NAME'], df['SAA_GROUP']))
    
    return saa_group_dict

build_filters()

verify_load()

bar = st.progress(0, text="Getting data..")
get_data(bar)
bar.progress(40, text="Computing transactions...")
compute_transactions()
bar.progress(60, text="Computing values...")
build_value_columns()
bar.progress(70, text="Building grid...")
build_grid()
st.write('The stated FWD asset type is overriden, BBG_ASSET_TYPE = "Cash" will be assigned to "Cash" FWD Asset Type, L1_ASSET_TYPE = "Derivatives" will be using the actual L3 Asset Type.')
st.write('_The page may freeze if there are too many datapoints, to solve the issue close the tab and reopen._')
st.write('')
bar.progress(80, text="Plotting analysis...")
build_analysis()
bar.progress(100, text="Done...")
bar.empty()