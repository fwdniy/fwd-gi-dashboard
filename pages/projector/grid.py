import streamlit as st
from grid import AgGridBuilder
from .chart import build_chart

def _build_cashflow_grid(df):
    grid = AgGridBuilder(df)
    
    columns = list(df.columns)
    values = [column for column in columns if column != 'YEAR']
        
    grid.gb.configure_grid_options(rowSelection={'mode': 'multiRow', 'groupSelects': 'filteredDescendants', 'checkboxLocation': 'autoGroupColumn', 'suppressRowClickSelection': False})
    
    for value in values:
        grid.add_column(value, cell_style=None)
        
    grid.show_grid(height=490, update_on=[('selectionChanged', 2000)], update_mode="NO_UPDATE", key='years_grid')
        
    return grid.grid['selected_rows']

def _build_selected_grid(df, selected_years):
    if selected_years is None:
        return
    
    selected_years = list(selected_years['YEAR'])
    df = df[df['YEAR'].isin(selected_years)]
    df = df.sort_values(by=['YEAR', 'VALUE'], ascending=[True, False])
    
    grid = AgGridBuilder(df, min_width=100)
    grid.add_column('VALUE', cell_style=None)
    grid.add_column('COUPON', cell_style=None)
    grid.add_column('PRINCIPAL', cell_style=None)
    grid.add_column('NOTIONAL', cell_style=None)
    grid.show_grid()
    
@st.fragment
def build_visuals(yearly_df, CASHFLOW_TYPES, CASHFLOW_COLORS, security_df):
    selected_years = _build_cashflow_grid(yearly_df)

    build_chart(yearly_df, CASHFLOW_TYPES, CASHFLOW_COLORS)

    _build_selected_grid(security_df, selected_years)