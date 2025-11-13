import streamlit as st
from streamlit import session_state as ss
import pandas as pd
from db.data.data_shipment import get_lbu_data, get_funnelweb_dates, get_funnelweb_data
from db.data.ratings import get_ratings_index, get_ratings_mapping
from auth import get_user_permissions
from pages.collateral.ratings import convert_csa_valuation_ratings
from pages.collateral.data import _add_haircut_valuations

def get_data(config):
    config.CATEGORY = _get_generic_data('category')
    config.SUBCATEGORY = _get_generic_data('subcategory', ['category_id'])
    config.TENOR = _get_generic_data('tenor', ['days'])
    config.UNIT = _get_generic_data('unit')
    config.INDEX = _get_generic_data('index', ['currency', 'ticker', 'reporting_basis'])
    config.METRICS = _get_metrics_data()
    config.METRIC_VALUES = _get_metric_values_data()
    config.LBU = get_lbu_data()
    config.RATINGS = get_ratings_index()
    config.USERS = get_user_permissions()

def map_data(config):
    lbu_df = config.LBU
    lbu_dict = dict(zip(lbu_df['ID'], lbu_df['GROUP_NAME']))
    
    category_df = config.CATEGORY
    category_dict = dict(zip(category_df['ID'], category_df['NAME']))
    
    subcategory_df = config.SUBCATEGORY
    subcategory_df['CATEGORY'] = subcategory_df['CATEGORY_ID'].map(category_dict)
    
    subcategory_dict = dict(zip(subcategory_df['ID'], subcategory_df['NAME']))
    category_dict = dict(zip(subcategory_df['ID'], subcategory_df['CATEGORY']))
    
    tenor_df = config.TENOR
    tenor_dict = dict(zip(tenor_df['ID'], tenor_df['DAYS']))
    tenor_name_dict = dict(zip(tenor_df['ID'], tenor_df['NAME']))
    
    unit_df = config.UNIT
    unit_dict = dict(zip(unit_df['ID'], unit_df['NAME']))
    
    user_df = config.USERS
    user_dict = dict(zip(user_df['ID'], user_df['EMAIL']))
    
    index_df = config.INDEX
    index_dict = dict(zip(index_df['ID'], index_df['NAME']))
    index_currency_dict = dict(zip(index_df['ID'], index_df['CURRENCY']))
    index_ticker_dict = dict(zip(index_df['ID'], index_df['TICKER']))
    index_reporting_basis_dict = dict(zip(index_df['ID'], index_df['REPORTING_BASIS']))
    
    metrics_df = config.METRICS
    
    metrics_df['LBU_GROUP'] = metrics_df['LBU_ID'].map(lbu_dict)
    metrics_df['CATEGORY'] = metrics_df['SUBCATEGORY_ID'].map(category_dict)
    metrics_df['SUBCATEGORY'] = metrics_df['SUBCATEGORY_ID'].map(subcategory_dict)
    metrics_df['TENOR_DAYS'] = metrics_df['TENOR_ID'].map(tenor_dict)
    metrics_df['TENOR'] = metrics_df['TENOR_ID'].map(tenor_name_dict)
    metrics_df['UNIT'] = metrics_df['UNIT_ID'].map(unit_dict)
    metrics_df['INDEX'] = metrics_df['INDEX_ID'].map(index_dict)
    metrics_df['INDEX_CURRENCY'] = metrics_df['INDEX_ID'].map(index_currency_dict)
    metrics_df['INDEX_TICKER'] = metrics_df['INDEX_ID'].map(index_ticker_dict)
    metrics_df['INDEX_REPORTING_BASIS'] = metrics_df['INDEX_ID'].map(index_reporting_basis_dict)
    
    metric_values = config.METRIC_VALUES
    metric_values = metric_values[metric_values['MAIN_ID'] != -1]
    metric_values = metric_values.merge(metrics_df, left_on='MAIN_ID', right_on='ID', how='left', suffixes=('', '_METRICS'))
    
    metric_values['PROJECTED_DATE'] = metric_values.apply(
        lambda row: 'Spot' 
        if row['PROJECTED_DATE'] == row['VALUATION_DATE'] 
        else row['PROJECTED_DATE'].strftime('%Y'), axis=1
    )
    
    metric_values['USER'] = metric_values['USER_ID'].map(user_dict)
    
    config.SUBCATEGORY = subcategory_df
    config.METRICS = metrics_df
    config.METRIC_VALUES = metric_values
    
    return config
    

@st.cache_data(ttl=3600, show_spinner=False)
def _get_generic_data(table_name, additional_columns=[]):
    columns = ', '.join(additional_columns) if additional_columns else ''
    
    sql = f"""
        SELECT 
            id,
            name,
            {columns}
        FROM 
            assumptions.{table_name};
    """
    df = ss.snowflake.query(sql)
    
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def _get_metrics_data():
    sql = """
        SELECT 
            id,
            lbu_id,
            subcategory_id,
            tenor_id,
            rating_id,
            index_id,
            unit_id
        FROM 
            assumptions.metrics;
    """
    df = ss.snowflake.query(sql)
    
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def _get_metric_values_data():
    sql = """
        SELECT 
            id,
            main_id,
            valuation_date,
            projected_date,
            value,
            data_source,
            user_id,
            timestamp,
            endorse_user_id,
            endorse_timestamp,
            disabled
        FROM 
            assumptions.metric_values;
    """
    df = ss.snowflake.query(sql)
    
    return df