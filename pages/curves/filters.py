import streamlit as st
from streamlit import session_state as ss
import pandas as pd
from .data import get_curves
from interface.filters import build_date_filter

def build_filters():
    with st.expander('Filters', True):
        build_curve_filters()
        
def build_curve_filters():
    df = get_curves()
    
    unique_fx = df['FX'].unique().tolist()
    selected_fx = st.selectbox('Currency', unique_fx, key='selected_currency', index=unique_fx.index('USD'))
    
    curves = df[df['FX'] == selected_fx]['CURVE'].unique().tolist()
    
    govt_index = next((i for i, curve in enumerate(curves) if '_govt' in curve), 0)
    selected_curve = st.selectbox('Curve', curves, key='selected_curve', index=govt_index)
    
    dates = df[(df['FX'] == selected_fx) & (df['CURVE'] == selected_curve)]['VALUATION_DATE'].unique().tolist()
    selected_date = build_date_filter('Valuation Date', dates, key='selected_date', default=max(dates))
    
    df['VALUATION_DATE'] = pd.to_datetime(df['VALUATION_DATE']).dt.date
        
    if 'selected_curves' not in st.session_state:
        st.session_state['selected_curves'] = {}
    if 'selected_curve_forward' not in st.session_state:
        st.session_state['selected_curve_forward'] = None
    
    selection = st.segmented_control(
        options=['Spot', 'Forward'],
        key='selected_mode',
        label='Mode',
        selection_mode='single',
        default='Spot'
    )
    
    if selection == 'Spot' and st.button('Add'):        
        key = f'{selected_curve} {selected_date}'
        
        if key not in st.session_state['selected_curves'].keys():
            curve_df = ss['curve_data'] = df[(df['FX'] == selected_fx) & (df['CURVE'] == selected_curve) & (df['VALUATION_DATE'] == ss['selected_date'])].copy()
            curve_df = curve_df[['CURVE', 'VALUATION_DATE', 'TENOR', 'RATE']].reset_index(drop=True)
            st.session_state['selected_curves'][key] = curve_df
    elif selection == 'Forward' and st.button('Select'):
        curve_df = df[(df['FX'] == selected_fx) & (df['CURVE'] == selected_curve) & (df['VALUATION_DATE'] == ss['selected_date'])].copy()
        curve_df = curve_df[['CURVE', 'VALUATION_DATE', 'TENOR', 'RATE']].reset_index(drop=True)
        ss.selected_curve_forward = curve_df