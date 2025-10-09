from interface import initialize
from pages.asset_allocation import build_filters, verify_and_load_data, process_data, generate_download_file, build_grid

initialize()

build_filters()

df = verify_and_load_data()

df = process_data(df)

build_grid(df)

generate_download_file(df)