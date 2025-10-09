from grid import AgGridBuilder

def build_grid(df):
    grid = AgGridBuilder(df)
    grid.add_columns(['Order', 'Level'], None, row_group=False, pinned='left')
    grid.add_column('Asset Type', None, {'border-right': '1px solid rgb(232,119,34)'}, pinned='left')
    
    ignore_columns = ['Order', 'Level', 'Asset Type']
    conditional_formatting_columns = ['MV Δ %', 'SAA Δ %']

    for column in df.columns.tolist():
        if column in ignore_columns:
            continue
        elif column in conditional_formatting_columns:
            grid.add_column(column)
        else:
            grid.add_column(column, cell_style=None)
    
    grid.show_grid()