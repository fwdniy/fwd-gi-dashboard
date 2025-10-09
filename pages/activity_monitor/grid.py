import streamlit as st
from streamlit import session_state as ss
import pandas as pd
from grid import AgGridBuilder
from .analysis import build_analysis

@st.fragment
def build_grid_and_analysis(config, df, selected_columns, value_columns, trans_cols, trans_col_headers):
    """Build the main grid and analysis section"""
    selected_rows = _build_grid(df, selected_columns, value_columns, trans_cols, trans_col_headers)
    #generate_report(df)
    build_analysis(config, df, selected_rows, selected_columns, trans_col_headers)

def _build_grid(df, selected_columns, selected_values, transaction_columns, transaction_column_headers):
    """Build the main grid"""
    value_columns = []
    
    start_date = ss.start_date_string
    end_date = ss.end_date_string
    
    for date in [start_date, end_date]:
        for column in selected_values[date]:
            value_columns.append(column['field'])
    
    grid_df = df.groupby(selected_columns)[value_columns + [item for sublist in transaction_column_headers.values() for item in sublist]].sum().reset_index()
    total_df = grid_df.groupby('FWD_ASSET_TYPE')[value_columns + [item for sublist in transaction_column_headers.values() for item in sublist]].sum().reset_index()
    total_df['LBU_GROUP'] = 'Total'
    
    grid_df = pd.concat([grid_df, total_df], axis=0)
    
    grid = AgGridBuilder(grid_df, min_width=100)
    grid.add_options(group_total=None, row_selection={'mode': 'multiRow', 'groupSelects': 'filteredDescendants', 'checkboxLocation': 'autoGroupColumn', 'suppressRowClickSelection': False}, header_name=' / '.join(ss['selected_columns']), group_expanded=0)

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

    grid.add_columns(selected_columns, value_formatter=None, sort='desc', comparator=customOrderComparatorString)
    
    for key, value in selected_values.items():
        grid.gb.configure_column(key, children=value)
    
    grid.gb.configure_column('Transactions', children=transaction_columns)
        
    grid.show_grid(update_on=[('selectionChanged', 2000)], update_mode="NO_UPDATE", key='activity_grid')
    
    selected_rows = grid.grid['selected_rows']
    
    return selected_rows

def generate_report(df):
    st.write(df)