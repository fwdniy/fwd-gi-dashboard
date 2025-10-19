import streamlit as st
from grid import AgGridBuilder

def build_grid(config, df):
    _build_valuations_grid(config)
    _build_summary_grid(config, df)
    _build_main_grid(config, df)
    
def _build_valuations_grid(config):
    df = config.CSA_VALUATIONS
    
    agency_mappings = config.AGENCY_MAPPINGS
    agency_mapping = {v: k for k, v in agency_mappings['S&P'].items()}
    agencies = config.AGENCIES
    
    for agency in agencies.values():
        df[f'{agency}_LOWER'] = df[f'{agency}_LOWER'].map(agency_mapping)
        df[f'{agency}_UPPER'] = df[f'{agency}_UPPER'].map(agency_mapping)
        
    csa_details = config.CSA_DETAILS
    csa_mapping = {row['ID']: row['NAME'] for _, row in csa_details.iterrows()}
    df['CSA_ID'] = df['CSA_ID'].map(csa_mapping)
    df.rename(columns={'CSA_ID': 'COUNTERPARTY'}, inplace=True)
    
    df['PERCENTAGE'] = df['PERCENTAGE'] * 100
    
    grid = AgGridBuilder(df)
    grid.show_grid(height=300)
    
def _build_summary_grid(config, df):
    counterparties = config.CSA_COUNTERPARTIES
    counterparty_mv_columns = [f'{cp} Haircut MV' for cp in counterparties]
    column_sums = df.groupby('ASSET_TYPE')[counterparty_mv_columns].sum().reset_index()
    column_sums.rename(columns=lambda x: x.replace(' Haircut MV', ''), inplace=True)
    column_sums = column_sums.transpose()
    column_sums.columns = column_sums.iloc[0]
    column_sums = column_sums[1:].reset_index()
    column_sums.rename(columns={'index': 'ASSET_TYPE'}, inplace=True)
    column_sums.rename(columns={'ASSET_TYPE': 'COUNTERPARTY'}, inplace=True)
    
    grid = AgGridBuilder(column_sums)
    
    for col in column_sums.columns:
        if col != 'COUNTERPARTY':
            column_sums[col] = column_sums[col] / 1_000_000
            grid.add_column(col, cell_style=None, row_group=False)
    
    height = 30 + 30 * len(column_sums) + 1
    
    grid.show_grid(height=height)
    
def _build_main_grid(config, df):
    haircut_columns = [col for col in df.columns if 'Haircut' in col]
    grid_df = df[config.REPORT_FIELDS + haircut_columns]

    grid = AgGridBuilder(grid_df)

    for col in grid_df.columns:
        if 'MV' in col:
            grid_df[col] = grid_df[col] / 1_000_000
            grid.add_column(col, cell_style=None, row_group=False)
        elif 'Percentage' in col:
            grid_df[col] = grid_df[col] * 100
            grid.add_column(col, cell_style=None, row_group=False)
    
    grid.show_grid()