import streamlit as st
from streamlit import session_state as ss
from st_aggrid import JsCode

from grid.formatting import format_numbers, conditional_formatting

#@st.cache_data(show_spinner=False)
def build_value_columns(config, df, selected_values):
    """Build value columns for the grid. This includes the start and end date values and the delta value."""
            
    start_columns = []
    end_columns = []
    delta_columns = []
    
    for column in selected_values:
        label = [column_name for column_name in config.FILTER_VALUES if config.FILTER_VALUES[column_name] == column][0]
        
        if column in config.FILTER_VALUES_SUM:
            (start_column, end_column, delta_column) = _build_sum_value_column(df, label, column, config.FILTER_VALUES_SUM[column])
        elif column in config.FILTER_VALUES_WA:
            (start_column, end_column, delta_column) = _build_weighted_average_value_column(df, label, column)
            
        start_columns.append(start_column)
        end_columns.append(end_column)
        delta_columns.append(delta_column)
            
    value_columns = {ss.start_date_string: start_columns, ss.end_date_string: end_columns, 'Δ Delta': delta_columns}
    
    return value_columns

def _build_sum_value_column(df, label, column, divisor):
    """
    Build sum value column for the grid. This includes the start and end date values and the delta value.
    Args:
        label (str): The label for the column
        column (str): The column to apply the logic to
        divisor (float): The divisor to divide the notionals by
    """
    
    df[column + '_START'] = df.apply(lambda row: row[column] / divisor if row['CLOSING_DATE'] == ss.start_date_string else 0, axis=1)
    df[column + '_END'] = df.apply(lambda row: row[column] / divisor if row['CLOSING_DATE'] == ss.end_date_string else 0, axis=1)
    
    start_column = {"headerName": label, "field": column + "_START", "aggFunc": "sum", "valueFormatter": format_numbers()}
    end_column = {"headerName": label, "field": column + "_END", "aggFunc": "sum", "valueFormatter": format_numbers()}
    
    deltaValueComparator = """
        function deltaValue(params) {
            return parseFloat((params.data.COLUMN_END - params.data.COLUMN_START).toFixed(6));
        }
    """
    
    deltaValueComparator = deltaValueComparator.replace("COLUMN", column)
    
    delta_column = {
        "headerName": label, 
        "valueGetter": JsCode(deltaValueComparator), 
        "aggFunc": "sum", 
        "valueFormatter": format_numbers(), 
        "cellStyle": conditional_formatting(lower_bound=-250, mid_point=0, upper_bound=250)
    }
    
    return (start_column, end_column, delta_column)

def _build_weighted_average_value_column(df, label, column):
    """
    Build weighted average value column for the grid. This includes the start and end date values and the delta value.
    Args:
        label (str): The label for the column
        column (str): The column to apply the logic to
    """
    
    df[column + '_START'] = df.apply(lambda row: row[column] if row['CLOSING_DATE'] == ss.start_date_string else 0, axis=1)
    df[column + '_END'] = df.apply(lambda row: row[column] if row['CLOSING_DATE'] == ss.end_date_string else 0, axis=1)
    
    valueComparator = """
        function weightedAverage(params) {                        
            let totalWeight = 0;
            let weightedSum = 0;
            
            params.rowNode.allLeafChildren.forEach((value) => {
                let datapoint = value.data["COLUMN"];
                
                if (datapoint != 0) {
                    let weight = value.data["NET_MV"];
                    totalWeight += weight;
                    weightedSum += Math.abs(weight * datapoint) * (value.data["POSITION"] >= 0 ? 1 : -1);
                }
            });

            if (totalWeight > 0) {
                weightedSum /= totalWeight;
            }
            
            return weightedSum;
        }
    """
    
    startComparator = valueComparator.replace("COLUMN", column + "_START")
    endComparator = valueComparator.replace("COLUMN", column + "_END")
    
    start_column = {"headerName": label, "field": column + "_START", "aggFunc": JsCode(startComparator), "valueFormatter": format_numbers()}
    end_column = {"headerName": label, "field": column + "_END", "aggFunc": JsCode(endComparator), "valueFormatter": format_numbers()}
    
    deltaValueComparator = """
        function deltaValue(params) {                    
            let totalWeightStart = 0;
            let weightedSumStart = 0;
            let totalWeightEnd = 0;
            let weightedSumEnd = 0;
            
            params.rowNode.allLeafChildren.forEach((value) => {
                let datapoint = value.data["COLUMN_START"];
                
                if (datapoint != 0) {
                    let weight = value.data["NET_MV"];
                    totalWeightStart += weight;
                    weightedSumStart += Math.abs(weight * datapoint) * (value.data["POSITION"] >= 0 ? 1 : -1);
                }
                
                datapoint = value.data["COLUMN_END"];
                
                if (datapoint != 0) {
                    let weight = value.data["NET_MV"];
                    totalWeightEnd += weight;
                    weightedSumEnd += Math.abs(weight * datapoint) * (value.data["POSITION"] >= 0 ? 1 : -1);
                }
            });

            if (totalWeightStart > 0) {
                weightedSumStart /= totalWeightStart;
            }
            
            if (totalWeightEnd > 0) {
                weightedSumEnd /= totalWeightEnd;
            }
            
            return weightedSumEnd - weightedSumStart;
        }
    """
    
    deltaValueComparator = deltaValueComparator.replace("COLUMN", column)
    
    delta_column = {
        "headerName": label, 
        "aggFunc": JsCode(deltaValueComparator), 
        "valueFormatter": format_numbers(), 
        "cellStyle": conditional_formatting(lower_bound=-250, mid_point=0, upper_bound=250)
    }
    
    return (start_column, end_column, delta_column)