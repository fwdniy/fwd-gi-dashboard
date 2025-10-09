import streamlit as st
from streamlit import session_state as ss
import pandas as pd
from grid import AgGridBuilder

ANALYSIS_COLUMNS = ['SAA_GROUP', 'FUND_CODE', 'FINAL_RATING_LETTER', 'COUNTRY_REPORT', 'MANAGER', 'MATURITY_RANGE', 'CURRENCY', 'L3_ASSET_TYPE']

@st.fragment
def build_analysis(config, df, selected_rows, selected_columns, trans_col_headers):
    """ Build analysis section below the grid based on selected rows in the grid. """
    st.write('Select checkboxes to show details below. Loading may take some time...')
    
    if type(selected_rows) != pd.DataFrame:
        return
    
    # Build filtered dataframe
    f_df = _build_filtered_dataframe(df, selected_rows, selected_columns)
    
    st.write("Click on bars to further filter, click another bar to swap or click white space to remove filters")
    
    # Create toggle to show transactions only or all holdings
    f_df, transaction_headers = _build_transactions_toggle(f_df, trans_col_headers)
    
    if len(f_df) == 0:
        st.warning("No transactions found for the selected filters and date range.")
        return
    
    start_df, end_df = _get_start_end_positions(f_df)
        
    held_df = _build_held_positions(config, start_df, end_df, transaction_headers)
    
    merged_df = _build_purchase_sale_positions(config, start_df, end_df, transaction_headers, held_df)
    
    # Add SAA Group
    merged_df = _join_saa_group(merged_df)
    
    analysis_columns = _build_analysis_columns(merged_df)
    
    for column in analysis_columns:
        if column + '_END' in merged_df.columns:
            merged_df[column] = merged_df.apply(lambda row: row[column + "_END"] if pd.notna(row[column + "_END"]) else row[column + "_START"], axis=1)
            merged_df = merged_df.drop(columns=[column + '_START'])
    
    # Add charts and show grid                
    grid = AgGridBuilder(merged_df, min_width=100)
    grid.add_columns(['POSITION_ID', 'SECURITY_NAME', 'BBGID_V2'], None, row_group=False)
    grid.add_chart('stackedBar', analysis_columns, trans_col_headers['Net Sales'] + trans_col_headers['Net Purchases'], ' Net Purchases / Sales')
    grid.show_grid(update_mode='MODEL_CHANGED', key='net_transactions', reload_data=True)

def _build_filtered_dataframe(df, selected_rows, selected_columns):
    """Builds dataframe filtered for selected rows and columns"""
    unique_pairs = selected_rows[selected_columns].dropna().drop_duplicates()
    unique_pairs_str = unique_pairs.apply(lambda row: ': '.join(row.values.astype(str)), axis=1).str.cat(sep=', ')
    st.write("Currently showing analysis for " + unique_pairs_str)
    
    unique_pairs_total = unique_pairs[unique_pairs['LBU_GROUP'] == 'Total']

    filtered_df = df[
        df[selected_columns].apply(tuple, axis=1).isin(unique_pairs.apply(tuple, axis=1)) |
        df['FWD_ASSET_TYPE'].isin(unique_pairs_total['FWD_ASSET_TYPE'])
    ]
   
    return filtered_df

def _build_transactions_toggle(df, transaction_column_headers):
    """Toggle whether to show positions with transactions only or not."""
    transaction_headers = [item for value in transaction_column_headers.values() for item in value]
            
    if st.toggle("Include transactions only", True):
        transactions_positions = df[df[transaction_headers].any(axis=1)]['POSITION_ID']
        df = df[df['POSITION_ID'].isin(transactions_positions)]
            
    return (df, transaction_headers)

def _get_start_end_positions(df):
    """Split dataframe into start and end date dataframes"""
    start_date = ss.start_date_string
    end_date = ss.end_date_string
    
    start_df = df[df['CLOSING_DATE'] == start_date]
    end_df = df[df['CLOSING_DATE'] == end_date]
    
    return start_df, end_df

@st.cache_data
def _build_config_lists(config):
    """Build lists of columns from config"""
    identifier_columns = [column.upper() for column in config.IDENTIFIER_COLUMNS]
    identifier_columns.remove('CLOSING_DATE')
    static_columns = [column.upper() for column in config.STATIC_COLUMNS]
    characteristic_columns = [column.upper() for column in config.CHARACTERISTIC_COLUMNS]
    characteristic_columns.append('NOTIONAL_USD')
    formula_columns = [column.upper() for column in config.FORMULA_COLUMNS.keys()]
    
    return identifier_columns, static_columns, characteristic_columns, formula_columns

def _build_held_positions(config, start_df, end_df, transaction_headers):
    """Get positions held throughout the period and aggregate transactions"""
    identifier_columns, static_columns, characteristic_columns, formula_columns = _build_config_lists(config)
    
    # Merge start and end df together stitched by position id with suffixes
    held_df = pd.merge(start_df.filter(identifier_columns + static_columns + characteristic_columns + formula_columns + transaction_headers), 
                         end_df.filter(identifier_columns + static_columns + characteristic_columns + formula_columns + transaction_headers), 
                         on='POSITION_ID', 
                         suffixes=('_START', '_END'))
    
    # Remove duplicate static columns with 'end' and remove 'start' from these column names
    held_df = held_df.drop(columns=[col + '_END' for col in identifier_columns + static_columns + formula_columns if col != 'POSITION_ID'])
    held_df = held_df.rename(columns={col + '_START': col for col in identifier_columns + static_columns + formula_columns if col != 'POSITION_ID'})
    
    # Merge transactions
    for col in transaction_headers:
        held_df[col] = held_df[col + '_START'] + held_df[col + '_END']
        held_df = held_df.drop(columns=[col + '_START', col + '_END'])
        
    return held_df

def _build_purchase_sale_positions(config, start_df, end_df, transaction_headers, held_df):
    """Get positions that were purchased or sold during the period"""
    identifier_columns, static_columns, characteristic_columns, formula_columns = _build_config_lists(config)
    columns_to_keep = identifier_columns + static_columns + characteristic_columns + formula_columns + transaction_headers
    held_positions = list(held_df['POSITION_ID'].unique())
    
    # Create purchases dataframe
    purchase_df = end_df[~end_df['POSITION_ID'].isin(held_positions)]
    purchase_df = purchase_df.drop(columns=[col for col in purchase_df.columns if col not in columns_to_keep])
    purchase_df = purchase_df.rename(columns={col: col + '_END' for col in characteristic_columns if col != 'POSITION_ID'})
    
    # Create sales dataframe
    sale_df = start_df[~start_df['POSITION_ID'].isin(held_positions)]
    sale_df = sale_df.drop(columns=[col for col in sale_df.columns if col not in columns_to_keep])
    sale_df = sale_df.rename(columns={col: col + '_START' for col in characteristic_columns if col != 'POSITION_ID'})
    
    # Merge sale and purchases dataframe with held positions
    merged_df = pd.merge(purchase_df, held_df, on=list(purchase_df.columns), how='outer')
    merged_df = pd.merge(sale_df, merged_df, on=list(sale_df.columns), how='outer')
    
    return merged_df

def _join_saa_group(df):
    """Join SAA Group information to dataframe"""
    saa_group_dict = _build_saa_group_mapping()
    df['SAA_GROUP'] = df['FUND_CODE'].map(saa_group_dict)
    
    return df

@st.cache_data
def _build_saa_group_mapping():
    """Build mapping of fund short name to SAA group"""
    df = ss.snowflake.query("SELECT short_name, saa_group, lbu_group FROM supp.fund f, supp.lbu l WHERE f.lbu = l.name;")
    
    df['SAA_GROUP'] = df.apply(lambda row: ('Shareholder' if row['LBU_GROUP'] == 'HK' else row['SHORT_NAME']) if row['SAA_GROUP'] == 'None' else row['SAA_GROUP'], axis=1)
    
    saa_group_dict = dict(zip(df['SHORT_NAME'], df['SAA_GROUP']))
    
    return saa_group_dict

def _build_analysis_columns(df):
    """Build list of columns to show in analysis grid based on assets"""
    analysis_columns = [column for column in ANALYSIS_COLUMNS]
    
    if df['BBG_ASSET_TYPE'].isin(['Foreign Exchange Forward']).any():
        analysis_columns.append('CURRENCY_PAIR')
        
    if df['BBG_ASSET_TYPE'].isin(['Mortgage Backed Security']).any():
        analysis_columns.append('SECURITIZED_CREDIT_TYPE')
    
    if len(df['FUND_GEO_FOCUS'].unique()) > 1:
        analysis_columns.append('FUND_GEO_FOCUS')
    
    if len(df['UNDERLYING_SECURITY_NAME'].unique()) > 1:
        analysis_columns.append('UNDERLYING_SECURITY_NAME')
        
    if len(df['ISSUER'].unique()) <= 50:
        analysis_columns.append('ISSUER')
    
    return analysis_columns