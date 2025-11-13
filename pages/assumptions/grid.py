import streamlit as st
from streamlit import session_state as ss
from grid import AgGridBuilder

def build_grid(config):
    df = config.METRIC_VALUES
    
    group_columns = ['LBU_GROUP', 'CATEGORY', 'SUBCATEGORY', 'TENOR_DAYS', 'TENOR']
        
    dates = df['PROJECTED_DATE'].unique()
    df['VALUE'] = df['VALUE'].astype(float)
    
    df_pivot = df.pivot_table(
        index=['LBU_GROUP', 'CATEGORY', 'SUBCATEGORY', 'TENOR_DAYS', 'TENOR'],
        columns='PROJECTED_DATE',
        values='VALUE',
        aggfunc='sum'
    ).reset_index().sort_values(by=['LBU_GROUP', 'CATEGORY', 'SUBCATEGORY', 'TENOR_DAYS'])
    
    df_pivot.insert(df_pivot.columns.get_loc('TENOR') + 1, 'Spot', df_pivot.pop('Spot'))
    df_pivot = df_pivot.drop(columns=['TENOR_DAYS'])
    
    group_columns.remove('TENOR_DAYS')
    
    grid = AgGridBuilder(df_pivot)

    grid.add_columns(group_columns, None, pinned='left', row_group=False)
    grid.add_columns(dates, row_group=False)
    
    grid.show_grid()
    
    df = df.loc[:, ~df.columns.str.contains('_ID')]
    grid = AgGridBuilder(df)
    grid.show_grid(340)