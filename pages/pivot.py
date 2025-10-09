from interface import initialize
from pages.pivot import build_filters, verify_to_load, get_data, build_grid

class PivotConfig:
    # Constants for pivot configuration
    COLUMNS = {
        'LBU Group': 'LBU_GROUP',
        'LBU Code': 'LBU_CODE',
        'Account Code': 'ACCOUNT_CODE',
        'Fund Code': 'FUND_CODE',
        'Fund Type': 'FUND_TYPE',
        'Manager': 'MANAGER',
        'FWD Asset Type': 'FWD_ASSET_TYPE',
        'BBG Asset Type': 'BBG_ASSET_TYPE',
        'L1 Asset Type': 'L1_ASSET_TYPE',
        'L2 Asset Type': 'L2_ASSET_TYPE',
        'L3 Asset Type': 'L3_ASSET_TYPE',
        'L4 Asset Type': 'L4_ASSET_TYPE',
        'Currency': 'CURRENCY',
        'Final Rating': 'FINAL_RATING',
        'Final Rating Letter': 'FINAL_RATING_LETTER',
        'Country': 'COUNTRY_REPORT',
        'Issuer': 'ISSUER',
        'Ultimate Parent': 'ULTIMATE_PARENT_NAME',
        'CAST Parent': 'CAST_PARENT_NAME',
        'Industry Sector': 'INDUSTRY_SECTOR',
        'Industry Group': 'INDUSTRY_GROUP',
        'Industry': 'INDUSTRY',
        'Ult Parent Industry Group': 'ULT_PARENT_INDUSTRY_GROUP'
    }

    VALUES = {
        'Net MV': 'NET_MV',
        'Clean MV': 'CLEAN_MV_USD',
        'Credit Spread': 'CREDIT_SPREAD_BP',
        'Duration': 'DURATION',
        'YTM': 'YTM',
        'DV01 000s': 'DV01_000',
        'CS01 000s': 'CS01_000',
        'Convexity': 'CONVEXITY',
        'WARF': 'WARF'
    }

    VALUES_FUNCTION = {
        'Net MV': 'sum',
        'Clean MV': 'sum',
        'Credit Spread': 'wa',
        'Duration': 'wa',
        'YTM': 'wa',
        'DV01 000s': 'sum',
        'CS01 000s': 'sum',
        'Convexity': 'wa',
        'WARF': 'wa'
    }


initialize()

build_filters(PivotConfig)

verify_to_load()

df = get_data(PivotConfig)

build_grid(PivotConfig, df)