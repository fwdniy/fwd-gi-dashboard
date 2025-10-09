import streamlit as st
from datetime import datetime
from utils.dates_extended import *
from utils.initializer import initialize_variables
from streamlit import session_state as ss

def build_date_filter(label: str, dates: list[datetime], default: datetime = None, key: str = 'selected_date', on_change = None):
    """
    Builds a basic date filter using Streamlit's built-in date_input given a list of dates and the default date.
    """
    date = st.date_input(label, default, min(dates), max(dates), key, on_change=on_change, args=[key], format='YYYY/MM/DD')
    
    return date

def build_date_filter_pills(label: str, dates: list[datetime], default: datetime = None, key: str = 'selected_date', comparison_date: datetime = None, pill_dates: list[datetime] = None):
    """
    Builds a date filter with pills for quick selection of common date ranges.
    """
    #if ss.reset_variables and f'{key}_override' in ss:
    #   ss.pop(f'{key}_override')
    
    if comparison_date == None:
        pill_dates, default = _build_valuation_pill_dates(dates, default)        
    else:
        pill_dates, default = _build_comparison_pill_dates(comparison_date, dates)
    
    _initialize_pill_dates(key, default)
    
    if default == '':
        st.write('')
        
    _override_date(key, pill_dates)
    
    build_date_filter(label, dates, pill_dates[default], key, _reset_pills)
    
    _set_pill_date(key, pill_dates)
    
    _build_pills(pill_dates, default, key)
    
def _build_valuation_pill_dates(dates, default):
    date = datetime.now().date()
    pill_dates = {'Today': max(dates).date(), 'YTD': get_ytd(date, dates), 'QTD': get_qtd(date, dates), 'MTD': get_mtd(date, dates)}
    
    if default == None:
        default = 'Today'
    
    return pill_dates, default

def _build_comparison_pill_dates(date, dates):
    pill_dates = {'YTD': get_ytd(date, dates), 'QTD': get_qtd(date, dates), 'MTD': get_mtd(date, dates), '1W': get_one_week(date, dates)}
    default = 'YTD'
    
    return pill_dates, default
    
def _initialize_pill_dates(key, default):
    initialize_pill = {
       f'{key}_pill_state': default,
       f'{key}_pill_selected': False
    }
    
    initialize_variables(initialize_pill)
    
def _reset_pills(key):
    ss[f'{key}_pill_state'] = None
    ss[f'{key}_pill_selected'] = False
    ss[f'{key}_pill_selection'] = None
    
def _set_pill_date(key, pill_dates):
    selected_date = ss[key]

    if selected_date in pill_dates.values():
        state = next((k for k, v in pill_dates.items() if v == selected_date), None)
        
        if f'{key}_override' in ss and ss[f'{key}_override'] != None and pill_dates[state] == pill_dates[ss[f'{key}_override']]:
            state = ss[f'{key}_override']
            
        ss[f'{key}_override'] = ss[f'{key}_pill_state'] = state
    else:
        ss[f'{key}_override'] = None
        
    ss[f'{key}_string'] = selected_date.strftime('%Y-%m-%d')

def _override_date(key, pill_dates):
    if ss[f'{key}_pill_selected'] and f'{key}_pill_selection' in ss:
        override_date = ss[f'{key}_pill_selection']
        if override_date == None:
            override_date = ss[f'{key}_previous_pill_selection']
        
        ss[key] = pill_dates[override_date]

def _enable_date_override(key):
    ss[f'{key}_pill_selected'] = True

def _build_pills(pill_dates, default, key):    
    st.pills('Date Pills', pill_dates.keys(), label_visibility='collapsed', default=default, key=f'{key}_pill_selection', on_change=_enable_date_override, args=[key])
    
    pill_selection = ss[f'{key}_pill_selection']
    
    if pill_selection != None:
        ss[f'{key}_previous_pill_selection'] = pill_selection