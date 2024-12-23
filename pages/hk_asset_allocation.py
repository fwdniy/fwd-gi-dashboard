from utils.interface.menu import menu
from utils.snowflake.funnelweb import get_funnelweb_dates
import streamlit as st
from utils.filter.filter import build_lbu_filter, build_date_filter_buttons
from streamlit import session_state as ss
from utils.snowflake.snowflake import query
import pandas as pd
from utils.interface.grid import AgGridBuilder

menu('pages/hk_asset_allocation.py')

with st.expander('Filters', True):
    dates = get_funnelweb_dates()

    build_date_filter_buttons('Valuation Date', dates, key='selected_date')
    build_date_filter_buttons('Comparison Date', dates, key='selected_comparison_date', date=ss['selected_date'])
    build_lbu_filter(True)

fund_codes = str(ss['selected_funds']).replace('[', '').replace(']', '')
entity_mapping = ss['entity_mapping']
current_date = ss['selected_date']
comparison_date = ss['selected_comparison_date']

def build_query(columns, values, add_comparison_date=False):
    dates = f'\'{current_date}\''

    if add_comparison_date:
        dates = f'\'{current_date}\', \'{comparison_date}\''

    query_string = f"SELECT closing_date, {columns}, {values} FROM funnelweb WHERE closing_date IN ({dates}) AND fund_code IN ({fund_codes}) GROUP BY closing_date, {columns} ORDER BY closing_date, {columns};"
    
    return query_string

def build_query_wa(columns, field, weight_field, additional_filter):

    query_string = f"""WITH mvs AS (SELECT {columns}, sum(net_mv) AS sum_net_mv FROM funnelweb WHERE closing_date = '{current_date}' AND fund_code IN ({fund_codes}) AND {field} <> 0{additional_filter} GROUP BY {columns} ORDER BY {columns}), 
    weight AS (SELECT {columns}, sum({field} * net_mv) AS {weight_field} FROM funnelweb WHERE closing_date = '{current_date}' AND fund_code IN ({fund_codes}){additional_filter} GROUP BY {columns} ORDER BY {columns})
    SELECT weight.fund_code, weight.fwd_asset_type, COALESCE(sum_net_mv, 0) AS sum_net_mv, COALESCE({weight_field}, 0) AS {weight_field} FROM weight LEFT JOIN mvs ON mvs.fund_code = weight.fund_code AND mvs.fwd_asset_type = weight.fwd_asset_type;"""

    return query_string

def build_aa_by_bbg_asset_type():
    st.write('Actual Allocation By Bloomberg Asset Type')
    columns = ['BBG_ASSET_TYPE']
    values = {'SUM_NET_MV': 'SUM(NET_MV) / 1000000 AS SUM_NET_MV'}

    query_string = build_query(', '.join(columns), ', '.join(values.values()), True)
    df = query(query_string)
    
    df['CLOSING_DATE'] = df['CLOSING_DATE'].dt.date.replace({current_date: 'Current Date', comparison_date: 'Comparison Date'})
    df = df.pivot(index='BBG_ASSET_TYPE', columns='CLOSING_DATE', values='SUM_NET_MV')
    df = df[['Current Date', 'Comparison Date']]
    df.reset_index(inplace=True)
    df.rename(columns={'BBG_ASSET_TYPE': 'Bloomberg Asset Type'}, inplace=True)
    df.fillna(0, inplace=True)

    df['Delta Δ'] = df['Current Date'] - df['Comparison Date']
    df['Current %'] = (df['Current Date'] / df['Current Date'].sum()) * 100
    df['Comparison %'] = (df['Comparison Date'] / df['Comparison Date'].sum()) * 100
    df['Delta Δ %'] = df['Current %'] - df['Comparison %']
    total_row = pd.DataFrame(df.sum(numeric_only=True)).T
    df = pd.concat([df, total_row], ignore_index=True)
    df.iloc[-1, df.columns.get_loc('Bloomberg Asset Type')] = 'Total'

    grid = AgGridBuilder(df)

    grid.add_columns([column for column in df.columns if 'Bloomberg' not in column and "Δ" not in column], False)
    grid.add_column('Delta Δ', cell_style_ranges=[sum(df['Current Date']) * -0.05 / 2, 0, sum(df['Current Date']) * 0.05 / 2])
    grid.add_column('Delta Δ %')
    grid.show_grid((len(df) + 1) * 30)

def build_sum_by_fwd_asset_type():
    columns = ['FUND_CODE', 'FWD_ASSET_TYPE']
    value_headers = {'Actual Allocation': 'SUM_NET_MV', 'DV01': 'SUM_DV01', 'CS01': 'SUM_CS01'}
    values = {'SUM_NET_MV': 'SUM(NET_MV) / 1000000 AS SUM_NET_MV', 'SUM_DV01': 'SUM(DV01_000) / 1000 AS SUM_DV01', 'SUM_CS01': 'SUM(CS01_000) / 100 AS SUM_CS01'}
    query_string = build_query(', '.join(columns), ', '.join(values.values()))
    df = ss['sum_df'] = query(query_string)

    df['ENTITY'] = df['FUND_CODE'].map(entity_mapping)
    column_order = ['ENTITY'] + columns + list(value_headers.values())
    df = df[column_order]

    assetTypeCount = len(df['FWD_ASSET_TYPE'].unique())
    height = 120 + 30 * assetTypeCount

    for header, value_column in value_headers.items():
        st.write(f'{header} by FWD Asset Type')
        grid = AgGridBuilder(df)
        grid.add_options(pivot_total='left', group_total=True, remove_pivot_headers=False)
        grid.add_columns(['FWD_ASSET_TYPE'], value_formatter=None, sort='asc')

        entity_comparator = grid.customOrderComparatorString.replace('value', "', '".join(df.groupby('ENTITY').agg({'SUM_NET_MV': 'sum'}).sort_values(by='SUM_NET_MV', ascending=False).index.tolist()))
        fund_comparator = grid.customOrderComparatorString.replace('value', "', '".join(df.groupby('FUND_CODE').agg({'SUM_NET_MV': 'sum'}).sort_values(by='SUM_NET_MV', ascending=False).index.tolist()))

        grid.set_pivot_column('ENTITY', entity_comparator)
        grid.set_pivot_column('FUND_CODE', fund_comparator)
        grid.add_value(value_column, header)
        grid.show_grid(height)

def build_wa_by_fwd_asset_type():
    columns = ['FUND_CODE', 'FWD_ASSET_TYPE']
    value_headers = {'Credit Spread': 'CREDIT_SPREAD_BP', 'Duration': 'DURATION', 'YTM': 'YTM', 'WARF': 'WARF'}
    additional_filters = {'WARF': ' AND bbg_asset_type NOT IN (\'Bond Option\', \'Repo Liability\')'}
    sum_df = ss['sum_df']

    for header, value_column in value_headers.items():
        st.write(f'{header} by FWD Asset Type')

        additional_filter = ''

        if value_column in additional_filters.keys():
            additional_filter = additional_filters[value_column]
        
        query_string = build_query_wa(', '.join(columns), value_column, 'SUMPRODUCT', additional_filter)
        df = query(query_string)

        df['ENTITY'] = df['FUND_CODE'].map(entity_mapping)
        column_order = ['ENTITY'] + columns + ['SUM_NET_MV', 'SUMPRODUCT']
        df = df[column_order]

        assetTypeCount = len(df['FWD_ASSET_TYPE'].unique())
        height = 120 + 30 * assetTypeCount

        grid = AgGridBuilder(df)
        grid.add_options(pivot_total='left', group_total=True, remove_pivot_headers=False)
        grid.add_columns(['FWD_ASSET_TYPE'], value_formatter=None, sort='asc')

        weight_comparator = grid.weightedAverageFuncString.replace("aggColumn", 'SUMPRODUCT').replace("weightColumn", 'SUM_NET_MV')
        entity_comparator = grid.customOrderComparatorString.replace('value', "', '".join(sum_df.groupby('ENTITY').agg({'SUM_NET_MV': 'sum'}).sort_values(by='SUM_NET_MV', ascending=False).index.tolist()))
        fund_comparator = grid.customOrderComparatorString.replace('value', "', '".join(sum_df.groupby('FUND_CODE').agg({'SUM_NET_MV': 'sum'}).sort_values(by='SUM_NET_MV', ascending=False).index.tolist()))

        grid.set_pivot_column('ENTITY', entity_comparator)
        grid.set_pivot_column('FUND_CODE', fund_comparator)
        grid.add_value('SUMPRODUCT', header, weight_comparator)

        grid.show_grid(height)

def build_ratings_profile():
    query_string = f"SELECT fund_code, index, final_rating, sum(net_mv) / 1000000 AS sum_net_mv FROM funnelweb, supp.ratings_ladder WHERE closing_date = '{current_date}' AND fund_code IN ({fund_codes}) AND funnelweb.warf <> 0 AND final_rating = rating GROUP BY fund_code, index, final_rating ORDER BY index;"
    df = query(query_string)
    df['ENTITY'] = df['FUND_CODE'].map(entity_mapping)
    df = df[['ENTITY', 'FUND_CODE', 'FINAL_RATING', 'SUM_NET_MV']]

    assetTypeCount = len(df['FINAL_RATING'].unique())
    height = 120 + 30 * assetTypeCount

    st.write("Actual Allocation by Final Rating")
    grid = AgGridBuilder(df)
    grid.add_options(pivot_total='left', group_total=True, remove_pivot_headers=False)
    grid.add_columns(['FINAL_RATING'], value_formatter=None, sort='')

    entity_comparator = grid.customOrderComparatorString.replace('value', "', '".join(df.groupby('ENTITY').agg({'SUM_NET_MV': 'sum'}).sort_values(by='SUM_NET_MV', ascending=False).index.tolist()))
    fund_comparator = grid.customOrderComparatorString.replace('value', "', '".join(df.groupby('FUND_CODE').agg({'SUM_NET_MV': 'sum'}).sort_values(by='SUM_NET_MV', ascending=False).index.tolist()))

    grid.set_pivot_column('ENTITY', entity_comparator)
    grid.set_pivot_column('FUND_CODE', fund_comparator)
    grid.add_value('SUM_NET_MV', 'MV')
    grid.show_grid(height)

def build_nr_securities_table():
    query_string = f"""WITH mvs AS (SELECT security_name, sum(net_mv) AS sum_net_mv, ROW_NUMBER() OVER (ORDER BY sum_net_mv DESC) AS index FROM funnelweb WHERE closing_date = '{current_date}' AND fund_code IN ({fund_codes}) AND final_rating = 'NR' AND bbg_asset_type <> 'Bond Option' GROUP BY security_name ORDER BY sum_net_mv DESC),
        fund_mvs AS (SELECT security_name, fund_code, net_mv, ROW_NUMBER() OVER (ORDER BY net_mv DESC) AS index FROM funnelweb WHERE closing_date = '{current_date}' AND fund_code IN ({fund_codes}) AND final_rating = 'NR' AND bbg_asset_type <> 'Bond Option' ORDER BY net_mv DESC)
        SELECT mvs.security_name, fund_code, net_mv FROM mvs LEFT JOIN fund_mvs ON mvs.security_name = fund_mvs.security_name ORDER BY mvs.index, fund_mvs.index;"""
    df = query(query_string)

    st.write("NR Securities by Allocation")

    if "nrSecuritiesExpanded" not in st.session_state:
        st.session_state["nrSecuritiesExpanded"] = -1

    col1, col2, col3 = st.columns([1, 1, 8])
    with col1:
        if st.button("Expand all", use_container_width=True):
            ss["nrSecuritiesExpanded"] = -1
    with col2:
        if st.button("Collapse all", use_container_width=True):
            ss["nrSecuritiesExpanded"] = 0
    
    grid = AgGridBuilder(df)
    grid.add_options(pivot_total='left', group_total=True, remove_pivot_headers=False, pivot_mode=False,group_expanded=ss["nrSecuritiesExpanded"])
    grid.add_columns(['SECURITY_NAME'], value_formatter=None, hide=True)
    grid.add_columns(['FUND_CODE'], row_group=False, value_formatter=None)
    grid.add_value('NET_MV', 'Net MV')

    grid.show_grid()

build_aa_by_bbg_asset_type()

build_sum_by_fwd_asset_type()

build_wa_by_fwd_asset_type()

build_ratings_profile()

build_nr_securities_table()