import streamlit as st
from streamlit import session_state as ss
import pandas as pd

from db.data.data_shipment import get_funnelweb_dates, get_hk_code_dict
from .ratings import convert_csa_valuation_ratings
from .custom import add_functions_to_config

def verify_to_load():
    """Verify user selections and load data if all checks pass"""
    if not st.button('Load Data'):
        st.stop()
    
    fund_codes = ss.get('selected_funds')
        
    if not fund_codes:
        st.warning("Please select at least one fund.")
        st.stop()
        
    cps = ss.get('selected_cps')
    
    if len(cps) == 0:
        st.warning("Please select at least one counterparty.")
        st.stop()

def get_data(config):
    config = add_functions_to_config(config)
    
    date = max(get_funnelweb_dates())
    
    df = get_funnelweb_data(date, config)

    config, df = _add_hk_codes(config, df)

    agency_mappings = config.AGENCY_MAPPINGS = get_ratings_mapping(list(config.AGENCIES.keys()))
    
    config.CSA_VALUATIONS = convert_csa_valuation_ratings(config.CSA_VALUATIONS, agency_mappings, config.AGENCIES)
    
    return config, df

def _add_hk_codes(config, df):
    hk_code_dict = get_hk_code_dict()
    df['HK_CODE'] = df['FUND_CODE'].map(hk_code_dict)
    config.REPORT_FIELDS = config.REPORT_FIELDS[:config.REPORT_FIELDS.index('FUND_CODE') + 1] + ['HK_CODE'] + config.REPORT_FIELDS[config.REPORT_FIELDS.index('FUND_CODE') + 1:]
    
    return config, df

def calculate_haircuts(config, fw_df):
    csa_details = config.CSA_DETAILS
    csa_funds_mapped = config.CSA_FUNDS_MAPPED
    csa_logics = config.CSA_LOGICS
    csa_valuations = config.CSA_VALUATIONS
    csa_counterparties = config.CSA_COUNTERPARTIES
    eligible_asset_types = config.ELIGIBLE_ASSET_TYPES
    custom_functions = config.CUSTOM_FUNCTIONS
    agencies = config.AGENCIES
    agency_mappings = config.AGENCY_MAPPINGS
        
    fw_df = fw_df[fw_df['FUND_CODE'].isin(csa_funds_mapped['FUND_CODE'].unique().tolist())].reset_index(drop=True)
    fw_df['ASSET_TYPE'] = None
    
    _check_asset_types_mapped(csa_logics, eligible_asset_types)
    
    for _, csa in csa_details.iterrows():
        csa_id = csa['ID']
        cp = csa['NAME']
        filtered_df = fw_df.copy()

        with st.spinner(f'Calculating haircuts for {cp}...'):
            # Filter for the CSA
            eligible_funds = csa_funds_mapped[csa_funds_mapped['CSA_ID'] == csa_id]['FUND_CODE'].unique()
            eligible_logics = csa_logics[csa_logics['CSA_ID'] == csa_id]
            eligible_logics = {asset_type: eligible_logics[eligible_logics['ASSET_TYPE'] == asset_type] for asset_type in eligible_logics['ASSET_TYPE'].unique()}
            eligible_valuations = csa_valuations[csa_valuations['CSA_ID'] == csa_id]
            
            # Add CP column if not already
            column_name = f'{cp} Haircut Percentage'
            if column_name not in filtered_df.columns:
                filtered_df[column_name] = 0.0

            # Filter dataframe for specific indexes - eligible funds and asset types
            filtered_df = filtered_df[(filtered_df['FUND_CODE'].isin(eligible_funds)) & (filtered_df['BBG_ASSET_TYPE'].isin(eligible_asset_types.values()))]
            filtered_df = filtered_df[~filtered_df['SECURITY_NAME'].str.startswith('.')]
            
            csa_df = filtered_df.iloc[0:0].copy()
            
            for asset_type, logics in eligible_logics.items():
                asset_type_df = filtered_df[filtered_df['BBG_ASSET_TYPE'] == eligible_asset_types[asset_type]]
                
                for _, logic_details in logics.iterrows():
                    asset_type_df = _filter_dataframe_by_logics(asset_type_df, logic_details, csa, custom_functions)
                        
                    if len(asset_type_df) == 0:
                        break
                
                asset_type_valuations = eligible_valuations[eligible_valuations['ASSET_TYPE'] == asset_type]
                asset_type_df = _add_haircut_valuations(asset_type_valuations, asset_type_df, agencies, agency_mappings, column_name)
                asset_type_df = asset_type_df[asset_type_df[column_name] != 0]
                asset_type_df['ASSET_TYPE'] = asset_type
                csa_df = pd.concat([csa_df, asset_type_df])
            
            fw_df = fw_df.merge(csa_df[[column_name]],
                    left_index=True, 
                    right_index=True, 
                    how='left')
            
            fw_df[column_name] = fw_df[column_name].fillna(0)
            
            fw_df.loc[csa_df.index, 'ASSET_TYPE'] = csa_df['ASSET_TYPE']
    
    config.REPORT_FIELDS = config.REPORT_FIELDS + ['ASSET_TYPE']
    
    cp_columns = [f'{cp} Haircut Percentage' for cp in csa_counterparties if f'{cp} Haircut Percentage' in fw_df.columns]
    fw_df['cp_sum'] = fw_df[cp_columns].sum(axis=1)
    fw_df = fw_df[fw_df['cp_sum'] != 0]
    fw_df = fw_df.drop(columns=['cp_sum'])
    
    mv_columns = [col.replace('Percentage', 'MV') for col in cp_columns]
    mv_data = fw_df[cp_columns].mul(fw_df['NET_MV'], axis=0)
    mv_data.columns = mv_columns
    
    for cp_col, mv_col in zip(cp_columns, mv_columns):
        fw_df.insert(fw_df.columns.get_loc(cp_col) + 1, mv_col, mv_data[mv_col])
    
    return fw_df

def _check_asset_types_mapped(eligible_logics, eligible_asset_types):
    for _, row in eligible_logics.iterrows():
        asset_type = row['ASSET_TYPE']
        
        if asset_type not in eligible_asset_types:
            st.error(f'Ineligible asset type: {asset_type}!')
            st.stop()

def _filter_dataframe_by_logics(df, logic_details, csa, custom_functions):
    field = logic_details['FIELD'].upper()
    datatype = logic_details['DATATYPE']
    logic = logic_details['LOGIC']
    value = logic_details['VALUE']
    
    if field in df.columns and df[field].dtype == 'float64':
        value = float(value)
    
    if datatype == 'Custom':
        df = custom_functions[field](logic_details, csa, df)
    elif logic == 'EQUALS':
        df = df[df[field] == value]
    elif logic == 'IN':
        value_list = value.split(';')
        df = df[df[field].isin(value_list)]
    elif logic == 'IN CONTAINS':
        value_list = value.split(';')
        df = df[df[field].str.contains('|'.join(value_list), case=False, na=False)]
    elif logic == 'LESS THAN':
        df = df[df[field] < value]
    elif logic == 'NOT EQUALS':
        df = df[df[field] != value]
    elif logic == 'GREATER THAN':
        df = df[df[field] > value]
    else:
        st.error(f"Logic '{logic}' is not coded!")
        st.stop()
        
    return df

def _add_haircut_valuations(valuation_logic, df, agencies, agency_mappings, cp):
    agency_mapping = agency_mappings['S&P']
    
    for index, row in df.iterrows():
        tenor = row['TIME_UNTIL_MATURITY']
        
        if pd.isna(tenor):
            tenor = 0
        
        if row['SECURITY_NAME'] == 'DTE 2.95 03/01/50':
            pass
                    
        for _, logic in valuation_logic.iterrows():
            tenor_lower = logic['TENOR_LOWER']
            tenor_upper = logic['TENOR_UPPER']
            
            lower_tenor = tenor < tenor_lower
            higher_tenor = tenor > tenor_upper and tenor_upper != -1
            
            if lower_tenor or higher_tenor:
                continue
            
            rating_match = True
            
            for _, column_name in agencies.items():
                #agency_columns = [item for item in list(eligible_valuations.columns) if agencies[agency] in item]
                
                columns = [f'FINAL_{column_name}_RATING', f'FINAL_{column_name}_ISSUER_RATING']
                
                rating_lower = logic[f'{column_name}_LOWER']
                rating_upper = logic[f'{column_name}_UPPER']
                
                if rating_lower == '' or rating_upper == '':
                    continue
                
                rating_lower = int(rating_lower)
                rating_upper = int(rating_upper)

                for column in columns:
                    value = row[column]
                    
                    if value == None or value == 'None':
                        continue
                    
                    rating_index = agency_mapping[value]

                    if rating_index > rating_lower:
                        rating_match = False

                    break
            
            if not rating_match:
                continue

            df.loc[index, cp] = logic['PERCENTAGE']
            break
        
    return df

def get_csa_data(config):
    config.CSA_FUNDS_MAPPED = _get_csa_funds_mapped()
    config.CSA_DETAILS = _get_csa_details()
    config.CSA_LOGICS = _get_csa_logics()
    config.CSA_VALUATIONS = _get_csa_valuations()
    
    return config

@st.cache_data(show_spinner=False)
def _get_csa_funds_mapped():
    sql = """
        SELECT 
            csa_id, 
            code, 
            fund_code 
        FROM 
            collateral.csa_fund_details d, 
            collateral.csa_fund_groups g, 
            collateral.csa_fund_mapping m 
        WHERE 
            d.fund_group_id = g.id 
            AND m.fund_group_id = g.id;
    """
    csa_funds_mapped = ss.snowflake.query(sql)
    
    return csa_funds_mapped

@st.cache_data(show_spinner=False)
def _get_csa_details():
    sql = """
        WITH max_dates AS (
            SELECT 
                entity_id, 
                cp_id, 
                MAX(effective_date) AS max_effective_date 
            FROM 
                collateral.csas 
            GROUP BY 
                entity_id, 
                cp_id
        )
        SELECT 
            c.id, 
            f.code, 
            base_currency, 
            eligible_currency, 
            fx_haircut, 
            cp.name
        FROM 
            collateral.csas c, 
            collateral.cp_entities cp, 
            max_dates m, 
            collateral.fwd_entities f 
        WHERE 
            cp.id = c.cp_id 
            AND m.entity_id = c.entity_id 
            AND m.cp_id = c.cp_id 
            AND c.effective_date = max_effective_date 
            AND c.entity_id = f.id;
    """
    csa_details = ss.snowflake.query(sql)
    
    return csa_details

@st.cache_data(show_spinner=False)
def _get_csa_logics():
    sql = """
        SELECT 
            csa_id, 
            asset_type, 
            field, 
            datatype, 
            logic, 
            value 
        FROM 
            collateral.collateral_logic;
    """
    csa_logics = ss.snowflake.query(sql)
    
    return csa_logics

@st.cache_data(show_spinner=False)
def _get_csa_valuations():
    sql = """
        SELECT 
            csa_id, 
            asset_type, 
            sp_lower, 
            sp_upper, 
            moodys_lower, 
            moodys_upper, 
            fitch_lower, 
            fitch_upper, 
            tenor_lower, 
            tenor_upper, 
            percentage 
        FROM 
            collateral.valuation_percentages;
    """
    csa_valuations = ss.snowflake.query(sql)
    
    return csa_valuations

@st.cache_data(show_spinner=False)
def get_ratings_mapping(agencies):
    sql = """
        SELECT 
            rating, 
            index 
        FROM 
            supp.ratings_ladder;
    """
    rating_ladder_df = ss.snowflake.query(sql)

    rating_ladder = dict(zip(rating_ladder_df['RATING'], rating_ladder_df['INDEX']))
    
    sql = """
        SELECT 
            agency, 
            rating, 
            equivalent_rating 
        FROM 
            supp.ratings_mapping;
    """
    rating_mapping_df = ss.snowflake.query(sql)
    
    agency_mappings = {}
    
    for agency in rating_mapping_df['AGENCY'].unique():
        if agency not in agencies:
            continue
        
        agency_df = rating_mapping_df[(rating_mapping_df['AGENCY'] == agency)].reset_index(drop=True)
        
        stop_index = agency_df[agency_df['EQUIVALENT_RATING'] == 'Default'].index[0] + 1
        agency_mapping_df = agency_df.iloc[:stop_index]
        agency_mapping = dict(zip(agency_mapping_df['RATING'], agency_mapping_df['EQUIVALENT_RATING'].map(rating_ladder)))
        agency_mappings[agency] = agency_mapping
    
    return agency_mappings

@st.cache_data(show_spinner=False)
def get_funnelweb_data(date, config):
    '''
    Fetches the funnelweb data based on the fields specified by the collateral logic
    '''
    logic_df = config.CSA_LOGICS
    unique_fields = list(logic_df[logic_df['DATATYPE'] != 'Custom']['FIELD'].unique())
    ratings_fields = [f"FINAL_{agency}_RATING, FINAL_{agency}_ISSUER_RATING" for agency in config.AGENCIES.values()]
    
    sql = f"""
        SELECT 
            {', '.join(config.REPORT_FIELDS)}, 
            {', '.join(config.EXTRA_FIELDS)}, 
            {', '.join(unique_fields)}, 
            {', '.join(ratings_fields)}
        FROM 
            funnelweb 
        WHERE 
            closing_date = '{date.strftime('%Y-%m-%d')}' 
            AND lbu_group = 'HK';
    """
    df = ss.snowflake.query(sql)

    return df