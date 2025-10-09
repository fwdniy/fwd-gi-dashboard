from grid import AgGridBuilder
from grid.js import get_custom_comparator, get_weighted_average_sum

# Constants
DELTA_STYLE_RANGES = {
    'lower_bound': lambda df: sum(df['Current Date']) * -0.05 / 2,
    'mid_point': 0,
    'upper_bound': lambda df: sum(df['Current Date']) * 0.05 / 2
}

# Helper Functions
def _get_comparator(df, group_by_col, value_col):
    """Generate a custom comparator based on grouped and sorted values."""
    custom_comparator = get_custom_comparator()
    sorted_values = df.groupby(group_by_col).agg({value_col: 'sum'}).sort_values(by=value_col, ascending=False).index.tolist()
    return custom_comparator.replace('value', "', '".join(sorted_values))

def build_grid_bbg(df):
    """Build grid for Bloomberg Asset Type."""
    grid = AgGridBuilder(df)
    
    height = 120 + 30 * len(df) + 1

    # Add columns excluding specific ones
    grid.add_columns(
        [col for col in df.columns if 'Bloomberg' not in col and "Δ" not in col],
        row_group=False
    )

    # Add Delta columns with styling
    grid.add_column('Delta Δ', cell_style_ranges={k: v(df) if callable(v) else v for k, v in DELTA_STYLE_RANGES.items()})
    grid.add_column('Delta Δ %')

    # Show grid with dynamic height
    grid.show_grid(height)

def build_grid_sum(df, value_column, header):
    grid = AgGridBuilder(df)
    
    asset_type_count = df['FWD_ASSET_TYPE'].nunique()
    height = 120 + 30 * asset_type_count
    
    grid.add_options(pivot_total='left', group_total=True, remove_pivot_headers=False)

    # Add columns and pivot settings
    grid.add_column('FWD_ASSET_TYPE', value_formatter=None, sort='asc', row_group=True)
    grid.set_pivot_column('ENTITY', _get_comparator(df, 'ENTITY', 'SUM_NET_MV'))
    grid.set_pivot_column('HK_CODE', _get_comparator(df, 'HK_CODE', 'SUM_NET_MV'))

    # Add value column
    grid.add_value(value_column, header)

    # Show grid with specified height
    grid.show_grid(height)

def build_grid_wa(df, sum_df, header):
    grid = AgGridBuilder(df)
    
    asset_type_count = df['FWD_ASSET_TYPE'].nunique()
    height = 120 + 30 * asset_type_count
    
    grid.add_options(pivot_total='left', group_total=True, remove_pivot_headers=False)
    grid.add_column('FWD_ASSET_TYPE', value_formatter=None, sort='asc', row_group=True)

    weighted_func = get_weighted_average_sum().replace("FUND_CODE", "HK_CODE")
    custom_comparator = get_custom_comparator()
    
    weight_comparator = weighted_func.replace("aggColumn", 'SUMPRODUCT').replace("weightColumn", 'SUM_NET_MV')
    entity_comparator = custom_comparator.replace('value', "', '".join(sum_df.groupby('ENTITY').agg({'SUM_NET_MV': 'sum'}).sort_values(by='SUM_NET_MV', ascending=False).index.tolist()))
    fund_comparator = custom_comparator.replace('value', "', '".join(sum_df.groupby('HK_CODE').agg({'SUM_NET_MV': 'sum'}).sort_values(by='SUM_NET_MV', ascending=False).index.tolist()))

    grid.set_pivot_column('ENTITY', entity_comparator)
    grid.set_pivot_column('HK_CODE', fund_comparator)
    grid.add_value('SUMPRODUCT', header, weight_comparator)

    grid.show_grid(height)
    
def build_grid_ratings(df):
    grid = AgGridBuilder(df)
    
    asset_type_count = df['FINAL_RATING'].nunique()
    height = 120 + 30 * asset_type_count
    
    grid.add_options(pivot_total='left', group_total=True, remove_pivot_headers=False)
    grid.add_columns(['FINAL_RATING'], value_formatter=None, sort='')

    custom_comparator = get_custom_comparator()

    entity_comparator = custom_comparator.replace('value', "', '".join(df.groupby('ENTITY').agg({'SUM_NET_MV': 'sum'}).sort_values(by='SUM_NET_MV', ascending=False).index.tolist()))
    fund_comparator = custom_comparator.replace('value', "', '".join(df.groupby('HK_CODE').agg({'SUM_NET_MV': 'sum'}).sort_values(by='SUM_NET_MV', ascending=False).index.tolist()))

    grid.set_pivot_column('ENTITY', entity_comparator)
    grid.set_pivot_column('HK_CODE', fund_comparator)
    grid.add_value('SUM_NET_MV', 'MV')
    grid.show_grid(height)

def build_grid_nr(df, expanded):
    grid = AgGridBuilder(df)
    grid.add_options(pivot_total='left', group_total=True, remove_pivot_headers=False, pivot_mode=False, group_expanded=expanded)
    grid.add_columns(['SECURITY_NAME'], value_formatter=None, hide=True)
    grid.add_columns(['FUND_CODE'], row_group=False, value_formatter=None)
    grid.add_value('NET_MV', 'Net MV')

    grid.show_grid()