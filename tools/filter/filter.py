import streamlit as st
from tools.filter.filter_data import get_lbu_data, get_date_data, get_currency_data
import streamlit_antd_components as sac
from datetime import datetime, timedelta

def build_lbu_filter():
    get_lbu_data()
    
    indexes = []
    index_classes = {}
    i = 0

    for group in st.session_state["lbus"]:
        indexes.append([i])
        index_classes[i] = group
        i += 1
        for lbu in group.lbus:
            index_classes[i] = lbu
            i += 1
            for fund_type in lbu.fundTypes:
                index_classes[i] = fund_type
                i += 1
                for fund in fund_type.funds:
                    index_classes[i] = fund
                    i += 1
                fund_type.build_cas_item()
            lbu.build_cas_item()
        group.build_cas_item()

    items = [group.casItem for group in st.session_state["lbus"]]
    
    st.write('LBU Group / LBU / Fund Type / Fund')
    selected_indexes = sac.cascader(items=items, multiple=True, search=True, clear=True, strict=True, return_index=True, index=indexes)
    
    if selected_indexes == []:
        selected_indexes = indexes

    selected_classes = [index_classes[index[0]] if type(index) == list else index_classes[index] for index in selected_indexes]        

    remove_selection = []
    for selection in selected_classes:
        exists = selection.lower_level_exists(selected_classes)

        if exists:
            remove_selection.append(selection)

    for selection in remove_selection:
        selected_classes.remove(selection)

    st.session_state['LBU Group / LBU / Fund Type / Fund'] = selected_classes

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
            st.date_input(label, default_date, st.session_state["min_date"], st.session_state["max_date"], on_change=check_weekday, key=label)
        else:
            st.date_input(label, default_date, st.session_state["min_date"], st.session_state["max_date"], on_change=check_weekday_comparison, key=label)

    date_cols = st.columns(2)

    with date_cols[0]:
        create_date_filter('Valuation Date', st.session_state["max_date"])
    with date_cols[1]:
        create_date_filter('Comparison Date', st.session_state["default_compare_date"])

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