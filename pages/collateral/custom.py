ISSUERS = {'US Treasury': {'BILLS': 'TREASURY BILL', 'BONDS': 'US TREASURY N/B', 'NOTES': 'US TREASURY N/B', 'STRIPS': 'STRIP PRINC', 'FRN': 'US TREASURY FRN', 'TIPS': 'TSY INFL IX N/B'},
           'Government of the United States': {'BILLS': 'TREASURY BILL', 'BONDS': 'US TREASURY N/B', 'NOTES': 'US TREASURY N/B', 'STRIPS': 'STRIP PRINC', 'FRN': 'US TREASURY FRN', 'TIPS': 'TSY INFL IX N/B'},
           'Hong Kong Government': {'BONDS': 'HONG KONG GOV\'T'},
           'Government of Japan': {'BILLS': 'JAPAN TREASURY DISC BILL', 'BONDS': 'JAPAN (', 'TIPS': 'JAPAN GOVT CPI LINKED', 'STRIPS': 'JAPAN PRINC', 'COUPON': 'JAPAN GOVT COUPON STRIPS'}}

ISSUER_NICKNAMES = {'UST': 'US Treasury', 'JGB': 'Government of Japan', 'HKGB': 'Hong Kong Government'}

def add_functions_to_config(config):
    config.CUSTOM_FUNCTIONS['CURRENCY'] = process_currency
    config.CUSTOM_FUNCTIONS['ISSUER'] = process_issuer
    config.CUSTOM_FUNCTIONS['FORM'] = process_form
    config.CUSTOM_FUNCTIONS['PRINCIPAL_BALANCE_LIMIT'] = process_principal_balance_limit
    config.CUSTOM_FUNCTIONS['COUNTRY_CONCENTRATION_LIMIT'] = process_country_concentration_limit
    config.CUSTOM_FUNCTIONS['COLLATERAL_LIMIT'] = process_collateral_limit
    
    return config

def process_currency(logic_details, csa, df):
    value = logic_details['VALUE']
    
    currencies = [value]
    
    if value == 'Base':
        currencies = [csa['BASE_CURRENCY']]
    elif value == 'Eligible':
        currencies = csa['ELIGIBLE_CURRENCY'].split(';')
    
    df = df[df['CURRENCY'].isin(currencies)]
    
    return df

def process_issuer(logic_details, csa, df):
    value = logic_details['VALUE']
    issuers = list(ISSUERS[value].values())
    
    df = df[df['ISSUER'].isin(issuers)]
    
    return df

def process_form(logic_details, csa, df):
    asset_type = logic_details['ASSET_TYPE']
    value = logic_details['VALUE']
    logic = logic_details['LOGIC']
    
    issuers = ISSUERS[ISSUER_NICKNAMES[asset_type]]
    
    if logic == 'NOT EQUALS':
        eligible_forms = [issuer for form, issuer in issuers.items() if form not in value.split(';')]
    else:
        pass
    #eligible_forms = [issuers[form] for form in value.split(';')]
    
    df = df[df['ISSUER'].isin(eligible_forms)]
    
    return df

def process_principal_balance_limit(logic_details, csa, df):
    value = float(logic_details['VALUE'])
    df['NOTIONAL'] = df['POSITION'] * df['UNIT']
    
    df = df[df['NOTIONAL'] < df['AMOUNT_OUTSTANDING'] * value]
    
    df = df.drop(columns=['NOTIONAL'])
    
    return df

def process_country_concentration_limit(logic_details, csa, df):
    return df

def process_collateral_limit(logic_details, csa, df):
    return df