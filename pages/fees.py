from interface import initialize
from pages.fees import build_month_end_filters, get_data, get_fee_data, process_fee_data, calculate_fees, build_fees_filters, build_grid

class FeeConfig:
    CALC_MODES = {}
    CALC_MODES_ID = {}
    MV_MODES = {}
    MV_MODES_ID = {}
    MANAGERS = {}
    MANAGERS_ID = {}
    MANAGERS_MV_MODES = {}
    USER_DICT = {}
    USER_DICT_ID = {}
    FEE_GROUPS = None
    FEE_DETAILS = None
    FEES = None
    CUSTOM_MANAGER_DATA = None
    GRID_MODES = {'LBU': 'LBU_GROUP_NAME', 'Sub LBU': 'LBU_CODE_NAME', 'Manager': 'MANAGER', 'Asset Type': 'ASSET_TYPE'}

initialize()

build_month_end_filters()

df = get_data()

get_fee_data(FeeConfig)

process_fee_data(FeeConfig)

fees_df = calculate_fees(df, FeeConfig)

fees_df = build_fees_filters(fees_df)

build_grid(fees_df, FeeConfig.GRID_MODES)