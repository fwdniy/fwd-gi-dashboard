import streamlit as st
from grid import AgGridBuilder

def build_grid(df):
    grid = AgGridBuilder(df)
    #grid.add_options(pivot_mode=False, group_total=False, cell_value_change='onCellValueChanged', pinned_top=[{'ADMIN': False}])
    grid.add_options(pivot_mode=False, group_total=False, cell_value_change='onCellValueChanged')
    grid.add_columns(['EMAIL', 'NAME', 'LBU', 'PERMISSIONS'], None, editable=True, row_group=False)
    grid.show_grid(400)
        
    return grid