import streamlit as st
from utils.interface.menu import menu
from utils.filter.filter import build_fx_filter, build_curve_filter
from datetime import datetime
import plotly.graph_objects as go
import pandas as pd
from utils.interface.download import create_download_button
from streamlit import session_state as ss
from utils.interface.grid import AgGridBuilder
from objects.curve import convert_floats_to_tenor

menu('Curves')

#region Initialization

if 'selected_curves' not in ss:
    ss['selected_curves'] = {}
    ss['selected_curves2'] = {}
    ss['remove_curve'] = None

#endregion

spot, forward = st.tabs(['Spot', 'Forward'])

def build_filter(add=True):
    suffix = ''

    if not add:
        suffix = '2'
    
    with st.expander('Filters', True):
        with st.spinner('Fetching currency data...'):
            build_fx_filter(suffix)

        with st.spinner('Fetching curve data...'):
            curve = build_curve_filter(suffix)
        
        button_label = 'Add'

        if not add:
            button_label = 'Select'

        if st.button(button_label):
            if not add:
                ss['selected_curves' + suffix] = {}
            
            date = ss['selected_date']
            rates = curve.get_rates(date, True)

            if rates == {}:
                st.error(f'No data found for {curve.name} on {date}!')
            else:
                curve_name = f'{curve.name} {date.strftime('%Y/%m/%d')}'
                ss['selected_curves' + suffix][curve_name] = rates
            
with spot:            
    build_filter()

    selected_curves: dict[str, dict[str: float]] = ss['selected_curves']
    remove_curve: str = ss['remove_curve']

    def build_graph():
        #region Checks

        if remove_curve != None:
            selected_curves.pop(remove_curve)
            ss['remove_curve'] = None

        if len(selected_curves) == 0:
            st.info('Add curves to visualize or download!')
            return

        #endregion

        #region Plot and Build DataFrame

        fig = go.Figure()
        df = pd.DataFrame(columns=['CURVE', 'VALUATION_DATE', 'TENOR', 'RATE'])

        for name, rates_dict in selected_curves.items():
            tenors = list(rates_dict.keys())
            rates = list(rates_dict.values())
            
            date_string = name.split(" ")[1]
            date = datetime.strptime(date_string, '%Y/%m/%d').date()

            values = pd.DataFrame({'CURVE': [name] * len(tenors), 'VALUATION_DATE': [date] * len(tenors), 'TENOR': tenors,'RATE': rates})

            df = pd.concat([df.astype(values.dtypes), values.astype(df.dtypes)], ignore_index=True)
            
            fig.add_trace(go.Scatter(x=tenors, y=rates, mode='lines+markers', name=name))

        fig.update_layout(
                title='Yield Curve',
                xaxis_title='Tenor (Years)',
                yaxis_title='Zero Coupon Rate (Continuous) (%)',
                template='plotly_dark',
                showlegend=True
            )

        st.plotly_chart(fig)

        #endregion

        #region Finalize Functions

        create_download_button(df, 'Download Curve Data')

        st.pills('Remove curve', selected_curves.keys(), key='remove_curve')

        #endregion

    build_graph()

with forward:    
    build_filter(False)

    selected_curves: dict[str, dict[str: float]] = ss['selected_curves2']
    
    def build_table():
        if len(selected_curves) == 0:
            st.info('Select a curve to visualize or download!')
            return

        data = list(next(iter(selected_curves.items())))

        st.write(data[0])
        rates = data[1]
        
        discount_factors = {}

        for tenor, rate in rates.items():
            factor = 1 / (1 + rate / 100)**tenor
            discount_factors[tenor] = factor

        tenor_keys = list(rates.keys())
        tenors = [0, 0.25, 0.5, 1, 2, 3, 4, 5, 7, 10, 15, 20, 25, 30]
        tenors_converted = convert_floats_to_tenor(rates.keys())
        tenor_mapping = dict(zip(tenor_keys, tenors_converted))
        tenor_keys = [key for key in tenor_keys if key != 0]

        df = pd.DataFrame(columns=['Tenor'] + [tenor_mapping[tenor] for tenor in tenors])
        df['Tenor'] = [tenor_mapping[key] for key in tenor_keys]

        for tenor, rate in rates.items():
            if tenor == 0:
                continue

            for tenor2 in tenors:    
                if tenor2 == 0:
                    df.at[tenor_keys.index(tenor), tenor_mapping[tenor2]] = rate
                    continue

                rate_start = rates[tenor] / 100
                rate_forward = rates[max([key for key in rates.keys() if key < tenor + tenor2])] / 100

                # Calculate discount factors
                df_start = 1 / (1 + rate_start * 0.5)
                df_forward = 1 / (1 + rate_forward * 1)

                # Calculate the forward rate for 1 year from 0.5 years
                forward_rate = (df_start / df_forward) ** (1 / (1 - 0.5)) - 1
                forward_rate *= 100

                df.at[tenor_keys.index(tenor), tenor_mapping[tenor2]] = forward_rate

        grid = AgGridBuilder(df)

        grid.add_columns(['Tenor'], False, sort='', value_formatter=None)
        grid.add_columns([tenor_mapping[tenor] for tenor in tenors], False)
        grid.show_grid((len(df) + 1) * 30)

        create_download_button(df, 'Download Curve Data')
    
    build_table()