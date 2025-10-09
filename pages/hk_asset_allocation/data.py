import streamlit as st
from streamlit import session_state as ss
import pandas as pd
from .grid import build_grid_bbg, build_grid_sum, build_grid_wa, build_grid_ratings, build_grid_nr
from db.data.data_shipment import get_lbu_data_hk
from db.data.lbu import FUND_CODE, HK_CODE, SUB_LBU

# Constants
CURRENT_DATE_LABEL = 'Current Date'
COMPARISON_DATE_LABEL = 'Comparison Date'
TOTAL_LABEL = 'Total'
SUM_VALUE_HEADERS = {
        'Net MV': ('SUM_NET_MV', 'SUM(NET_MV) / 1000000 AS SUM_NET_MV'),
        'DV01': ('SUM_DV01', 'SUM(DV01_000) / 1000 AS SUM_DV01'),
        'CS01': ('SUM_CS01', 'SUM(CS01_000) / 100 AS SUM_CS01')
    }
WA_VALUE_HEADERS = {'Credit Spread': 'CREDIT_SPREAD_BP', 'Duration': 'DURATION', 'YTM': 'YTM', 'WARF': 'WARF'}
ENTITY_CODES = {'Bermuda': 'HK', 'Hong Kong': 'ML', 'Macau': 'MC', 'Assurance': 'MH'}


def verify_to_load():
    """Verify user selections and load data if all checks pass"""    
    if not st.button('Load Data'):
        st.stop()
    
    fund_codes = ss.get('selected_funds')
        
    if not fund_codes:
        st.warning("Please select at least one fund.")
        st.stop()
        
    tabs = ss.get('selected_tab')
    
    if len(tabs) == 0:
        st.warning("Please select at least one view.")
        st.stop()

def _build_query(columns, values, add_comparison_date=False):    
    current_date = ss.selected_date
    comparison_date = ss.selected_comparison_date
    fund_codes = ss.selected_funds
    
    dates = f"'{current_date}'"
    if add_comparison_date:
        dates = f"'{current_date}', '{comparison_date}'"

    fund_codes_string = "', '".join(fund_codes)

    return (
        f"SELECT closing_date, {columns}, {values} "
        f"FROM funnelweb "
        f"WHERE closing_date IN ({dates}) AND fund_code IN ('{fund_codes_string}') "
        f"GROUP BY closing_date, {columns} "
        f"ORDER BY closing_date, {columns};"
    )

def _calculate_percentages(df, current_col, comparison_col):
    """Calculate percentage columns and deltas."""
    df['Delta Δ'] = df[current_col] - df[comparison_col]
    df['Current %'] = (df[current_col] / df[current_col].sum()) * 100
    df['Comparison %'] = (df[comparison_col] / df[comparison_col].sum()) * 100
    df['Delta Δ %'] = df['Current %'] - df['Comparison %']
    return df

def _add_total_row(df, label_col):
    """Add a total row to the DataFrame."""
    total_row = pd.DataFrame(df.sum(numeric_only=True)).T
    total_row[label_col] = TOTAL_LABEL
    return pd.concat([df, total_row], ignore_index=True)

@st.fragment
def get_bbg_asset_type_allocation():
    """Get allocation by Bloomberg Asset Type."""
    st.write('Net MV by Bloomberg Asset Type')

    columns = 'BBG_ASSET_TYPE'
    values = 'SUM(NET_MV) / 1000000 AS SUM_NET_MV'

    sql = _build_query(columns, values, add_comparison_date=True)
    df = ss.snowflake.query(sql)

    # Transform DataFrame
    current_date = ss.selected_date
    comparison_date = ss.selected_comparison_date
    
    df['CLOSING_DATE'] = df['CLOSING_DATE'].dt.date.replace({
        current_date: CURRENT_DATE_LABEL,
        comparison_date: COMPARISON_DATE_LABEL
    })
    
    df = df.pivot(index='BBG_ASSET_TYPE', columns='CLOSING_DATE', values='SUM_NET_MV')
    df = df[[CURRENT_DATE_LABEL, COMPARISON_DATE_LABEL]].fillna(0).reset_index()
    df.rename(columns={'BBG_ASSET_TYPE': 'Bloomberg Asset Type'}, inplace=True)

    # Calculate percentages and deltas
    df = _calculate_percentages(df, CURRENT_DATE_LABEL, COMPARISON_DATE_LABEL)

    # Add total row
    df = _add_total_row(df, 'Bloomberg Asset Type')

    build_grid_bbg(df)

def _get_sum_df(sql=None):
    if sql is None:
        columns = ['FUND_CODE', 'FWD_ASSET_TYPE']
        sql = _build_query(', '.join(columns), 'SUM(NET_MV) / 1000000 AS SUM_NET_MV')
    
    df = ss.snowflake.query(sql)
    
    return df

def _map_entity_hk_code(df):
    lbu_df = ss['lbu_df_hk']
    
    entity_map = dict(zip(lbu_df[FUND_CODE], lbu_df[SUB_LBU]))
    hk_code_map_raw = dict(zip(lbu_df[FUND_CODE], lbu_df[HK_CODE]))
    hk_code_values = list(hk_code_map_raw.values())
    
    hk_code_map = {}
    
    for key, value in hk_code_map_raw.items():
        hk_code = value
        
        if hk_code_values.count(value) > 1:
            hk_code = f'{value} ({ENTITY_CODES[entity_map[key]]})'
                
        hk_code_map[key] = hk_code
    
    df['ENTITY'] = df['FUND_CODE'].map(entity_map)
    df['HK_CODE'] = df['FUND_CODE'].map(hk_code_map)
    
    return df

@st.fragment
def build_sum_by_fwd_asset_type(modes):
    original_modes = modes
    
    if isinstance(modes, str):
        modes = [modes]
    
    if 'Net MV' not in modes:
        modes.append('Net MV')

    columns = ['FUND_CODE', 'FWD_ASSET_TYPE']
    value_headers = {key: value for key, value in SUM_VALUE_HEADERS.items() if key in modes}

    # Build SQL query and fetch data
    sql = _build_query(', '.join(columns), ', '.join(v[1] for v in value_headers.values()))
    df = _get_sum_df(sql)

    # Map ENTITY and HK_CODE
    df = _map_entity_hk_code(df)

    # Reorder columns
    column_order = ['ENTITY', 'HK_CODE', 'FWD_ASSET_TYPE'] + [v[0] for v in value_headers.values()]
    df = df[column_order]

    # Build grids for each value header
    for header, (value_column, _) in value_headers.items():
        if header not in original_modes:
            continue
        
        st.write(f'{header} by FWD Asset Type')
        build_grid_sum(df, value_column, header)

def _build_query_wa(columns, field, weight_field, additional_filter, current_date, fund_codes):
    fund_codes_string = "', '".join(fund_codes)

    sql = f"""WITH mvs AS (SELECT {columns}, sum(net_mv) AS sum_net_mv FROM funnelweb WHERE closing_date = '{current_date}' AND fund_code IN ('{fund_codes_string}') AND {field} <> 0{additional_filter} GROUP BY {columns} ORDER BY {columns}), 
    weight AS (SELECT {columns}, sum({field} * net_mv) AS {weight_field} FROM funnelweb WHERE closing_date = '{current_date}' AND fund_code IN ('{fund_codes_string}') {additional_filter} GROUP BY {columns} ORDER BY {columns})
    SELECT weight.fund_code, weight.fwd_asset_type, COALESCE(sum_net_mv, 0) AS sum_net_mv, COALESCE({weight_field}, 0) AS {weight_field} FROM weight LEFT JOIN mvs ON mvs.fund_code = weight.fund_code AND mvs.fwd_asset_type = weight.fwd_asset_type;"""

    return sql

@st.fragment
def build_wa_by_fwd_asset_type(modes):
    original_modes = modes
    
    if isinstance(modes, str):
        modes = [modes]
        
    if 'Net MV' not in modes:
        modes.append('Net MV')
    
    columns = ['FUND_CODE', 'FWD_ASSET_TYPE']
    value_headers = {key: value for key, value in WA_VALUE_HEADERS.items() if key in modes}
    additional_filters = {'WARF': ' AND bbg_asset_type NOT IN (\'Bond Option\', \'Repo Liability\')'}
    sum_df = _get_sum_df()
    sum_df = _map_entity_hk_code(sum_df)

    current_date = ss.selected_date
    fund_codes = ss.selected_funds

    for header, value_column in value_headers.items():
        if header not in original_modes:
            continue

        st.write(f'{header} by FWD Asset Type')
        
        additional_filter = ''
        
        if value_column in additional_filters.keys():
            additional_filter = additional_filters[value_column]
        
        sql = _build_query_wa(', '.join(columns), value_column, 'SUMPRODUCT', additional_filter, current_date, fund_codes)
        df = ss.snowflake.query(sql)

        df = _map_entity_hk_code(df)
        column_order = ['ENTITY', 'HK_CODE', 'FWD_ASSET_TYPE', 'SUM_NET_MV', 'SUMPRODUCT']
        df = df[column_order]


        build_grid_wa(df, sum_df, header)

@st.fragment
def build_ratings_profile():
    current_date = ss.selected_date
    fund_codes = ss.selected_funds
    fund_codes_string = "', '".join(fund_codes)

    sql = f"SELECT fund_code, index, final_rating, sum(net_mv) / 1000000 AS sum_net_mv FROM funnelweb, supp.ratings_ladder WHERE closing_date = '{current_date}' AND fund_code IN ('{fund_codes_string}') AND funnelweb.warf <> 0 AND final_rating = rating GROUP BY fund_code, index, final_rating ORDER BY index;"
    df = ss.snowflake.query(sql)
    
    df = _map_entity_hk_code(df)
    column_order = ['ENTITY', 'HK_CODE', 'FINAL_RATING', 'SUM_NET_MV']
    df = df[column_order]
    
    build_grid_ratings(df)

@st.fragment
def build_nr_table():
    current_date = ss.selected_date
    fund_codes = ss.selected_funds
    fund_codes_string = "', '".join(fund_codes)
    
    sql = f"""WITH mvs AS (SELECT security_name, sum(net_mv) AS sum_net_mv, ROW_NUMBER() OVER (ORDER BY sum_net_mv DESC) AS index FROM funnelweb WHERE closing_date = '{current_date}' AND fund_code IN ('{fund_codes_string}') AND final_rating = 'NR' AND bbg_asset_type <> 'Bond Option' GROUP BY security_name ORDER BY sum_net_mv DESC),
        fund_mvs AS (SELECT security_name, fund_code, net_mv, ROW_NUMBER() OVER (ORDER BY net_mv DESC) AS index FROM funnelweb WHERE closing_date = '{current_date}' AND fund_code IN ('{fund_codes_string}') AND final_rating = 'NR' AND bbg_asset_type <> 'Bond Option' ORDER BY net_mv DESC)
        SELECT mvs.security_name, fund_code, net_mv FROM mvs LEFT JOIN fund_mvs ON mvs.security_name = fund_mvs.security_name ORDER BY mvs.index, fund_mvs.index;"""
        
    df = ss.snowflake.query(sql)
    
    st.write("NR Securities by Allocation")

    selection = st.segmented_control(
        options=['Expanded', 'Collapsed'],
        key='selected_nr_mode',
        label='Funds',
        selection_mode='single',
        default='Expanded'
    )
    
    expanded = -1 if selection == 'Expanded' else 0
    
    build_grid_nr(df, expanded)

TABS_MAPPING = {'MV (BBG)': get_bbg_asset_type_allocation, 'MV': build_sum_by_fwd_asset_type, 'DV01': build_sum_by_fwd_asset_type, 'CS01': build_sum_by_fwd_asset_type, 'Spread': build_wa_by_fwd_asset_type, 'Duration': build_wa_by_fwd_asset_type, 'YTM': build_wa_by_fwd_asset_type, 'WARF': build_wa_by_fwd_asset_type, 'Ratings': build_ratings_profile, 'NR Securities': build_nr_table}
TABS_KWARGS = {
    'MV': {'modes': 'Net MV'},
    'DV01': {'modes': 'DV01'},
    'CS01': {'modes': 'CS01'},
    'Spread': {'modes': 'Credit Spread'},
    'Duration': {'modes': 'Duration'},
    'YTM': {'modes': 'YTM'},
    'WARF': {'modes': 'WARF'},
}

def load_data():
    tabs = ss.get('selected_tab', [])

    if not tabs:
        st.warning("No tabs selected. Please select at least one tab.")
        return

    for tab in tabs:
        func = TABS_MAPPING.get(tab)
        kwargs = TABS_KWARGS.get(tab, {})

        if func is None:
            st.warning(f"Tab '{tab}' is not recognized.")
            continue

        # Call the function with the appropriate arguments
        func(**kwargs)