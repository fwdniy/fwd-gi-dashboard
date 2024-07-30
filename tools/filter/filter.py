import streamlit as st
from tools.filter.filter_data import get_lbu_data, get_date_data, get_currency_data
import streamlit_antd_components as sac
from datetime import datetime, timedelta

def build_lbu_filter():
    get_lbu_data()
    
    for group in st.session_state["lbus"]:
        for lbu in group.lbus:
            for type in lbu.fundTypes:
                type.build_cas_item()
            lbu.build_cas_item()
        group.build_cas_item()

    items = [group.casItem for group in st.session_state["lbus"]]
    
    indexes = []

    i = 0
    for group in items:
        indexes.append([i])
        i += 1
        for lbu in group.children:
            i += 1
            for type in lbu.children:
                i += 1 + len(type.children)

    st.write('LBU Group / LBU / Fund Type / Fund')
    st.session_state['LBU Group / LBU / Fund Type / Fund'] = sac.cascader(items=items, multiple=True, search=True, clear=True, strict=True, return_index=True, index=indexes)

def build_date_filter():
    get_date_data()
    
    def create_date_filter(label, default_date, comparison_date = False):
        def check_weekday_comparison():
            check_weekday(True)

        def check_weekday(comparison_date = False):
            if not comparison_date:
                selected_date = st.session_state['Valuation Date']
            else:
                selected_date = st.session_state['Comparison Date']
            day_of_week = selected_date.strftime("%A")
            if day_of_week in ['Saturday', 'Sunday']:
                st.toast("Weekend selected, changing to first previous week day.", icon="⚠️")

                if day_of_week == 'Saturday':
                    adjuster = 1
                else:
                    adjuster = 2

                if not comparison_date:
                    st.session_state['Valuation Date'] = selected_date - timedelta(days=adjuster)
                else:
                    st.session_state['Comparison Date'] = selected_date - timedelta(days=adjuster)

        if not comparison_date:
            return st.date_input(label, default_date, st.session_state["min_date"], st.session_state["max_date"], on_change=check_weekday, key=label)
        else:
            return st.date_input(label, default_date, st.session_state["min_date"], st.session_state["max_date"], on_change=check_weekday_comparison, key=label)

    date_cols = st.columns(2)

    with date_cols[0]:
        datetime.combine(create_date_filter('Valuation Date', st.session_state["max_date"]), datetime.min.time())
    with date_cols[1]:
        datetime.combine(create_date_filter('Comparison Date', st.session_state["default_compare_date"]), datetime.min.time())

def build_currency_filter():
    get_currency_data()

    currencies = []
    for currency in st.session_state['currencies']:
        currencies.append(sac.CasItem(currency))

    st.write('Currency')
    st.session_state['Currency'] = sac.cascader(currencies, search=True, strict=True, index=next((i for i, obj in enumerate(currencies) if obj.label == 'USD'), None))

def build_level_filter():
    if 'level' not in st.session_state:
        st.session_state['level'] = 2

    st.write("Level")
    st.session_state['level'] = int(sac.buttons([sac.ButtonsItem(label='1'), sac.ButtonsItem(label='2'), sac.ButtonsItem(label='3'), sac.ButtonsItem(label='4')], index=1))