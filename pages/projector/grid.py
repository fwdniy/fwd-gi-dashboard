import streamlit as st
from grid import AgGridBuilder
from .chart import build_chart

def _build_cashflow_grid(df, period):
    grid = AgGridBuilder(df)
    
    columns = list(df.columns)
    values = [column for column in columns if column != period]
        
    grid.gb.configure_grid_options(rowSelection={'mode': 'multiRow', 'groupSelects': 'filteredDescendants', 'checkboxLocation': 'autoGroupColumn', 'suppressRowClickSelection': False})
    
    for value in values:
        grid.add_column(value, cell_style=None)
        
    grid.show_grid(height=490, update_on=[('selectionChanged', 2000)], update_mode="NO_UPDATE", key='period_grid')
        
    return grid.grid['selected_rows']

def _build_selected_grid(df, selected_periods, period):
    if selected_periods is None:
        return
    
    selected_periods = list(selected_periods[period])
    df = df[df[period].isin(selected_periods)]
    df = df.sort_values(by=[period, 'VALUE'], ascending=[True, False])
    
    grid = AgGridBuilder(df, min_width=100)
    grid.add_column('VALUE', cell_style=None)
    grid.add_column('COUPON', cell_style=None)
    grid.add_column('PRINCIPAL', cell_style=None)
    grid.add_column('NOTIONAL', cell_style=None)
    grid.show_grid()
    
@st.fragment
def build_visuals(period_df, CASHFLOW_TYPES, CASHFLOW_COLORS, security_df, monthly=False, hide_trends=False):
    period = 'YEAR'
    
    if monthly:
        period = 'MONTH'
    
    selected_periods = _build_cashflow_grid(period_df, period)

    build_chart(period_df, CASHFLOW_TYPES, CASHFLOW_COLORS, period, hide_trends)

    _build_selected_grid(security_df, selected_periods, period)