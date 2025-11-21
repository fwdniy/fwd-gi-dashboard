import streamlit as st
from streamlit import session_state as ss
from grid import AgGridBuilder
from .filters import build_pivot_filter, build_row_group_filter, build_period_filter
from utils.download import create_download_button

def build_grid(df, modes):
    pivot_mode = build_pivot_filter(modes)    
    
    group_column_labels = build_row_group_filter({key: value for key, value in modes.items() if value != pivot_mode})
    group_columns = [modes[mode] for mode in group_column_labels]
    
    period_mode = build_period_filter()
    df['FEE_K'] = df['FEE_K'] / period_mode
        
    grid = AgGridBuilder(df)
    
    grid.add_options(group_total='bottom', header_name=' / '.join(group_column_labels), group_expanded=1)
    grid.add_columns(group_columns, None, sort='desc')
    grid.add_values(['NET_MV', 'FEE_K'], ['MV ($ mn)', 'Fee ($ k)'], max_width=120)
    
    valueComparator = """
        function weightedAverage(params) {                        
            let totalWeight = 0;
            let weightedSum = 0;
            
            console.log(params);
            console.log(params.pivotResultColumn.colId);
            let colIdParts = params.pivotResultColumn.colId.split('_');
            let asset_type = colIdParts[colIdParts.length - 3];
            
            params.rowNode.allLeafChildren.forEach((value) => {
                console.log(value);
                let mv = value.data["NET_MV"];
                
                if (mv != 0 && value.data["{PIVOT_COLUMN}"] == asset_type) {
                    let fee = value.data["FEE_BPS"];
                    totalWeight += mv;
                    weightedSum += fee * mv;
                }
            });
            
            if (totalWeight > 0) {
                weightedSum /= totalWeight;
            }            
            
            return weightedSum;
        }
    """
    
    valueComparator = valueComparator.replace("{INDEX}", '3' if pivot_mode == 'ASSET_TYPE' else '2')
    valueComparator = valueComparator.replace("{PIVOT_COLUMN}", pivot_mode)
    
    grid.add_value('FEE_BPS', 'Fee (bps)', valueComparator, max_width=100)
    
    grid.set_pivot_column(pivot_mode)
    grid.show_grid()
    
    file_name = f'Fees Data {ss.selected_month_end}'
    create_download_button(df, file_name, file_name, "Unpivoted Data", True)
    
    st.caption('*Pivot column means the grouping used in the columns.')
    st.caption('^Period refers to the divisor of the fees (Monthly = 12, Quarterly = 4, Yearly = 1). The data used is still based on the manager\'s billing frequency (monthly / quarterly).')