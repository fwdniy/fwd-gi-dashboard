import streamlit as st
from streamlit import session_state as ss
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def build_chart(df, cashflow_types, cashflow_colors):
    color_mapping = {cashflow_types[key]: cashflow_colors[key] for key in cashflow_types}
    
    columns = ['YEAR'] + [cashflow_types[key] for key in cashflow_types if cashflow_types[key] in df.columns]
    flat_df = df[columns]
    flat_df = pd.melt(flat_df, id_vars=['YEAR'], var_name='MODE', value_name='VALUE')
    
    fig = px.bar(flat_df, x='YEAR', y='VALUE', color='MODE', color_discrete_map=color_mapping)
    
    fig.add_trace(go.Scatter(
        x=df['YEAR'],
        y=df['Net Cashflow'],
        mode='markers',
        name='Net Value',
        marker=dict(color='#CC0000', size=10, symbol=141, line=dict(
                color='#CC0000',
                width=3
            ))
    ))
    
    fig.add_trace(go.Scatter(
        x=df['YEAR'],
        y=df['Cumulative Cashflow'],
        mode='lines',
        name='Cumulative Net Value',
        line=dict(color='#CC0000', width=2, dash='dash')
    ))
        
    st.plotly_chart(fig)