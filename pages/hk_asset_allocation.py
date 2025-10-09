from interface import initialize
from pages.hk_asset_allocation import build_filters, verify_to_load, load_data

initialize()

build_filters()

verify_to_load()
    
load_data()