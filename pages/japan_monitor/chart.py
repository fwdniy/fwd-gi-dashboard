import streamlit as st
from streamlit import session_state as ss
import pandas as pd
from pages.projector.data import build_asset_liability_df
from dateutil.relativedelta import relativedelta

def build_cashflow_df(asset_df, pol_df):
    policy_start_column = 'POLICY_COMPLETION_DATE_RAW'
    policy_cashflow_column = 'USD_GA_ACCUMULATION_BENEFIT_AMOUNT'
    
    pol_df['POLICY_FINAL_DATE'] = pol_df.apply(
        lambda row: pd.to_datetime(
            f"{int(int(str(row[policy_start_column])[:4]) + row['POLICY_TERM'])}-{str(row[policy_start_column])[5:7]}-{str(row[policy_start_column])[8:10]}"
        ),
        axis=1
    )
    
    date = ss.selected_date
    
    pol_df['MONTHS'] = pol_df['POLICY_FINAL_DATE'].apply(
        lambda x: relativedelta(x, date).years * 12 + relativedelta(x, date).months
    )
    pol_df['MONTH'] = pol_df['MONTHS'].apply(lambda x: int(x))
    pol_df[policy_cashflow_column] = -pol_df[policy_cashflow_column] / 1_000_000
    pol_df = pol_df.groupby('MONTH', as_index=False).agg({policy_cashflow_column: 'sum'})
    pol_df['GROUP_NAME'] = 'JSPA'
    pol_df['MODE'] = 'Guaranteed Liabilities'
    
    pol_df.rename(columns={policy_cashflow_column: 'VALUE'}, inplace=True)
    
    period_df = build_asset_liability_df(asset_df, pol_df, True)
    
    return period_df