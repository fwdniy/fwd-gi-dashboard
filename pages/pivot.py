from utils.interface.menu import menu
from utils.snowflake.funnelweb import get_funnelweb_dates
import streamlit as st
from utils.filter.filter import build_lbu_filter, build_date_filter_buttons
from datetime import datetime
from streamlit import session_state as ss
from utils.snowflake.snowflake import query
import pandas as pd
from utils.interface.grid import AgGridBuilder

menu('Funnelweb Pivot')

columns = {'LBU Group': 'LBU_GROUP', 'LBU Code': 'LBU_CODE', 'Account Code': 'ACCOUNT_CODE', 'Fund Code': 'FUND_CODE', 'Fund Type': 'FUND_TYPE', 'Manager': 'MANAGER', 'FWD Asset Type': 'FWD_ASSET_TYPE', 'BBG Asset Type': 'BBG_ASSET_TYPE', 'L1 Asset Type': 'L1_ASSET_TYPE', 'L2 Asset Type': 'L2_ASSET_TYPE', 'L3 Asset Type': 'L3_ASSET_TYPE', 'L4 Asset Type': 'L4_ASSET_TYPE', 'Currency': 'CURRENCY', 'Final Rating': 'FINAL_RATING', 'Final Rating Letter': 'FINAL_RATING_LETTER', 'Country': 'COUNTRY_REPORT', 'Issuer': 'ISSUER', 'Ultimate Parent': 'ULTIMATE_PARENT_NAME', 'CAST Parent': 'CAST_PARENT_NAME', 'Industry Sector': 'INDUSTRY_SECTOR', 'Industry Group': 'INDUSTRY_GROUP', 'Industry': 'INDUSTRY', 'Ult Parent Industry Group': 'ULT_PARENT_INDUSTRY_GROUP'}
values = {'Net MV': 'NET_MV', 'Clean MV': 'CLEAN_MV_USD', 'Credit Spread': 'CREDIT_SPREAD_BP', 'Duration': 'DURATION', 'YTM': 'YTM', 'DV01 000s': 'DV01_000', 'CS01 000s': 'CS01_000', 'Convexity': 'CONVEXITY', 'WARF': 'WARF'}
values_function = {'Net MV': 'sum', 'Clean MV': 'sum', 'Credit Spread': 'wa', 'Duration': 'wa', 'YTM': 'wa', 'DV01 000s': 'sum', 'CS01 000s': 'sum', 'Convexity': 'wa', 'WARF': 'wa'}

def load_data():
    def check_columns_values():
        selected_columns = ss['selected_columns']
        selected_values = ss['selected_values']
        selected_funds = ss['selected_funds']

        if len(selected_columns) == 0 or len(selected_values) == 0:
            st.warning('Please select at least one column and one value!')
            ss['sql_statement'] = ''
            return True
        
        if len(selected_funds) == 0: 
            st.warning('Please select at least one fund!')
            ss['sql_statement'] = ''
            return True

        return False
    
    def build_query():
        selected_columns = [columns[column] for column in ss['selected_columns']]
        selected_values = [values[column] for column in ss['selected_values']]

        fund_codes = str(ss['selected_funds']).replace('[', '').replace(']', '')
        current_date = ss['selected_date']
        comparison_date = ss['selected_comparison_date']

        mv_list = [column for column in selected_values if 'MV' in column]

        if len(mv_list) == 0:
            selected_values.append('NET_MV')

        query_string = f'SELECT CLOSING_DATE, {", ".join(selected_columns)}, {", ".join(selected_values)} FROM funnel.funnelweb WHERE fund_code IN ({fund_codes}) AND closing_date IN (\'{current_date}\', \'{comparison_date}\') ORDER BY closing_date DESC;'
        
        with st.expander('SQL Statement'):
            st.write(query_string)
            
        return query_string

    def query_data(query_string: str):
        if query_string == ss['sql_statement']:
            return ss['query_df']
        
        with st.spinner('Fetching your requested data...'):
            df = ss['query_df'] = query(query_string)

        ss['sql_statement'] = query_string

        return df

    def build_grid(df: pd.DataFrame):
        df['CLOSING_DATE'] = pd.to_datetime(df['CLOSING_DATE']).dt.strftime('%Y-%m-%d')

        current_date = df['CLOSING_DATE'].unique()[0]
        comparison_date = df['CLOSING_DATE'].unique()[1]

        selected_columns = ss['selected_columns']
        selected_values = ss['selected_values']

        grid = AgGridBuilder(df)

        columnComparator = """
        function sort(valueA, valueB, nodeA, nodeB, isDescending) {
            let mvA = nodeA.aggData["pivot_CLOSING_DATE_{CURRENT_DATE}_{SELECTED_VALUE}"];
            let mvB = nodeB.aggData["pivot_CLOSING_DATE_{CURRENT_DATE}_{SELECTED_VALUE}"];

            if (mvA > mvB) {
                return 1;
            }
            else {
                return -1;
            }
        }
        """

        valueComparator = """
        function weightedAverage(params) {
            console.log(params);

            let node = params.rowNode;

            let assetType = node.id;
            console.log(assetType);

            let properties = {};

            while (node.id != "ROOT_NODE_ID") {
                let field = node.field;
                let key = node.key;

                properties[field] = key;

                node = node.parent;
            }

            let date = params.pivotResultColumn.colId.split("_")[3];
            properties["CLOSING_DATE"] = date;

            console.log(date);

            let keys = Object.keys(properties);
            console.log(JSON.stringify(properties));

            let totalWeight = 0;
            let weightedSum = 0;
            
            params.rowNode.allLeafChildren.forEach((value) => {
                let valueProperties = {};
                let match = true;

                keys.map(function(key) {
                    let keyProperty = properties[key];
                    let valueProperty = value.data[key];

                    if (keyProperty != valueProperty) {
                        match = false;
                    }
                });

                if (match) {
                    let weight = value.data["{weight}"];
                    let sum = value.data["{field}"];

                    if (sum != 0) {
                        totalWeight += weight;
                        weightedSum += weight * sum;
                    }
                }
            });

            if (totalWeight > 0) {
                weightedSum /= totalWeight;
            }
            
            return weightedSum;
        }
        """

        mv_list = [column for column in selected_values if 'MV' in column]

        columnComparator = columnComparator.replace("{CURRENT_DATE}", current_date).replace("{SELECTED_VALUE}", selected_values[0])

        pivotComparator = grid.customOrderComparatorString.replace('value', f'{current_date}\', \'{comparison_date}')
        
        grid.add_options()
        grid.add_columns([columns[column] for column in selected_columns], value_formatter=None, comparator=columnComparator, sort='desc', labels=selected_columns)
        
        sum_values = [column for column in selected_values if values_function[column] == 'sum']
        wa_values = [column for column in selected_values if values_function[column] == 'wa']

        grid.add_values([values[column] for column in sum_values], labels=sum_values)
        
        for column in wa_values:
            comparator = valueComparator.replace("{weight}", values[mv_list[0]]).replace("{field}", values[column])
            
            grid.add_value(column, values[column], comparator)

        grid.set_pivot_column(comparator=pivotComparator)
        grid.show_grid()

    load = False

    if st.button('Load Data'):
        load = True
    
    empty = check_columns_values()

    if empty or not load:
        return

    query_string = build_query()

    df = query_data(query_string)

    build_grid(df)

    st.toast('Loaded info!', icon='🎉')
    st.write('Note: by default the grid is sorted by the first value selected')

with st.expander('Filters', True):
    dates = get_funnelweb_dates()

    build_date_filter_buttons('Valuation Date', dates, key='selected_date')
    build_date_filter_buttons('Comparison Date', dates, key='selected_comparison_date', date=ss['selected_date'])
    build_lbu_filter()

    selected_columns = st.multiselect('Columns', columns.keys(), key='selected_columns')
    selected_values = st.multiselect('Values', values.keys(), key='selected_values')

load_data()