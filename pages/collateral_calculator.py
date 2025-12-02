import streamlit as st
from interface import initialize
from pages.collateral import build_filters, verify_to_load, get_data, calculate_haircuts, build_grid

class CollateralCalculatorConfig:
    REPORT_FIELDS = [
        'POSITION_ID',
        'FUND_CODE',
        'ACCOUNT_CODE',
        'SECURITY_NAME',
        'BBGID_V2',
        'ISIN',
        'NET_MV',
        'POSITION',
        'PLEDGE_POS',
    ]
    
    EXTRA_FIELDS = ['POSITION',
        'UNIT',
        'ISSUER',
    ]
    
    ELIGIBLE_ASSET_TYPES = {'Cash': 'Cash', 'JGB': 'Government Bond', 'UST': 'Treasury', 'HKGB': 'Government Bond', 'Corporate Bonds': 'Corporate Bond'}
    CUSTOM_FUNCTIONS = {}
    
    AGENCIES = {'S&P': 'SP', 'Moodys': 'MOODYS', 'Fitch': 'FITCH'}
    AGENCY_MAPPINGS = None
    
    CSA_FUNDS_MAPPED = None
    CSA_DETAILS = None
    CSA_LOGICS = None
    CSA_VALUATIONS = None
    CSA_COUNTERPARTIES = None

    FUNDS = {
        'Par': [
            'HK: Trad', 'HK: MF1', 'HK: MF2', 'HK: MF3-5/10p', 'HK: MF4-5/10p',
            'HK: MF5-5/10p', 'HK: MF6', 'HK: CrisisXD', 'HK: W ICON', 'HK: W ICON 4',
            'HK: W ICON 5 RMB', 'HK: W ICON 5', 'HK: UL1', 'HK: UL2', 'HK: UL2.1',
            'HK: UL2.2', 'HK: Provie', 'HK: IUL'
        ],
        'Non Par': [
            'HK: SHF', 'HK: Trad Non-Par', 'HK: BSH', 'HK: MTE', 'HK: PDA', 'HK: DCA'
        ]
    }


initialize()

build_filters(CollateralCalculatorConfig)

verify_to_load()

config, df = get_data(CollateralCalculatorConfig)

df = calculate_haircuts(config, df)

build_grid(config, df)