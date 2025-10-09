import streamlit as st
from streamlit import session_state as ss
import plotly.graph_objects as go
import pandas as pd
from .data import convert_tenors_to_float, build_spot_df
from utils.download import create_download_button

def build_spot_chart():
    if ss.selected_mode != 'Spot':
        return
    
    selected_curves = ss.selected_curves
    
    if len(selected_curves) == 0:
        return
        
    fig = go.Figure()
    chart_df = pd.DataFrame(columns=['CURVE', 'VALUATION_DATE', 'TENOR', 'RATE'])
        
    for name, df in selected_curves.items():
        values, tenors, rates = build_spot_df(df)

        chart_df = pd.concat([chart_df.astype(values.dtypes), values.astype(df.dtypes)], ignore_index=True)
        
        fig.add_trace(go.Scatter(x=tenors, y=rates, mode='lines+markers', name=name))
    
    fig.update_layout(
                title='Yield Curve',
                xaxis_title='Tenor (Years)',
                yaxis_title='Zero Coupon Rate (Continuous) (%)',
                template='plotly_dark',
                showlegend=True,
                legend=dict(
                    orientation='h',
                    y=-0.2,
                    x=0.5,
                    xanchor='center',
                    yanchor='top'
                )
            )

    st.plotly_chart(fig)
    
    create_download_button(chart_df, 'curve_spot_rates', 'curve_spot_rates', 'Curve Data')