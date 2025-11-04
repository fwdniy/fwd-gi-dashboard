import streamlit as st
from streamlit import session_state as ss
import pandas as pd
from dateutil.relativedelta import relativedelta
from datetime import datetime

COLUMN_MAPPING = {
    'fund_code': 'FUND_CODE',
    'maturity': 'EFFECTIVE_MATURITY',
    'call_date': 'NEXT_CALL_DATE',
    'call_price': 'NEXT_CALL_PRICE',
    'redemption_value': 'REDEMPTION_VALUE',
    'rate': 'COUPON_RATE',
    'freq': 'COUPNFREQ',
    'coupon': 'COUPON',
    'first_coupon': 'first_coupon_date',
    'penultimate_coupon': 'penultimate_coupon_date',
    'unit': 'UNIT',
    'position': 'POSITION',
    'mortgage_fac': 'MTGE_FACTOR',
    'principal_fac': 'PRINCIPAL_FACTOR',
    'fx_rate': 'FX_RATE',
    'fwd_asset_type': 'FWD_ASSET_TYPE',
    'manager': 'MANAGER',
    'security_name': 'SECURITY_NAME',
    'position_id': 'POSITION_ID',
    'bbgid_v2': 'BBGID_V2',
    'time_until_maturity': 'TIME_UNTIL_MATURITY',
    'year': 'YEAR',
    'value': 'VALUE',
    'notional': 'NOTIONAL',
    'cashflow': 'CASHFLOW',
    'cashflow_dollar': 'CASHFLOW_DOLLAR',
    'coupon_dollar': 'COUPON_DOLLAR',
    'principal_dollar': 'PRINCIPAL_DOLLAR',
    'bbg_asset_type': 'BBG_ASSET_TYPE',
    'net_mv': 'NET_MV',
    'principal': 'PRINCIPAL',
}

def build_cashflows(pos_df, cf_df):
    fund_codes = ss.selected_funds
    df = pos_df[pos_df[COLUMN_MAPPING['fund_code']].isin(fund_codes)].reset_index(drop=True)

    def calculate_coupon(row):
        if row[COLUMN_MAPPING['bbg_asset_type']] == 'Mortgage Backed Security' and row[COLUMN_MAPPING['rate']] == 0:
            return 6 / row[COLUMN_MAPPING['freq']]
        elif row[COLUMN_MAPPING['freq']] == 0:
            return row[COLUMN_MAPPING['rate']]
        else:
            return row[COLUMN_MAPPING['rate']] / row[COLUMN_MAPPING['freq']]

    df[COLUMN_MAPPING['coupon']] = df.apply(calculate_coupon, axis=1)

    cf_df = cf_df.pivot(index='BBGID', columns='CATEGORY', values='VALUE').reset_index()
    df = pd.merge(df, cf_df, left_on='BBGID_V2', right_on='BBGID', how='left')

    cashflows_list = []
    coupon_dollars_list = []
    principal_dollars_list = []
    notionals_list = []
    cashflow_dollars_list = []

    for _, row in df.iterrows():        
        cashflow_columns = ['maturity', 'call_date', 'call_price', 'redemption_value', 'coupon', 'freq', 'first_coupon', 'penultimate_coupon']
        
        cashflow_kwargs = _build_kwargs(row, cashflow_columns)
        cashflow, coupons, principal = _compute_cashflows(**cashflow_kwargs)

        notional_columns = ['unit', 'position', 'mortgage_fac', 'principal_fac', 'fx_rate', 'net_mv']
        notional_kwargs = _build_kwargs(row, notional_columns)
        notional = _compute_notional(**notional_kwargs)

        cashflow_dollar = _adjust_cashflows(cashflow, notional)
        coupons_dollar = _adjust_cashflows(coupons, notional)
        principal_dollar = _adjust_cashflows(principal, notional)

        cashflows_list.append(cashflow)
        notionals_list.append(notional)
        cashflow_dollars_list.append(cashflow_dollar)
        coupon_dollars_list.append(coupons_dollar)
        principal_dollars_list.append(principal_dollar)

    # Add new columns to the DataFrame
    df[COLUMN_MAPPING['cashflow']] = cashflows_list
    df[COLUMN_MAPPING['notional']] = notionals_list
    df[COLUMN_MAPPING['cashflow_dollar']] = cashflow_dollars_list
    df[COLUMN_MAPPING['coupon_dollar']] = coupon_dollars_list
    df[COLUMN_MAPPING['principal_dollar']] = principal_dollars_list

    return df

def _compute_cashflows(maturity, call_date, call_price, redemption_value, coupon, freq, first_coupon, penultimate_coupon):
    selected_date = datetime.combine(ss.selected_date, datetime.min.time())

    max_date = maturity.to_pydatetime()
    principal = redemption_value

    if call_date is not pd.NaT and call_date.to_pydatetime() == max_date and call_price != 0.0:  # Sentinel value for missing dates
        principal = call_price

    if principal == 0.0:
        principal = 100.0
    
    final_payment = principal + coupon

    cashflows = {}
    coupons = {}
    principals = {}
    
    cashflows[to_date_string(max_date)] = final_payment
    coupons[to_date_string(max_date)] = coupon
    principals[to_date_string(max_date)] = principal

    if freq != 0:
        per_x_months = 12 / freq

        # Generate all cashflow dates efficiently
        loop_date = penultimate_coupon.to_pydatetime()
        
        if penultimate_coupon is pd.NaT or penultimate_coupon > max_date:
            loop_date = max_date - relativedelta(months=per_x_months)
        elif max_date == loop_date:
            loop_date = loop_date - relativedelta(months=per_x_months)
        
        while loop_date >= selected_date:
            coupons[to_date_string(loop_date)] = cashflows[to_date_string(loop_date)] = coupon
            principals[to_date_string(loop_date)] = 0
            loop_date -= relativedelta(months=per_x_months)
        
        if first_coupon > loop_date and first_coupon < selected_date:
            loop_date = first_coupon.to_pydatetime()
        
        last_date = to_date_string(loop_date)
        
        if last_date == None:
            last_date = selected_date

        coupons[last_date] = principals[last_date] = cashflows[last_date] = 0

    return cashflows, coupons, principals

def _compute_notional(unit, position, mortgage_fac, principal_fac, fx_rate, net_mv):
    mortgage_fac = 1 if mortgage_fac == 0 else mortgage_fac
    principal_fac = 1 if principal_fac == 0 else principal_fac
    
    notional = unit * position * mortgage_fac * principal_fac * fx_rate
    
    if notional / net_mv > 100:
        notional /= 1000
    
    return notional

def _adjust_cashflows(cashflow, notional):
    cashflow_adjusted = {}
    
    for key, value in cashflow.items():
        cashflow_adjusted[key] = value / 100 * notional
        
    return cashflow_adjusted

def _build_kwargs(row, columns):
    kwargs = {}

    for column in columns:
        value = row[COLUMN_MAPPING[column]]

        kwargs[column] = value
        
    return kwargs

def to_date_string(timestamp):
    """Convert pandas.Timestamp to 'YYYY-MM-DD' string."""
    if pd.isna(timestamp):
        return None
    return timestamp.strftime('%Y-%m-%d')

def build_yearly_cashflow_df(df, cashflow_types):
    date = ss.selected_comparison_date
    
    cashflow_columns = ['year', 'value', 'principal', 'coupon']
    columns = ['fund_code', 'fwd_asset_type', 'manager', 'year', 'value', 'position_id', 'security_name', 'bbgid_v2', 'notional', 'coupon', 'freq', 'time_until_maturity']
    columns = list(dict.fromkeys(cashflow_columns + columns))
    
    rows = []
    
    for _, row in df.iterrows():        
        row_data = {}

        for column in columns:
            if column not in cashflow_columns:
                column_name = COLUMN_MAPPING[column]
                row_data[column_name] = row[column_name]
        
        cashflow = row[COLUMN_MAPPING['cashflow_dollar']]
        coupons = row[COLUMN_MAPPING['coupon_dollar']]
        principal = row[COLUMN_MAPPING['principal_dollar']]
        
        yearly_cashflow = {}
        yearly_principal = {}
        yearly_coupon = {}

        for payment_date in cashflow.keys():
            year = relativedelta(datetime.strptime(payment_date, "%Y-%m-%d"), date).years
            
            if year not in yearly_cashflow.keys():
                yearly_cashflow[year] = cashflow[payment_date]
                yearly_principal[year] = principal[payment_date]
                yearly_coupon[year] = coupons[payment_date]
            else:
                yearly_cashflow[year] += cashflow[payment_date]
                yearly_principal[year] += principal[payment_date]
                yearly_coupon[year] += coupons[payment_date]

        for year, value in yearly_cashflow.items():
            row_data_copy = row_data.copy()
            row_data_copy[COLUMN_MAPPING['year']] = year + 1
            row_data_copy[COLUMN_MAPPING['value']] = value
            row_data_copy[COLUMN_MAPPING['principal']] = yearly_principal[year]
            row_data_copy[COLUMN_MAPPING['coupon']] = yearly_coupon[year]
            rows.append(row_data_copy)

    security_df = pd.DataFrame(rows, columns=[COLUMN_MAPPING[column] for column in columns])
    security_df = security_df.sort_values(by=[COLUMN_MAPPING[column] for column in cashflow_columns], ascending=[True if column == 'year' else False for column in cashflow_columns])
    yearly_df = security_df[[COLUMN_MAPPING[column] for column in cashflow_columns]].copy()
    yearly_df = yearly_df.groupby([COLUMN_MAPPING['year']], as_index=False).sum(numeric_only=True)

    yearly_df[[COLUMN_MAPPING['principal'], COLUMN_MAPPING['coupon'], COLUMN_MAPPING['value']]] /= 1_000_000
    
    yearly_df = yearly_df.rename(columns={COLUMN_MAPPING['value']: cashflow_types['asset']})    

    return security_df, yearly_df