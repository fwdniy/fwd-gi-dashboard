import streamlit as st
from streamlit import session_state as ss
import pandas as pd
from grid import AgGridBuilder
from grid.js import get_custom_comparator

@st.fragment
def build_grid(config, df):
    columns = config.COLUMNS
    values = config.VALUES
    values_function = config.VALUES_FUNCTION
    
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
    
    if len(mv_list) == 0:
        mv_list = ['Net MV']
        
    for column in mv_list:
        df_column = values[column]
        if df_column and df_column in df.columns and max(df[df_column]) > 1_000_000:
            df[df_column] = df[df_column] / 1_000_000

    columnComparator = columnComparator.replace("{CURRENT_DATE}", current_date).replace("{SELECTED_VALUE}", selected_values[0])

    pivotComparator = get_custom_comparator().replace('value', f'{current_date}\', \'{comparison_date}')
    
    grid.add_options()
    grid.add_columns([columns[column] for column in selected_columns], value_formatter=None, comparator=columnComparator, sort='desc', labels=selected_columns)
    
    sum_values = [column for column in selected_values if values_function[column] == 'sum']
    wa_values = [column for column in selected_values if values_function[column] == 'wa']

    grid.add_values([values[column] for column in sum_values], sum_values)
    
    for column in wa_values:
        comparator = valueComparator.replace("{weight}", values[mv_list[0]]).replace("{field}", values[column])
        
        grid.add_value(values[column], column, comparator)

    grid.set_pivot_column(comparator=pivotComparator)
    grid.show_grid()