from grid import AgGridBuilder

def build_grid(df):        
    grid = AgGridBuilder(df)
    columns = list(df.columns)
    
    grid.add_columns([column for column in columns if column != 'NET_MV'], None, row_group=False)
    grid.add_values(['NET_MV'], ['Net MV'])

    height = (len(df) + 1) * 30
    grid.show_grid(height)