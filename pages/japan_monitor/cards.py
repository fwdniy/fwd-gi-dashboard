import streamlit as st
from streamlit import session_state as ss
import pandas as pd
from .data import get_yields
from dateutil.relativedelta import relativedelta
# Inflow use initial account value
# Total use FUnnelweb

def build_aum_cards(pol_df, df):    
    inflow_column = 'USD_INITIAL_GA_ACCOUNT_VALUE'
    policy_date = 'POLICY_COMPLETION_DATE_RAW'
    
    date = ss.selected_date
    
    pol_df[policy_date] = pd.to_datetime(pol_df[policy_date], format='%Y%m%d')
    
    pol_df['MONTHS_FROM_SELECTED'] = pol_df[policy_date].apply(
        lambda x: relativedelta(x, pd.Timestamp(date)).months
    )
    
    st.write(pol_df)
    monthly_inflow = pol_df.groupby('MONTHS_FROM_SELECTED')[inflow_column].sum()
    one_month_inflow = monthly_inflow.get(0, 0)
    prev_month_inflow = monthly_inflow.get(-1, 0)
    #mom_change = ((one_month_inflow - prev_month_inflow) / prev_month_inflow * 100) if prev_month_inflow != 0 else 0
    
    aum = df[df['CLOSING_DATE'] == date]['NET_MV'].sum()
    
    col1, col2 = st.columns(2)
    with col1:
        #st.metric('AUM Inflow', f'${one_month_inflow:,.0f}', f"{mom_change:.0f}% MoM",border=True)
        st.metric('AUM Inflow', f'${one_month_inflow:,.0f}',border=True)
    with col2:
        st.metric('Total AUM', f'${aum:,.0f}',border=True)
        
def build_yield_cards():
    ust_df, cds_df = get_yields()
    
    ust_tenors = ust_df['TENOR'].unique().tolist()
    cds_tenors = cds_df['TENOR'].unique().tolist()
    reinvestment_bps = 100.0
    
    for tenor in ust_tenors:
        col1, col2, col3 = st.columns(3)

        ust_rate = list(ust_df[ust_df['TENOR'] == tenor]['RATE'])[0]
        
        cds_tenor = max([t for t in cds_tenors if int(t) <= int(tenor)])
        
        cds_rate = list(cds_df[cds_df['TENOR'] == cds_tenor]['SPREAD_BID'])[0]
        
        if tenor != cds_rate:
            cds_rate = (cds_rate * float(cds_tenor) + reinvestment_bps * (float(tenor) - float(cds_tenor))) / float(tenor)
        
        with col1:
            st.metric(f'UST {tenor}Y Yield', f"{ust_rate:.2f}%",border=True)
        with col2:
            st.metric(f'CDS {tenor}Y Spread', f"{cds_rate:.2f} bps",border=True)
        with col3:
            st.metric(f'All-in {tenor}Y Yield', f"{(ust_rate + cds_rate/100):.2f}%",border=True)