import streamlit as st
from tools.filter.filter_data import get_lbu_data, get_date_data, get_currency_data
import streamlit_antd_components as sac
from datetime import datetime, timedelta
from streamlit_js_eval import streamlit_js_eval
import time
from streamlit_tree_select import tree_select

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

    if "lbu_default" in st.session_state:
        indexes = st.session_state["lbu_default"]
    
    st.write('LBU Group / LBU / Fund Type / Fund')
    col1, col2 = st.columns([0.8, 0.2])

    with col1:
        selected_indexes = st.session_state[f"lbu_default"] = sac.cascader(items=items, multiple=True, search=True, clear=True, strict=True, return_index=True, index=indexes)
    with col2:
        if st.button("Select all", f"Select All LBU", use_container_width=True):
            st.session_state["lbu_default"] = [[item.value] for item in items]
            st.rerun()
    
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

def build_lbu_tree(hk_entities = False):
    get_lbu_data()
    
    values = []
    entities = {}

    for group in st.session_state["lbus"]:
        childrenLbus = []

        if not hk_entities:
            lbus = group.lbus
        elif group.lbu_group_code == 'HK':
            lbus = group.entities
        else:
            continue

        for lbu in lbus:
            childrenFundTypes = []

            if hk_entities and lbu not in entities:
                entities[lbu.lbu_code] = []

            for fund_type in lbu.fundTypes:
                childrenFunds = []
                for fund in fund_type.funds:
                    if hk_entities:
                        entities[lbu.lbu_code].append(fund.fund_code)
                    
                    childrenFunds.append({"label": fund.fund_code, "value": f"fund_code:{fund.fund_code}"})
                childrenFundTypes.append({"label": fund.fund_type, "value": f"fund_type:{lbu.lbu_code}-{fund.fund_type}", "children": childrenFunds})
            childrenLbus.append({"label": lbu.lbu_name, "value": f"lbu_code:{lbu.lbu_code}", "children": childrenFundTypes})
        values.append({"label": group.lbu_group_name, "value": f"lbu_group:{group.lbu_group_code}", "children": childrenLbus})
    
    all = []
    all.append({"label": "Select All", "value": "all", "children": values})

    expanded = []
    
    if hk_entities:
        expanded.extend([entity['value'] for entity in all[0]['children']])
        expanded.append("all")
        st.session_state['hk_entities'] = entities

    selected_values = build_tree_selectors({"lbu_tree": {"title": "LBUs", "data": all, "expanded": expanded}})

    st.session_state['lbu_tree_data'] = [value.replace('fund_code:', '') for value in selected_values['lbu_tree']['checked'] if 'fund_code:' in value]

def build_date_filter(current_date_only = False):
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

    if (current_date_only):
        create_date_filter('Valuation Date', st.session_state["max_date"])
        return

    date_cols = st.columns(2)

    with date_cols[0]:
        create_date_filter('Valuation Date', st.session_state["max_date"])
    with date_cols[1]:
        create_date_filter('Comparison Date', st.session_state["default_compare_date"])

def build_currency_filter():
    get_currency_data()

    df = st.session_state["fxs_df"]

    current_fx = st.session_state['fxs_current'] = df[(df['VALUATION_DATE'] == st.session_state['Valuation Date'])]
    compare_fx = st.session_state['fxs_compare'] = df[(df['VALUATION_DATE'] == st.session_state['Comparison Date'])]

    st.session_state['currencies'] = list(set(current_fx['FX'].unique()) & set(compare_fx['FX'].unique()))

    currencies = []
    for currency in st.session_state['currencies']:
        currencies.append(sac.CasItem(currency))

    st.write('Currency')
    currency = sac.cascader(currencies, search=True, strict=True, index=next((i for i, obj in enumerate(currencies) if obj.label == 'USD'), None))

    if type(currency) == list:
        currency = currency[0]

    st.session_state['Currency'] = currency

    st.session_state['fx_rate_current'] = current_fx[current_fx['FX'] == currency]["RATE"].iloc[0]
    st.session_state['fx_rate_compare'] = compare_fx[compare_fx['FX'] == currency]["RATE"].iloc[0]

def build_level_filter():
    if 'level' not in st.session_state:
        st.session_state['level'] = 2

    st.write("Level")
    st.session_state['level'] = int(sac.buttons([sac.ButtonsItem(label='1'), sac.ButtonsItem(label='2'), sac.ButtonsItem(label='3'), sac.ButtonsItem(label='4')], index=1))

def build_tree_selectors(data, height=200):
    cols = st.columns(len(data))
    keys = list(data.keys())
    selected_values = {}

    for i in range (0, len(cols)):
        key = keys[i]
        parameters = data[key]
        title = parameters["title"]
        
        if "data" not in parameters:
            items = parameters["values"]
            checked = parameters["checked"]
            display_names = parameters["column_label_dict"]
            data = [{"label": display_names[item], "value": item} for item in items]
        else:
            data = parameters["data"]
            values = lambda d: [d['value']] + sum([values(c) for c in d.get('children', [])], [])
            checked = sum([values(item) for item in data], [])

            if "expanded" != []:
                expanded = parameters["expanded"]
            elif 'all' in checked:
                expanded = ['all']
            else:
                expanded = []

        with cols[i]:
            with st.container(border=True):
                st.write(title)
                with st.container(height=height):
                    
                    if type(checked) == dict:
                        expanded = checked["expanded"]
                        checked = checked["checked"]

                    selected = tree_select(data, check_model='leaf', key=key, checked=checked, expanded=expanded)
                    selected_values[key] = selected
    
    return selected_values