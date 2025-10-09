import streamlit as st
from streamlit import session_state as ss
import pandas as pd
import numpy as np
from st_aggrid import JsCode
from grid.formatting import format_numbers, conditional_formatting

#@st.cache_data(show_spinner=False)
def compute_transactions(df):
    """Compute transactions for specific types in the grid"""
    increase_columns = {}
    decrease_columns = {}
    
    increase_columns["ADDITION"], decrease_columns["SOLD PARTIALLY"], decrease_columns["PREPAYMENTS"] = _compute_held_positions(df)
    decrease_columns["MATURITIES"], decrease_columns["SOLD ENTIRELY"] = _compute_sold_positions(df)
    increase_columns["PURCHASES"] = _compute_new_positions(df)
    
    _build_transaction_columns(df, increase_columns, 1_000_000)
    _build_transaction_columns(df, decrease_columns, -1_000_000)
    
    trans_cols = [
        {
            "headerName": "Net Purchases", 
            "children": _build_transaction_children(increase_columns)
        }, {
            "headerName": "Net Sales", 
            "children": _build_transaction_children(decrease_columns)
        }, {
            "headerName": "Net Purchases / Sales", 
            "children": _build_net_transactions(increase_columns, decrease_columns)
        }
    ]
    
    trans_col_headers = _build_transaction_headers(trans_cols)
    
    #zipped_headers = [list(t) for t in zip(*trans_col_headers.values())]
    
    #df['TOTAL_TRANSACTIONS'] = [sum(row) for row in zip(*[df[col] for col in zipped_headers])]
    
    return df, trans_cols, trans_col_headers

@st.cache_data(show_spinner=False)
def _build_start_end_data(df):
    """Get start and end dataframes for the selected date range"""
    start_date = ss.start_date_string
    end_date = ss.end_date_string
    
    start_df = df[df['CLOSING_DATE'] == start_date]
    end_df = df[df['CLOSING_DATE'] == end_date]
    start_positions = start_df['POSITION_ID']
    end_positions = end_df['POSITION_ID']
    
    return start_df, end_df, start_positions, end_positions

def _compute_held_positions(df):
    """Computes held positions, including partial purchase / sales of existing positions and positions with changes in notional from prepayment."""
    start_df, end_df, _, _ = _build_start_end_data(df)
    
    # Merge start and end data
    diff_df = pd.merge(
        start_df[['POSITION_ID', 'SECURITY_NAME', 'BBG_ASSET_TYPE', 'FWD_ASSET_TYPE', 
                 'NOTIONAL_USD', 'MTGE_FACTOR', 'PRINCIPAL_FACTOR', 'LAST_TRADE_DATE', 'POSITION']],
        end_df[['POSITION_ID', 'NOTIONAL_USD', 'MTGE_FACTOR', 'PRINCIPAL_FACTOR', 
                'LAST_TRADE_DATE', 'POSITION']],
        on='POSITION_ID',
        suffixes=('_START', '_END')
    )
    
    # Calculate changes using vectorized operations
    diff_df['NOTIONAL_USD_CHANGE'] = diff_df['NOTIONAL_USD_END'] - diff_df['NOTIONAL_USD_START']
    diff_df['MTGE_FACTOR_CHANGE'] = diff_df['MTGE_FACTOR_END'] - diff_df['MTGE_FACTOR_START']
    diff_df['PRINCIPAL_FACTOR_CHANGE'] = diff_df['PRINCIPAL_FACTOR_END'] - diff_df['PRINCIPAL_FACTOR_START']
    
    # Filter changes
    changed_mask = (
        (diff_df['NOTIONAL_USD_START'] != diff_df['NOTIONAL_USD_END']) & 
        ((diff_df['LAST_TRADE_DATE_START'] != diff_df['LAST_TRADE_DATE_END']) |
         (diff_df['POSITION_START'] != diff_df['POSITION_END']) |
         (diff_df['MTGE_FACTOR_CHANGE'] != 0) |
         (diff_df['PRINCIPAL_FACTOR_CHANGE'] != 0) |
         (diff_df['BBG_ASSET_TYPE'] == 'Foreign Exchange Forward') |
         (diff_df['FWD_ASSET_TYPE'] == 'Accreting notes'))
    )
    diff_df = diff_df[changed_mask]
    
    # Calculate positions in one go
    increased_positions = diff_df.loc[diff_df['NOTIONAL_USD_END'] > diff_df['NOTIONAL_USD_START'], 
                                    ['POSITION_ID', 'NOTIONAL_USD_CHANGE']].set_index('POSITION_ID')['NOTIONAL_USD_CHANGE'].to_dict()
    
    decreased_mask = ((diff_df['NOTIONAL_USD_END'] < diff_df['NOTIONAL_USD_START']) & 
                     (diff_df['MTGE_FACTOR_CHANGE'] == 0) & 
                     (diff_df['PRINCIPAL_FACTOR_CHANGE'] == 0))
    decreased_positions = diff_df.loc[decreased_mask, 
                                    ['POSITION_ID', 'NOTIONAL_USD_CHANGE']].set_index('POSITION_ID')['NOTIONAL_USD_CHANGE'].map(lambda x: -x).to_dict()
    
    prepay_mask = ((diff_df['MTGE_FACTOR_CHANGE'] != 0) | 
                   (diff_df['PRINCIPAL_FACTOR_CHANGE'] != 0))
    prepay_positions = diff_df.loc[prepay_mask, 
                                  ['POSITION_ID', 'NOTIONAL_USD_CHANGE']].set_index('POSITION_ID')['NOTIONAL_USD_CHANGE'].map(lambda x: -x).to_dict()
    
    return increased_positions, decreased_positions, prepay_positions

def _compute_sold_positions(df):
    """Computes sold positions, including positions that have matured and positions that have been sold entirely."""
    start_df, end_df, start_positions, end_positions = _build_start_end_data(df)
    
    missing_positions = list(set(start_positions) - set(end_positions))
    missing_df = start_df[start_df['POSITION_ID'].isin(missing_positions)]

    # Positions that have run off
    matured_df = missing_df[missing_df['MATURITY'].dt.date <= ss.end_date]
    matured_positions = list(matured_df['POSITION_ID'])
    
    # Positions that are sold entirely
    sold_df = missing_df[(missing_df['MATURITY'].isna()) | (missing_df['MATURITY'].dt.date > ss.end_date)]
    sold_positions = list(sold_df['POSITION_ID'])
    
    return matured_positions, sold_positions

def _compute_new_positions(df):
    """Computes new positions, including purchases and positions that have been added to."""
    start_df, end_df, start_positions, end_positions = _build_start_end_data(df)
    
    new_df = end_df[end_df['POSITION_ID'].isin(list(set(end_positions) - set(start_positions)))]
    new_positions = list(new_df['POSITION_ID'])
    
    return new_positions

def _build_transaction_columns(df, columns, divisor):
    """
    Build transaction columns for the grid. This includes purchases, addition to existing positions, sales, partial sales, prepayments.

    Args:
        df: DataFrame containing the transaction data
        columns: Dictionary of column names and their corresponding position data
        divisor: Value to scale the notionals (typically 1_000_000 for millions)
    """
    transaction_mode = ss['selected_mode_converted']
    
    for key, value in columns.items():
        if isinstance(value, list):
            mask = df['POSITION_ID'].isin(value)
            df[key] = np.where(mask, df[transaction_mode] / divisor, 0)
        elif isinstance(value, dict):            
            start_date = ss.start_date_string
            start_date_mask = (df['CLOSING_DATE'] == start_date)
            position_mask = df['POSITION_ID'].isin(value.keys())
            combined_mask = start_date_mask & position_mask
            
            df[key] = np.where(combined_mask, df['POSITION_ID'].map(value) / divisor, 0)
            
            if transaction_mode == 'NET_MV':
                df[key] = np.where(combined_mask, (df[key] / df['NOTIONAL_USD'] * df['NET_MV']), 0)

            # Handle NaN values
            df[key] = df[key].fillna(0)

def _build_transaction_children(columns):
    """Build transaction children for the grid."""
    children = []
    
    for column in columns:
        children.append({
            "headerName": column.title(), 
            "field": column, 
            "aggFunc": "sum", 
            "valueFormatter": format_numbers()
        })
            
    deltaValueComparator = """
            function deltaValue(params) {
                return params.data['COLUMNS'];
            }
        """
    
    delta_columns = "'] + params.data['".join(columns)
    deltaValueComparator = deltaValueComparator.replace("COLUMNS", delta_columns)
    
    children.append({
        "headerName": "Total", 
        "valueGetter": JsCode(deltaValueComparator), 
        "aggFunc": "sum", 
        "valueFormatter": format_numbers(), 
        "cellStyle": conditional_formatting(lower_bound=-250, mid_point=0, upper_bound=250)
    })
        
    return children

def _build_net_transactions(increase_columns, decrease_columns):
    """Build net purchases / sales columns for the grid. This includes the total of net purchases and net sales."""
        
    deltaValueComparator = """
            function deltaValue(params) {
                return parseFloat((params.data['COLUMNS']).toFixed(6));
            }
        """
    
    delta_columns = "'] + params.data['".join(list(increase_columns.keys()) + list(decrease_columns.keys()))    
    deltaValueComparator = deltaValueComparator.replace("COLUMNS", delta_columns)
    
    net = {
        "headerName": "Total", 
        "valueGetter": JsCode(deltaValueComparator), 
        "aggFunc": "sum", 
        "valueFormatter": format_numbers(), 
        "cellStyle": conditional_formatting(lower_bound=-250, mid_point=0, upper_bound=250)
    }
    
    return [net]

def _build_transaction_headers(transaction_columns):
    """Build transaction headers for the grid. This includes the net purchases and net sales."""
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