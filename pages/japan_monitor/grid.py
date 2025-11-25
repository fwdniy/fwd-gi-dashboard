import streamlit as st
from streamlit import session_state as ss
import pandas as pd
from grid import AgGridBuilder

def build_profile_grid(pol_df, aum_df):    
    date = ss.selected_date
    asset_df = aum_df[aum_df['CLOSING_DATE'] == date]
    
    asset_df['TENOR'] = asset_df['FUND_CODE'].str.extract(r'(\d+)')
    asset_df = asset_df[['TENOR', 'NET_MV']]
    asset_df['NET_MV_%'] = asset_df['NET_MV'] / asset_df['NET_MV'].sum() * 100
    st.write(asset_df)
    
    _process_policy_classification(pol_df)
    
def _process_policy_classification(df):
    dob_column = 'DOB_RAW'
    liability_mv = 'USD_GA_ACCOUNT_VALUE'
    
    df['DOB'] = pd.to_datetime(df[dob_column].str[:6] + '01', format='%Y%m%d')
    
    df['CURRENT_AGE'] = df['DOB'].apply(lambda x: (pd.to_datetime(ss.selected_date) - x).days // 365)
    bins = [0, 18, 30, 40, 50, 60, 70, 80, 100]
    labels = ['0-18', '19-30', '31-40', '41-50', '51-60', '61-70', '71-80', '81+']
    df['AGE_RANGE'] = pd.cut(df['CURRENT_AGE'], bins=bins, labels=labels, right=False)
    df['GENDER_MAPPED'] = df['GENDER'].map({1: 'Male', 2: 'Female'})
    
    pivot_table = df.pivot_table(
        index='POLICY_TERM',
        columns=['GENDER_MAPPED', 'AGE_RANGE'],
        values=liability_mv,
        aggfunc='sum',
        fill_value=0
    )
    
    # Add a total row and column
    pivot_table.loc['Total'] = pivot_table.sum(axis=0)
    pivot_table['Total'] = pivot_table.sum(axis=1)
    
    # Calculate percentage of total
    pivot_table_percentage = pivot_table.iloc[:-1, :-1].div(pivot_table.iloc[:-1, :-1].sum().sum()) * 100
    # Add back the "Total" row and column
    pivot_table_percentage.loc['Total'] = pivot_table_percentage.sum(axis=0)
    pivot_table_percentage['Total'] = pivot_table_percentage.sum(axis=1)
    
    # Display both the pivot table and the percentage table
    st.write("Pivot Table (Absolute Values):")
    st.write(pivot_table)
    
    st.write("Pivot Table (% of Total):")
    st.write(pivot_table_percentage)

def build_yield_grid(pol_df, aum_df):
    date = ss.selected_date
    yield_df = aum_df[aum_df['CLOSING_DATE'] == date]
    yield_df = yield_df[['FUND_CODE', 'WEIGHTED_AVG_YTM']]
    pol_ytm_column = 'USD_I_ISSUE_BIR'
    pol_weight = 'USD_GA_ACCOUNT_VALUE'
    
    # Calculate weighted yield
    pol_df['WEIGHTED_YIELD'] = pol_df[pol_ytm_column] * pol_df[pol_weight]
    
    # Group by POLICY_TERM and calculate weighted average yield
    grouped_pol = pol_df.groupby('POLICY_TERM').apply(
        lambda x: pd.Series({
            'WEIGHTED_AVG_YIELD': x['WEIGHTED_YIELD'].sum() / x[pol_weight].sum() if x[pol_weight].sum() > 0 else 0,
            'TOTAL_WEIGHT': x[pol_weight].sum()
        })
    ).reset_index()
    
    st.write(yield_df)
    st.write(grouped_pol)
    
def build_duration_grid(pol_df, aum_df):    
    date = ss.selected_date
    asset_df = aum_df[aum_df['CLOSING_DATE'] == date]
    asset_df = asset_df[['FUND_CODE', 'WEIGHTED_AVG_DURATION']]
    
    policy_cashflow_column = 'USD_GA_ACCOUNT_VALUE'
    # Calculate weighted duration for policies
    pol_df[policy_cashflow_column] = pol_df[policy_cashflow_column]
    pol_df['YEARS'] = pol_df['MONTHS'] / 12
    pol_df['WEIGHTED_DURATION'] = pol_df['YEARS'] * pol_df[policy_cashflow_column]

    # Group by POLICY_TERM and calculate weighted average duration
    grouped_pol = pol_df.groupby('POLICY_TERM').apply(
        lambda x: pd.Series({
            'WEIGHTED_AVG_DURATION': x['WEIGHTED_DURATION'].sum() / x[policy_cashflow_column].sum() if x[policy_cashflow_column].sum() > 0 else 0,
            'TOTAL_CASHFLOW': x[policy_cashflow_column].sum()
        })
    ).reset_index()
    
    st.write(asset_df)
    st.write(grouped_pol)