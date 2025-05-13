from classes.bond import Bond
from utils.snowflake.snowflake import query
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
from utils.snowflake.funnelweb import get_funnelweb_dates
from utils.filter.filter import build_lbu_filter, build_date_filter_buttons, build_multi_select_filter, build_fund_filter
import streamlit as st
from streamlit import session_state as ss
from utils.interface.menu import menu
import plotly.express as px
import plotly.graph_objects as go
from utils.interface.download import create_download_button

menu('pages/almatcher.py')
        
def load_data(bar):        
    (cf_df, pos_df) = _get_data(ss.selected_date)
    bar.progress(5, "Filtering securities...")
    
    (pos_df_filtered, remove_securities) = _clean_pos(pos_df)
        
    bar.progress(10, "Building cashflows...")
    bonds = _build_bonds(bar, pos_df_filtered, cf_df, remove_securities)
    
    bar.progress(80, "Aggregating cashflows...")
    cashflow_df = _build_cashflow_df(bonds)    
    
    return (bonds, cashflow_df)

def _get_data(date):
    """
    Gets cashflow dates and positional data from snowflake
    """

    if 'previous_selected_date' in ss and ss.selected_date == ss.previous_selected_date and 'cashflow_df' in ss:
        return (ss.cashflow_df, ss.pos_df)
    
    cf_df = ss['cashflow_df'] = query(f"SELECT bbgid, category, value FROM supp.cashflow_dates WHERE valuation_date = '{date}';")
    pos_df = ss['pos_df'] = query(f"SELECT closing_date, position_id, lbu_code, fund_code, fwd_asset_type, account_code, bbg_asset_type, security_name, bbgid_v2, isin, effective_maturity, maturity, next_call_date, coupon_rate, coupnfreq, position, unit, mtge_factor, principal_factor, redemption_value, next_call_price, currency, fx_rate FROM funnel.funnelweb WHERE closing_date = '{date}' AND lbu_group = 'HK' AND is_bbg_fi = TRUE;")
    
    ss.previous_selected_date = ss.selected_date

    return (cf_df, pos_df)

def _clean_pos(pos_df):
    default_skip_securities = ['.APPIS 0 01/30/2125 8999']
    default_remove_bbg_asset_types = ['Repo Liability', 'Bond Option']
    default_remove_fwd_asset_types = ['Listed Equity - Local', 'Listed Equity - International', 'Liability hedging assets']
    
    fund_code = ss.selected_funds
    pos_df_filtered = pos_df[pos_df['FUND_CODE'].isin(fund_code)]
    
    if len(pos_df_filtered) == 0:
        st.error('No data available for the selected fund.')
        st.stop()
    
    with st.expander('Field Filters', True):
        remove_securities = _build_column_filter('Securities', pos_df_filtered['SECURITY_NAME'].unique(), 'selected_securities', default_skip_securities)
        remove_bbg_asset_types = _build_column_filter('BBG Asset Type', pos_df_filtered['BBG_ASSET_TYPE'].unique(), 'selected_bbg_asset_types', default_remove_bbg_asset_types)
        remove_fwd_asset_types = _build_column_filter('FWD Asset Type', pos_df_filtered['FWD_ASSET_TYPE'].unique(), 'selected_fwd_asset_types', default_remove_fwd_asset_types)
    
    pos_df_filtered = pos_df_filtered[~pos_df_filtered['BBG_ASSET_TYPE'].isin(remove_bbg_asset_types)]
    pos_df_filtered = pos_df_filtered[~pos_df_filtered['FWD_ASSET_TYPE'].isin(remove_fwd_asset_types)]
    pos_df_filtered['COUPON_RATE'] = pos_df_filtered.apply(lambda row: 6.0 if row['COUPON_RATE'] == 0.0 and row['BBG_ASSET_TYPE'] == 'Mortgage Backed Security' else row['COUPON_RATE'], axis=1)
    pos_df_filtered = pos_df_filtered.reset_index(drop=True)
        
    return (pos_df_filtered, remove_securities)

def _build_cashflow_df(bonds):
    group_columns = ['FUND_CODE', 'FWD_ASSET_TYPE', 'YEAR']
    value_columns = ['VALUE']
    columns = group_columns + value_columns    
    
    rows = []          
    
    for i, bond in enumerate(bonds):
        for cashflow in bond.cashflow:
            rows.append({
                'FUND_CODE': bond.fund_code,
                'FWD_ASSET_TYPE': bond.fwd_asset_type,
                'YEAR': cashflow.year,
                'VALUE': cashflow.payment
            })
        
    df = pd.DataFrame(rows, columns=columns)
    df = df.sort_values(by='YEAR')
    group_df = df.groupby(group_columns).sum().reset_index()
    
    return group_df

def _build_column_filter(label, data, key, default):
    default_values = [value for value in data if value in default]
    
    remove_values = build_multi_select_filter(f'{label} Filter', {value: value for value in data}, key, default_values)
    
    return remove_values

def _build_bonds(bar, pos_df, cf_df, remove_securities):
    """
    Build a list of Bond objects with the cashflow data
    """
    bonds = []
    cf_bbgids = cf_df['BBGID'].unique()
    cf_dict = {bbgid: cf_df[cf_df['BBGID'] == bbgid] for bbgid in cf_bbgids}

    for index, row in pos_df.iterrows():
        if row['SECURITY_NAME'] in remove_securities:
            continue
        
        bbgid = row['BBGID_V2']
            
        bond_cf_df = cf_dict.get(bbgid, pd.DataFrame())
        
        bond = Bond(row, bond_cf_df)
        bonds.append(bond)
        
        if index % 100 == 0 or index == len(pos_df) - 1:
            bar.progress(int(10 + (index / len(pos_df) * 70)), "Building cashflows...")
    
    return bonds

def output_cashflows(bonds):
    max_date = datetime.min
    
    for bond in bonds:
        if bond.max_date > max_date:
            max_date = bond.max_date
            
    date_columns = []
    
    date = bonds[0].closing_date
    
    while max_date >= date:
        date_columns.append(max_date.strftime('%Y-%m'))
        max_date += relativedelta(months=-1)
        
    date_columns.append(max_date.strftime('%Y-%m'))
        
    date_columns.reverse()
    
    security_characteristics = ['POSITION_ID', 'LBU_CODE', 'FUND_CODE', 'FWD_ASSET_TYPE', 'ACCOUNT_CODE', 'SECURITY_NAME', 'ISIN', 'BBGID_V2', 'CURRENCY', 'FX_RATE', 'COUPON_RATE', 'COUPON_FREQ', 'NOTIONAL']
    
    columns = security_characteristics + date_columns
    
    df = pd.DataFrame(None, index=range(len(bonds)), columns=columns)
    
    index = 0
    for bond in bonds:
        df.loc[index, 'POSITION_ID'] = bond.position_id
        df.loc[index, 'LBU_CODE'] = bond.lbu_code
        df.loc[index, 'FUND_CODE'] = bond.fund_code
        df.loc[index, 'FWD_ASSET_TYPE'] = bond.fwd_asset_type
        df.loc[index, 'ACCOUNT_CODE'] = bond.account_code
        df.loc[index, 'SECURITY_NAME'] = bond.security_name
        df.loc[index, 'ISIN'] = bond.isin
        df.loc[index, 'BBGID_V2'] = bond.bbgid
        df.loc[index, 'CURRENCY'] = bond.currency
        df.loc[index, 'FX_RATE'] = bond.fx_rate
        df.loc[index, 'COUPON_RATE'] = bond.rate
        df.loc[index, 'COUPON_FREQ'] = bond.freq
        df.loc[index, 'NOTIONAL'] = bond.notional
        
        cashflow_dict = {cashflow.date.strftime('%Y-%m'): cashflow.payment for cashflow in bond.cashflow}
        df.loc[index, cashflow_dict.keys()] = pd.Series(cashflow_dict)
        
        if (index + 1) % 1000 == 0 or index == len(bonds) - 1:
            print(f"Added to dataframe for {index + 1} of {len(bonds)} bonds")
        
        index += 1
        
    print('Dataframe build!')
    
    df.to_excel('results.xlsx')
    
    print('Excel outputted!')
    
    return df

def _build_liability_groups_filter():
    liab_df =_get_liabilities()
    
    groups = list(liab_df['GROUP_NAME'].unique())
    
    group = st.pills('Liability Groups', groups, default=groups[0], key='selected_liability_group')
    
    ss.selected_funds = _get_saa_groups()

def _get_saa_groups():
    funds_df = query(f"SELECT short_name FROM supp.fund WHERE saa_group = '{ss.selected_liability_group}';")
    
    return funds_df['SHORT_NAME'].tolist()

def _get_liabilities():    
    liab_df = ss["liab_df"] = query(f"SELECT group_name, year, value FROM liability_profile.hk_liabilities WHERE as_of_date = (SELECT max(as_of_date) AS max_date FROM liability_profile.hk_liabilities WHERE as_of_date <= '{ss.selected_date}');")
    
    return liab_df

def build_filters():
    """
    Build filters for the activity monitor page. This includes LBU, date, column and value filters.
    """
    
    with st.expander('Filters', True):
        dates = get_funnelweb_dates()
        build_date_filter_buttons('Asset Date', dates, key='selected_date')
        build_date_filter_buttons('Liability Date', dates, 'MTD', key='selected_comparison_date')
        _build_liability_groups_filter()
    
    if ss.selected_funds == []:
        st.error('Please select at least one fund')
        st.stop()

def build_charts(bar, bonds, df):
    bar.progress(90, "Building asset flows chart...")
    _build_asset_flows(df)
    bar.progress(95, "Building maturities chart...")
    _build_maturity_chart(bonds)

def _build_maturity_chart(bonds):
    columns = ['SECURITY_NAME', 'BBGID_V2', 'FWD_ASSET_TYPE', 'FUND_CODE', 'EFFECTIVE_MATURITY', 'NOTIONAL', 'YEAR']
    mat_df = pd.DataFrame(None, index=range(len(bonds)), columns=columns)
    mat_df = mat_df.sort_values(by='FWD_ASSET_TYPE')

    index = 0
    for bond in bonds:
        mat_df.loc[index, 'SECURITY_NAME'] = bond.security_name
        mat_df.loc[index, 'BBGID_V2'] = bond.bbgid
        mat_df.loc[index, 'FWD_ASSET_TYPE'] = bond.fwd_asset_type
        mat_df.loc[index, 'FUND_CODE'] = bond.fund_code
        mat_df.loc[index, 'EFFECTIVE_MATURITY'] = bond.effective_maturity
        mat_df.loc[index, 'NOTIONAL'] = bond.notional
        mat_df.loc[index, 'YEAR'] = bond.cashflow[-1].year
        index += 1

    fig = px.scatter(
        mat_df, 
        x='EFFECTIVE_MATURITY', 
        y='NOTIONAL', 
        color='FWD_ASSET_TYPE', 
        title='Asset Flows by Workout Maturity',
        hover_data=['FUND_CODE', 'SECURITY_NAME', 'BBGID_V2', 'YEAR'],
        category_orders={'FWD_ASSET_TYPE': sorted(mat_df['FWD_ASSET_TYPE'].unique())}
    )
        
    fig.update_layout(        
        xaxis_title='Effective Maturity (Year)',
        yaxis_title='Notional (USD)',
        xaxis=dict(
        range=[ss.selected_comparison_date, mat_df['EFFECTIVE_MATURITY'].max()]
        )
    )

    st.plotly_chart(fig)

def _build_asset_flows(df):
    group_columns = ['FWD_ASSET_TYPE', 'YEAR']
    
    group_df = df.groupby(group_columns)['VALUE'].sum().reset_index()
    
    fig = px.line(
        group_df, 
        x='YEAR', 
        y='VALUE', 
        color='FWD_ASSET_TYPE', 
        title='Asset Flows by Year',
        category_orders={'FWD_ASSET_TYPE': sorted(group_df['FWD_ASSET_TYPE'].unique())},
        markers=True  # Adds markers at each data point
    )

    fig.update_layout(
        xaxis_range=[1, group_df['YEAR'].max()],
        yaxis_title="Cashflow (USD)",
        xaxis_title="Year (from Liability Date)",
        xaxis_dtick=1  # Forces yearly x-axis ticks
    )

    st.plotly_chart(fig)

def build_alm_chart(df):
    liab_df = ss.liab_df
    liab_df = liab_df[liab_df['GROUP_NAME'] == ss.selected_liability_group]
    liab_df = liab_df[['YEAR', 'VALUE']]
    liab_df['MODE'] = 'liab'
    
    asset_df = df.groupby(['YEAR'])['VALUE'].sum().reset_index()
    asset_df['VALUE'] = asset_df['VALUE'] / 1000000
    asset_df['MODE'] = 'asset'
    
    al_df = pd.concat([liab_df, asset_df], ignore_index=True)
    
    color_discrete_map = {'asset': '#F3BB90', 'liab': '#EDEFF0'}

    fig = px.bar(al_df, x='YEAR', y='VALUE', color='MODE', color_discrete_map=color_discrete_map)
    
    net_values = pd.merge(asset_df, liab_df, on='YEAR', how='outer', suffixes=('_asset', '_liab'))
    net_values.fillna(0, inplace=True)
    net_values['NET_VALUE'] = net_values['VALUE_asset'] + net_values['VALUE_liab']

    net_values['CUMULATIVE_NET'] = net_values['NET_VALUE'].cumsum()
    
    fig.add_trace(go.Scatter(
        x=net_values['YEAR'],
        y=net_values['NET_VALUE'],
        mode='markers',
        name='Net Value',
        marker=dict(color='red', size=10, symbol=141)
    ))
    
    fig.add_trace(go.Scatter(
        x=net_values['YEAR'],
        y=net_values['CUMULATIVE_NET'],
        mode='lines',
        name='Cumulative Net Value',
        line=dict(color='red', width=2, dash='dash')
    ))
    
    st.plotly_chart(fig)
    
    return net_values
    

build_filters()

bar = st.progress(0, text="Getting data..")
(bonds, cashflow_df) = load_data(bar)

#build_charts(bar, bonds, cashflow_df)
al_df = build_alm_chart(cashflow_df)

bar.empty()

create_download_button(al_df, 'asset_liability', 'Download Asset Liability Data', True)