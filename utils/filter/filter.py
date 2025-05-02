import streamlit as st
from classes.fx import build_currencies
from classes.curve import build_curves
from classes.lbu import build_lbu
from datetime import datetime
from streamlit import session_state as ss
from utils.date import get_ytd, get_qtd, get_mtd, get_one_week
from utils.filter.tree import build_tree_selectors

def build_fx_filter(key_suffix=''):
    if 'currencies' not in ss:
        ss['currencies'] = build_currencies()
    
    currencies = ss['currencies']
    currency_names = [currency.name for currency in currencies]
    
    key = 'selected_currency' + key_suffix

    st.selectbox('Currency', currency_names, index=currency_names.index('USD'), key=key)

    return currencies[currency_names.index(ss[key])]

def build_curve_filter(key_suffix=''):
    if "curves" not in ss:
        ss["curves"] = build_curves()
    
    curves = ss["curves"]
    curve_names = [curve.name for curve in curves]
    fx_curve_names = [curve.name for curve in curves if curve.fx == ss['selected_currency' + key_suffix]]
    
    key = 'selected_curve' + key_suffix

    st.selectbox('Curves', fx_curve_names, index=next((i for i, s in enumerate(fx_curve_names) if '_govt' in s), None), key=key)

    curve = curves[curve_names.index(ss[key])]
    dates = curve.rates['VALUATION_DATE'].unique()
    build_date_filter('Date', dates, max(dates), key='selected_date' + key_suffix)

    return curve

def build_lbu_filter(entities=False, height=300):
    if "lbus" not in ss:
        ss['lbus'] = build_lbu()

    lbus = ss['lbus']
    
    data = [{'label': 'Select All', 'value': 'all'}]

    children = []
    entity_mapping = {}

    for lbu_group in lbus:
        if entities and lbu_group.code != 'HK':
            continue

        children.append(lbu_group.build_tree_data(entities))
        entity_mapping.update(lbu_group.build_entity_mapping())

    data[0]['children'] = children

    checked = ['all']
    funds = []

    for lbu_group in children:
        checked.append(lbu_group['value'])
        for lbu in lbu_group['children']:
            checked.append(lbu['value'])
            for type in lbu['children']:
                checked.append(type['value'])
                for fund in type['children']:
                    checked.append(fund['value'])
                    funds.append(fund['value'].replace('f:', ''))

    expanded = ['all']

    if entities:
        expanded.append('lg:HK')

    build_tree_selectors('LBUs', data, 'selected_lbus', checked, expanded, height=height)

    if ss['selected_lbus'] == None:
        ss['selected_funds'] = funds
    else:
        ss['selected_funds'] = [item.replace('f:', '') for item in ss['selected_lbus']['checked'] if 'f:' in item]

    ss['entity_mapping'] = entity_mapping

def build_fund_filter():
    if "lbus" not in ss:
        ss['lbus'] = build_lbu()

    lbu_groups = ss['lbus']
    
    lbu_names = sorted([lbu.name for lbu_group in lbu_groups for lbu in lbu_group.lbus])
    
    st.selectbox('LBU', lbu_names, index=lbu_names.index('Hong Kong'), key='selected_lbu')
    
    fund_names = sorted([fund.name for lbu_group in lbu_groups for lbu in lbu_group.lbus if lbu.name == ss['selected_lbu'] for fund in lbu.funds])
    
    st.selectbox('Fund', fund_names, key='selected_fund')

def build_date_filter(label: str, dates: list[datetime], default:datetime = None, key: str = 'selected_date', on_change = None):
    #if default == None:
     #   default = max(dates)
    
    st.date_input(label, default, min(dates), max(dates), key, on_change=on_change)

def build_date_filter_buttons(label: str, dates: list[datetime], default: datetime = None, key: str = 'selected_date', date: datetime = None, pill_dates: list[datetime] = None):
    if date == None:
        date = datetime.now().date()
        pill_dates = {'Today': max(dates).date(), 'YTD': get_ytd(date, dates), 'QTD': get_qtd(date, dates), 'MTD': get_mtd(date, dates)}
        
        if default == None:
            default = 'Today'
    
    if pill_dates == None and default == None:
        pill_dates = {'YTD': get_ytd(date, dates), 'QTD': get_qtd(date, dates), 'MTD': get_mtd(date, dates), '1W': get_one_week(date, dates)}
        default = 'YTD'
    
    if key + '_pill_state' not in ss:
        ss[key + '_pill_state'] = default
        ss[key + '_state'] = False

    if default == '':
        build_date_filter(label, dates, default=None, key=key)
        return

    if ss[key + '_state'] and key + '_override' in ss:
        ss[key] = pill_dates[ss[key + '_override']]
        
    def reset_pills():
        ss[key + '_pill_state'] = None
        ss[key + '_state'] = False

    build_date_filter(label, dates, pill_dates[default], key, reset_pills)
    selected_date = ss[key]

    if selected_date in pill_dates.values():
        state = next((k for k, v in pill_dates.items() if v == selected_date), None)
        
        if key + '_override' in ss and ss[key + '_override'] != None and pill_dates[state] == pill_dates[ss[key + '_override']]:
            state = ss[key + '_override']
            
        ss[key + '_override'] = ss[key + '_pill_state'] = state
    else:
        ss[key + '_override'] = None

    def override_date():
        ss[key + '_state'] = True

    st.pills('Pills', pill_dates.keys(), label_visibility='collapsed', default=default, key=key + '_override', on_change=override_date)
    
    ss[key + '_string'] = selected_date.strftime('%Y-%m-%d')

def build_level_filter():
    st.pills('Levels', ['1', '2', '3', '4'], selection_mode='single', default='2', key='selected_level')
    
def build_multi_select_filter(label, mapping, key, default, disabled=False):
    selected = st.multiselect(label, mapping.keys(), key=key, default=default, disabled=disabled)
    ss[f'{key}_converted'] = [mapping[column] for column in selected]
    
    return selected