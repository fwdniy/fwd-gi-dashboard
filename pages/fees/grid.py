import streamlit as st
from grid import AgGridBuilder
from grid.js import get_weighted_average_sum
from .filters import build_pivot_filter, build_period_filter

def build_grid(df):
    modes = {'Asset Type': 'ASSET_TYPE', 'Manager': 'MANAGER'}
    pivot_mode = build_pivot_filter(modes)
    period_mode = build_period_filter()
    df['FEE_K'] = df['FEE_K'] / period_mode
        
    grid = AgGridBuilder(df)
    group_columns = ['LBU_GROUP_NAME', 'LBU_CODE_NAME', group_column]
    
    grid.add_options(group_total='bottom', header_name=' / '.join(group_columns), group_expanded=1)
    grid.add_columns(group_columns, None, sort='desc')
    grid.add_values(['NET_MV', 'FEE_K'], ['MV ($ mn)', 'Fee ($ k)'], max_width=120)
    
    valueComparator = """
        function weightedAverage(params) {                        
            let totalWeight = 0;
            let weightedSum = 0;
            
            console.log(params);
            console.log(params.pivotResultColumn.colId);
            let colIdParts = params.pivotResultColumn.colId.split('_');
            let asset_type = colIdParts[{INDEX}];
            
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
    #grid.add_value('FEE_BPS', 'Fee (bps)', max_width=100)
    grid.set_pivot_column(pivot_mode)
    grid.show_grid()