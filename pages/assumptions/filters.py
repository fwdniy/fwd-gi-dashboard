import streamlit as st
from streamlit import session_state as ss
from interface.filters import build_multi_select_filter
import pandas as pd

def build_filters(config):
    with st.expander('Filters', True):
        metrics_df = config.METRIC_VALUES

        metrics_df = _filter_by_lbu(metrics_df)
        metrics_df = _filter_by_category(metrics_df)
        metrics_df = _filter_by_subcategory(metrics_df)
        metrics_df = _filter_by_reporting_basis(metrics_df)
        metrics_df = _filter_by_tenor(metrics_df)
        metrics_df = _filter_by_valuation_date(metrics_df)
        metrics_df = _filter_by_projected_date(metrics_df)

        config.METRIC_VALUES = metrics_df

    return config

def _filter_by_lbu(metrics_df):
    lbus = metrics_df['LBU_GROUP'].sort_values().unique().tolist()
    lbu_dict = {item: item for item in lbus}
    selected_lbu = build_multi_select_filter('LBU', lbu_dict, 'filter_lbu', lbus)
    return metrics_df[metrics_df['LBU_GROUP'].isin(selected_lbu[0])]

def _filter_by_category(metrics_df):
    categories = metrics_df['CATEGORY'].sort_values().unique().tolist()
    category_dict = {item: item for item in categories}
    selected_categories = build_multi_select_filter(
        'Category', category_dict, 'filter_category', categories[0], max_selections=1
    )
    return metrics_df[metrics_df['CATEGORY'].isin(selected_categories[0])]

def _filter_by_subcategory(metrics_df):
    subcategories = metrics_df['SUBCATEGORY'].sort_values().unique().tolist()
    subcategory_dict = {item: item for item in subcategories}
    selected_subcategories = build_multi_select_filter('Subcategory', subcategory_dict, 'filter_subcategory', subcategories)
    return metrics_df[metrics_df['SUBCATEGORY'].isin(selected_subcategories[0])]

def _filter_by_reporting_basis(metrics_df):
    basis = list(
        set(
            basis_item.strip()
            for basis_str in metrics_df['INDEX_REPORTING_BASIS'].dropna()
            for basis_item in basis_str.split(', ')
        )
    )
    basis_dict = {item: item for item in basis}
    selected_basis = build_multi_select_filter('Reporting Basis', basis_dict, 'filter_reporting_basis', 'EV')
    return metrics_df[
        metrics_df['INDEX_REPORTING_BASIS'].apply(
            lambda x: any(b in x for b in selected_basis[0]) if pd.notna(x) else False
        )
    ]

def _filter_by_tenor(metrics_df):
    tenors = metrics_df['TENOR'].sort_values().unique().tolist()
    tenor_dict = {item: item for item in tenors}
    selected_tenor = build_multi_select_filter('Tenor', tenor_dict, 'filter_tenor', tenors)
    return metrics_df[metrics_df['TENOR'].isin(selected_tenor[0])]

def _filter_by_valuation_date(metrics_df):
    valuation_dates = metrics_df['VALUATION_DATE'].sort_values().dt.strftime('%Y-%m-%d').unique().tolist()
    valuation_date_dict = {item: item for item in valuation_dates}
    selected_valuation_dates = build_multi_select_filter(
        'Valuation Date',
        valuation_date_dict,
        'filter_valuation_date',
        max(metrics_df['VALUATION_DATE']).strftime('%Y-%m-%d'),
        max_selections=1
    )
    return metrics_df[
        metrics_df['VALUATION_DATE'].dt.strftime('%Y-%m-%d').isin(selected_valuation_dates[0])
    ]

def _filter_by_projected_date(metrics_df):
    projected_dates = sorted(
        metrics_df['PROJECTED_DATE'].unique(),
        key=lambda x: (x != 'Spot', int(x) if x.isdigit() else float('inf'))
    )
    projected_date_dict = {item: item for item in projected_dates}
    selected_projected_dates = build_multi_select_filter('Projected Date', projected_date_dict, 'filter_projected_date', projected_dates)
    return metrics_df[metrics_df['PROJECTED_DATE'].isin(selected_projected_dates[0])]