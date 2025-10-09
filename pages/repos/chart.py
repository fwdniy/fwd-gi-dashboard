import streamlit as st
from streamlit import session_state as ss
import plotly.express as px

def build_chart(df):    
    chart_df = df.groupby(['ISSUER', 'CLOSING_DATE', 'L3_ASSET_TYPE']).sum('NET_MV').reset_index()
    chart_df['NET_MV_ROUNDED'] = chart_df['NET_MV'].round(0)

    # Determine facet column based on toggle
    selection = st.segmented_control(
        options=['Split', 'Total'],
        key='selected_facet',
        label='L3 Asset Type',
        selection_mode='single',
        default='Split'
    )
    
    facet_col = 'L3_ASSET_TYPE' if selection == 'Split' else None

    # Create the bar chart
    fig = px.bar(
        chart_df,
        x='ISSUER',
        y='NET_MV',
        color='CLOSING_DATE',
        barmode='group',
        facet_col=facet_col,
        hover_data={
            'NET_MV_ROUNDED': False,
            'CLOSING_DATE': True,
            'ISSUER': True,
            'L3_ASSET_TYPE': True,
            'NET_MV': True
        },
        text='NET_MV_ROUNDED',
        labels={
            'ISSUER': 'Issuer Name',
            'NET_MV': 'Net MV',
            'CLOSING_DATE': 'Closing Date',
            'L3_ASSET_TYPE': 'L3 Asset Type'
        }
    )

    # Display the chart
    st.plotly_chart(fig, use_container_width=True)