import streamlit as st
from streamlit import session_state as ss
import pandas as pd
import numpy as np
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode

from utils.interface.menu import menu
from utils.filter.filter import build_multi_select_filter
from utils.snowflake.snowflake import query
from utils.interface.grid import AgGridBuilder, format_numbers, conditional_formatting
from utils.filter.tree import build_tree_selectors

menu('pages/collateral.py')

REPORT_FIELDS = ['POSITION_ID', 'FUND_CODE', 'ACCOUNT_CODE', 'SECURITY_NAME', 'BBGID_V2', 'ISIN', 'NET_MV', 'PLEDGE_POS', 'POSITION']
COUNTERPARTIES = {'MS':'Morgan Stanley', 'Mizuho':'Mizuho', 'GS': 'Goldman Sachs'}
#CUSTOM_FIELDS = {'principal_balance_limit': ['']}

RATING_FIELDS = {'SP_RATING': 'S&P', 'MOODYS_RATING': 'Moodys'}
RATING_REMOVE_LETTERS = [' ','*+', '*-']
RATING_NR_LETTERS = ['P', 'WD', 'WR']
TENOR_FIELD = 'TIME_UNTIL_MATURITY'
RESULT_FIELDS = {'HK_CODE': 'Fund Code', 'FUND_CODE': 'Fund Short Name', 'ACCOUNT_CODE': 'Account', 'SECURITY_NAME': 'Security Name', 'BBGID_V2': 'BBGID_V2', 'ISIN': 'ISIN', 'ASSET_TYPE': 'Asset Type', 'NET_MV': 'Net MV', 'VALUATION_PERCENTAGE': 'Valuation Percentage', 'COLLATERAL_MV': 'Eligible Collateral MV', 'POSITION': 'Total Positions', 'PLEDGE_POS': 'Pledged Positions', 'RATING': 'Final Rating', TENOR_FIELD: 'Tenor' }

#region Get Data

def get_data():
    '''
    Gets collateral logic and funnelweb data for the given date.
    '''
    date = ss.max_date = _get_max_date()
    logic_df = ss.logic_df = _get_collateral_logic(ss.max_date)
    df = ss.funnelweb_collateral_df = _get_funnelweb_data(date, logic_df)
    csa_funds_df, fund_mapping_df = _get_collateral_funds(ss.max_date, df)
    valuation_df = _get_valuation_percentage(ss.max_date)
    rating_ladder, rating_mapping_df = _get_rating_mapping()
    
    return df, logic_df, csa_funds_df, fund_mapping_df, valuation_df, rating_ladder, rating_mapping_df

def _get_max_date():
    '''
    Fetches the maximum closing_date in Funnelweb
    '''
    
    if 'max_date' in ss:
        return ss.max_date
    
    max_date = query('SELECT max(closing_date) AS max_date FROM funnelweb;')['MAX_DATE'][0]
    
    return max_date

def _get_collateral_logic(date):
    '''
    Fetches the collateral logic for a given date from the database.
    '''

    if 'logic_df' in ss:
        return ss.logic_df
    
    logic_df = query(f"WITH max_dates AS (SELECT counterparty, max(effective_date) AS max_date FROM supp.collateral_logic GROUP BY counterparty) SELECT effective_date, l.counterparty, asset_type, field, datatype, logic, value FROM supp.collateral_logic l, max_dates d WHERE l.counterparty = d.counterparty AND l.effective_date = d.max_date AND l.effective_date <= '{date.strftime('%Y-%m-%d')}';")
    
    return logic_df

def _get_funnelweb_data(date, logic_df):
    '''
    Fetches the funnelweb data based on the fields specified by the collateral logic
    '''
    
    if 'funnelweb_collateral_df' in ss:
        return ss.funnelweb_collateral_df
    
    unique_fields = list(logic_df[logic_df['DATATYPE'] != 'Custom']['FIELD'].unique())
    df = query(f"SELECT {' ,'.join(REPORT_FIELDS)}, {','.join(unique_fields)} FROM funnelweb WHERE closing_date = '{date.strftime('%Y-%m-%d')}' AND lbu_group = 'HK';")
    
    return df

def _get_collateral_funds(date, df):
    if 'csa_funds_df' in ss and 'fund_mapping_df' in ss:
       return ss.csa_funds_df, ss.fund_mapping_df
    
    csa_funds_df = ss.csa_funds_df = query(f"WITH max_dates AS (SELECT counterparty, max(effective_date) AS max_date FROM supp.collateral_fund GROUP BY counterparty) SELECT effective_date, f.counterparty, fund, minimum_transfer, rounding FROM supp.collateral_fund f, max_dates d WHERE f.counterparty = d.counterparty AND f.effective_date = d.max_date AND f.effective_date <= '{date.strftime('%Y-%m-%d')}';")
    fund_mapping_df = query(f"SELECT short_name, hk_code, csa_name, sub_lbu FROM supp.fund f, supp.lbu l WHERE f.lbu = l.name AND bloomberg_name = 'HK';")
    
    funds = list(df['FUND_CODE'].unique())
    fund_mapping_df = ss.fund_mapping_df = fund_mapping_df[fund_mapping_df['SHORT_NAME'].isin(funds)]
    
    return csa_funds_df, fund_mapping_df

def _get_valuation_percentage(date):
    if 'valuation_df' in ss:
        return ss.valuation_df
    
    valuation_df = ss.valuation_df = query(f"WITH max_dates AS (SELECT counterparty, max(effective_date) AS max_date FROM supp.collateral_fund GROUP BY counterparty) SELECT effective_date, v.counterparty, asset_type, rating_lower, rating_upper, tenor_lower, tenor_upper, percentage FROM supp.collateral_valuation v, max_dates d WHERE v.counterparty = d.counterparty AND v.effective_date = d.max_date AND v.effective_date <= '{date.strftime('%Y-%m-%d')}';")
    
    return valuation_df

def _get_rating_mapping():
    if 'rating_ladder' in ss and 'rating_mapping_df' in ss:
        return ss.rating_ladder, ss.rating_mapping_df
    
    rating_mapping_df = ss.rating_mapping_df = query("SELECT agency, rating, equivalent_rating FROM supp.ratings_mapping;")
    rating_ladder_df = query("SELECT rating, index FROM supp.ratings_ladder;")
    
    rating_ladder = ss.rating_ladder = dict(zip(rating_ladder_df['RATING'], rating_ladder_df['INDEX']))
    
    return rating_ladder, rating_mapping_df

#endregion

#region Get Counterparty Data

def get_selection(logic_df, csa_funds_df, fund_mapping_df):
    selected_cp = _get_counterparty()
    cp_logic_df = _get_counterparty_logic(logic_df, selected_cp)
    selected_asset_type = _get_asset_type(cp_logic_df)
    cp_funds_df, funds_df = _get_funds(csa_funds_df, fund_mapping_df, selected_cp)
    
    return cp_logic_df, selected_asset_type, cp_funds_df, funds_df

def _get_counterparty():
    build_multi_select_filter('Counterparty', COUNTERPARTIES, 'selected_cp', [], max_selections=1)

    selected_cp = ss.selected_cp

    if selected_cp == []:
        st.warning("Please select a counterparty to filter the data.")
        st.stop()
        
    return selected_cp

def _get_counterparty_logic(logic_df, selected_cp):
    df = logic_df[logic_df['COUNTERPARTY'] == COUNTERPARTIES[selected_cp[0]]]

    return df

def _get_asset_type(df):
    asset_types = df['ASSET_TYPE'].unique()
    asset_type_dict = {at: at for at in asset_types}
    build_multi_select_filter('Asset Type', asset_type_dict, 'selected_asset_type', ['Corporate Bonds'])

    selected_asset_type = ss.selected_asset_type

    if selected_asset_type == []:
        st.warning("Please select an asset type to filter the data.")
        st.stop()
        
    return selected_asset_type

def _get_funds(csa_funds_df, fund_mapping_df, selected_cp):
    cp_funds_df = csa_funds_df[csa_funds_df['COUNTERPARTY'] == COUNTERPARTIES[selected_cp[0]]]
    funds_df = fund_mapping_df[(fund_mapping_df['SUB_LBU'] == 'Bermuda') & (fund_mapping_df['CSA_NAME'] != 'N/A') & (fund_mapping_df['CSA_NAME'].isin(list(cp_funds_df['FUND'])))]
        
    csa_funds = list(cp_funds_df['FUND'].unique())
    
    data = [{'label': 'Select All', 'value': 'all'}]
    
    children = []
    checked = ['all']
    expanded = ['all']
    height = 300
    fund_codes = []
    
    for csa_fund in csa_funds:
        sub_children = []        
        
        funds = funds_df[funds_df['CSA_NAME'] == csa_fund].sort_values(by='HK_CODE')
        funds = dict(zip(funds['HK_CODE'], funds['SHORT_NAME']))

        for hk_code, fund_code in funds.items():
            sub_children.append({'label': hk_code, 'value': fund_code})
            checked.append(fund_code)
            fund_codes.append(fund_code)
        
        if len(sub_children) == 0:
            children.append({'label': f'{csa_fund} (No Assets)', 'value': csa_fund})
        else:    
            children.append({'label': csa_fund, 'value': csa_fund, 'children': sub_children})
            
        checked.append(csa_fund)
        
    data[0]['children'] = children
    
    build_tree_selectors('Funds', data, 'selected_csa_funds', checked, expanded, height=height)
    
    if ss.selected_csa_funds == None:
        ss.selected_funds = fund_codes
    else:
        ss.selected_funds = [fund for fund in ss.selected_csa_funds['checked'] if fund in fund_codes]
        
    if len(ss.selected_funds) == 0:
        st.warning("Please select a fund to filter the data.")
        st.stop()
    
    return cp_funds_df, funds_df

#endregion

#region Filter Eligible Corporate Bonds

def show_data(df, fund_mapping_df, cp_logic_df, selected_asset_type, valuation_df, rating_ladder, rating_mapping_df):
    previous_data_exists = 'previous_cp_logic' in ss and 'previous_valuation_df' in ss and 'previous_eligible_collateral_df' in ss
        
    if previous_data_exists and ss.previous_counterparty == ss.selected_cp and ss.previous_asset_type == ss.selected_asset_type and ss.previous_funds == ss.selected_funds:
        result_df = ss.previous_eligible_collateral_df
        cp_logic_df = ss.previous_cp_logic
        filtered_valuation_df = ss.previous_valuation_df
    else:
        df = map_hk_code(df, fund_mapping_df)
        result_df = filter_eligible_bonds(df, cp_logic_df, selected_asset_type)
        result_df, filtered_valuation_df = assign_valuation_percentage(result_df, valuation_df, cp_logic_df, rating_ladder, rating_mapping_df)
    
    build_grid(result_df, cp_logic_df, filtered_valuation_df)
    
    ss.previous_counterparty = ss.selected_cp
    ss.previous_asset_type = ss.selected_asset_type
    ss.previous_funds = ss.selected_funds
    ss.previous_cp_logic = cp_logic_df
    ss.previous_valuation_df = filtered_valuation_df
    ss.previous_eligible_collateral_df = result_df
    

def map_hk_code(df, fund_mapping_df):
    selected_funds = ss.selected_funds
    filtered_fund_mapping_df = fund_mapping_df[fund_mapping_df['SHORT_NAME'].isin(selected_funds)]
    fund_mapping = dict(zip(filtered_fund_mapping_df['SHORT_NAME'], filtered_fund_mapping_df['HK_CODE']))
    df['HK_CODE'] = df['FUND_CODE'].map(fund_mapping)
        
    return df

def assign_valuation_percentage(df, valuation_df, cp_logic_df, rating_ladder, rating_mapping_df):
    #region Prepare ratings
    
    filtered_valuation_df = valuation_df[(valuation_df['COUNTERPARTY'] == COUNTERPARTIES[ss.selected_cp[0]]) & valuation_df['ASSET_TYPE'].isin(ss.selected_asset_type)].copy()
    filtered_valuation_df['RATING_LOWER_INDEX'] = filtered_valuation_df['RATING_LOWER'].map(rating_ladder)
    filtered_valuation_df['RATING_UPPER_INDEX'] = filtered_valuation_df['RATING_UPPER'].map(rating_ladder)
    
    rating_fields = _build_agency_rating_mapping(cp_logic_df, rating_mapping_df)
    
    #endregion
            
    df['VALUATION_PERCENTAGE'] = None
    df['RATING'] = None
    
    rating_ladder_index = {value: key for key, value in rating_ladder.items()}
    
    for index, row in df.iterrows():
        #region Sort Ratings
        
        ratings_index = []
        
        for rating_field, rating_mapping in rating_fields.items():
            rating = _clean_rating(row[rating_field])
            
            if rating == 'None':
                continue
            equivalent_rating = rating_mapping[rating]
            rating_index = rating_ladder[equivalent_rating]
            ratings_index.append(rating_index)
            
        ratings_index.sort()
        
        if len(ratings_index) == 0:
            continue
        
        #endregion
        
        #region Look for match
        
        rating_index = ratings_index[-1]
        tenor = row[TENOR_FIELD]
            
        rating_match = (filtered_valuation_df['RATING_UPPER_INDEX'] <= rating_index) & (filtered_valuation_df['RATING_LOWER_INDEX'] >= rating_index)
        tenor_match = (filtered_valuation_df['TENOR_UPPER'] <= tenor) & (filtered_valuation_df['TENOR_LOWER'] < tenor)
        asset_type_match = filtered_valuation_df['ASSET_TYPE'] == row['ASSET_TYPE']
        
        valuation_match_df = filtered_valuation_df[rating_match & tenor_match & asset_type_match].reset_index(drop=True)
        
        if len(valuation_match_df) == 0:
            continue
        
        #endregion
        
        #region Assign Valuation Percentage
        
        percentage = valuation_match_df.loc[0, 'PERCENTAGE']
        
        df.loc[index, 'VALUATION_PERCENTAGE'] = percentage
        
        position = row['POSITION']
        pledge_pos = row['PLEDGE_POS']
        mv = row['NET_MV']
        
        if abs(pledge_pos) > position:
            st.toast(f"Pledged position is higher than actual position for security '{row['SECURITY_NAME']}' in account '{row['ACCOUNT_CODE']}'")
        
        df.loc[index, 'COLLATERAL_MV'] = mv * (position + pledge_pos) / position * percentage
        df.loc[index, 'RATING'] = rating_ladder_index[rating_index]
        
        #endregion
    
    # Filter out non eligible bonds
    df = df[~df['VALUATION_PERCENTAGE'].isna()]
    
    return df, filtered_valuation_df

def _build_agency_rating_mapping(cp_logic_df, rating_mapping_df):
    logic_fields = list(cp_logic_df['FIELD'])
    rating_fields = {}
    for key, value in RATING_FIELDS.items():
        if key.lower() not in logic_fields:
            continue
        
        agency_mapping_df = rating_mapping_df[rating_mapping_df['AGENCY'] == value]
        agency_mapping = dict(zip(agency_mapping_df['RATING'], agency_mapping_df['EQUIVALENT_RATING']))
        rating_fields[key] = agency_mapping
        
    return rating_fields

def _clean_rating(rating):
    for letter in RATING_REMOVE_LETTERS:
        rating = rating.replace(letter, '')
    
    for letter in RATING_NR_LETTERS:
        if letter in rating:
            rating = 'NR'
    
    return rating

def filter_eligible_bonds(df, cp_logic_df, selected_asset_type):
    df['ASSET_TYPE'] = None
    
    result_df = pd.DataFrame()
    
    for asset_type in selected_asset_type:
        at_logic_df = cp_logic_df[cp_logic_df['ASSET_TYPE'] == asset_type]
        filter_df = df[df['FUND_CODE'].isin(ss.selected_funds)].copy()
        
        for index, row in at_logic_df.iterrows():
            filter_df = _filter_dataframe(row, filter_df)
        
        if len(result_df) == 0:
            result_df = filter_df
        else:
            result_df = pd.concat([result_df, filter_df], ignore_index=True)
    
    if len(result_df) == 0:
        st.warning('No eligible collateral for this selection!')
        st.stop()
    
    return result_df.reset_index(drop=True)

    #st.write(f'Pledged positions summary')
    #st.write(result_df[result_df['PLEDGE_POS'] != 0])

def _filter_dataframe(row, filter_df):
    field = row['FIELD']
    logic = row['LOGIC']
    datatype = row['DATATYPE']
    value = row['VALUE'].replace('//', '/')
    asset_type = row['ASSET_TYPE']
    
    if datatype == 'Double':
        value = float(value)
    
    if datatype == 'Custom':
        if field == 'principal_balance_limit':
            value = value
        elif field == 'or_rating':
            filter_df = filter_df[(filter_df['SP_RATING'] != None) | (filter_df['MOODYS_RATING'] != None)]
        else:
            st.toast(f"Custom logic for field '{field}' is not coded!", icon='⚠️')
    elif value == 'None':
        if logic == 'NOT EQUAL':
            filter_df = filter_df[filter_df[field.upper()] != '']
            filter_df = filter_df[filter_df[field.upper()] != 'None']
            filter_df = filter_df[filter_df[field.upper()] != 'NR']
            filter_df = filter_df[filter_df[field.upper()] != 'WD']
            filter_df = filter_df[filter_df[field.upper()] != 'WR']
    elif logic == 'EQUAL':
        filter_df = filter_df[filter_df[field.upper()] == value]
    elif logic == 'IN':
        value_list = value.split(';')
        filter_df = filter_df[filter_df[field.upper()].isin(value_list)]
    elif logic == 'IN CONTAINS':
        value_list = value.replace(';', '|')
        filter_df = filter_df[filter_df[field.upper()].str.contains(value_list)]
    elif logic == 'LESS THAN':
        filter_df = filter_df[filter_df[field.upper()] < value]
    elif logic == 'NOT EQUAL':
        filter_df = filter_df[filter_df[field.upper()] != value]
    elif logic == 'GREATER THAN':
        filter_df = filter_df[filter_df[field.upper()] > value]
    else:
        st.toast(f"Logic '{logic}' is not coded!", icon='⚠️')
        
    filter_df['ASSET_TYPE'] = asset_type
        
    return filter_df

def build_grid(df, cp_logic_df, filtered_valuation_df):
    logic_height = 300
    result_height = 600
    
    #region Display Logic
    
    with st.expander('Counterparty Logic'):
        grid = AgGridBuilder(cp_logic_df, min_width=200)
        grid.show_grid(height=logic_height, autofit=False)
    
    with st.expander("Counterparty Valuation Percentage"):
        grid = AgGridBuilder(filtered_valuation_df, min_width=200)
        grid.add_column('PERCENTAGE', value_formatter=format_numbers(1, percentage=True), cell_style=None)
        grid.show_grid(height=logic_height, autofit=False)
        
    #endregion
    
    st.write(f'Total positions: {len(df)}')
    st.write(f"Total eligible collateral MV: ${df['COLLATERAL_MV'].sum() / 1000000:,.2f}mn")
    
    grid_df = df[RESULT_FIELDS.keys()].rename(columns=RESULT_FIELDS).reset_index(drop=True)
    grid = AgGridBuilder(grid_df)
        
    grid.add_column(RESULT_FIELDS['NET_MV'], value_formatter=format_numbers(0), cell_style=None)
    grid.add_column(RESULT_FIELDS['VALUATION_PERCENTAGE'], value_formatter=format_numbers(1, percentage=True), cell_style=None)
    grid.add_column(RESULT_FIELDS['COLLATERAL_MV'], value_formatter=format_numbers(0), cell_style=None)
    grid.add_column(RESULT_FIELDS['POSITION'], value_formatter=format_numbers(0), cell_style=None)
    grid.add_column(RESULT_FIELDS['PLEDGE_POS'], value_formatter=format_numbers(0), cell_style=None)
    grid.add_column(RESULT_FIELDS[TENOR_FIELD], value_formatter=format_numbers(1), cell_style=None)
    
    grid.show_grid(height=result_height)

#endregion

st.write('Currently only supporting corporate bond CSAs in Bermuda')
df, logic_df, csa_funds_df, fund_mapping_df, valuation_df, rating_ladder, rating_mapping_df = get_data()
cp_logic_df, selected_asset_type, cp_funds_df, funds_df = get_selection(logic_df, csa_funds_df, fund_mapping_df)

show_data(df, fund_mapping_df, cp_logic_df, selected_asset_type, valuation_df, rating_ladder, rating_mapping_df)