import pandas as pd
from dateutil.relativedelta import relativedelta
from streamlit import session_state as ss
import math

class Bond:
    def __init__(self, row, cf_df):
        """
        Initialize a Bond object with the given row and cashflow DataFrame.
        
        Args:
            row (pd.Series): A row from a DataFrame containing bond information.
            cf_df (pd.DataFrame): A DataFrame containing cashflow information.
        """
        
        self.row = row
        
        self.closing_date = row['CLOSING_DATE']
        self.position_id = row['POSITION_ID']
        self.lbu_code = row['LBU_CODE']
        self.fund_code = row['FUND_CODE']
        self.fwd_asset_type = row['FWD_ASSET_TYPE']
        self.account_code = row['ACCOUNT_CODE']
        self.security_name = row['SECURITY_NAME']
        self.isin = row['ISIN']
        self.bbgid = row['BBGID_V2']
        self.effective_maturity = row['EFFECTIVE_MATURITY']
        self.maturity = row['MATURITY']
        self.call_date = row['NEXT_CALL_DATE']
        self.rate = row['COUPON_RATE']
        self.freq = row['COUPNFREQ']
        self.position = row['POSITION']
        self.unit = row['UNIT']
        self.mortgage_fac = row['MTGE_FACTOR'] if row['MTGE_FACTOR'] != 0 else 1
        self.principal_fac = row['PRINCIPAL_FACTOR'] if row['PRINCIPAL_FACTOR'] != 0 else 1
        self.redemption_val = row['REDEMPTION_VALUE'] if row['REDEMPTION_VALUE'] != 0 else 100
        self.call_price = row['NEXT_CALL_PRICE']
        self.currency = row['CURRENCY']
        self.fx_rate = row['FX_RATE']
        
        self.per_x_months = 12 / self.freq if self.freq != 0 else 0
        self.payment = self.rate / self.freq if self.freq != 0 else 0
        self.notional = self.unit * self.position * self.mortgage_fac * self.principal_fac * self.fx_rate
        
        self.cashflow = self._compute_payment_details(cf_df)
        self.cashflow = self._apply_notional()
    
    def _compute_payment_details(self, df):        
        cashflows = []
        
        self.max_date = self.maturity if pd.isna(self.call_date) else self.call_date
        
        if self.max_date != self.effective_maturity:
            return
        
        # Add maturity payment
        cashflows.append(Cashflow(self.max_date, self._calculate_principal_amount()))
        
        # Exit if Zero Coupon
        if self.freq == 0:
            return cashflows
        
        # Assign dates
        self._assign_cashflow_dates(df)
        loop_date = self.penultimate_date
        
        while loop_date >= self.closing_date:
            cashflow = Cashflow(loop_date, self.payment)
            cashflows.append(cashflow)
            loop_date = self._adjust_date(loop_date)
            
        cashflows = sorted(cashflows, key=lambda x: x.date)
        
        return cashflows
    
    def _adjust_date(self, date):
        return date + relativedelta(months=-self.per_x_months)
    
    def _assign_cashflow_dates(self, df):
        self.first_date = self.closing_date
        self.penultimate_date = self._adjust_date(self.max_date)
        
        if len(df) > 0:
            pen_df = df[df['CATEGORY'] == 'penultimate_coupon_date']
        
            if len(pen_df) > 0 and pen_df['VALUE'].max() < self.max_date:
                self.penultimate_date = pen_df['VALUE'].max()
            
            first_df = df[df['CATEGORY'] == 'first_coupon_date']
            
            if len(first_df) > 0:
                self.first_date = first_df['VALUE'].max()
            
    def _calculate_principal_amount(self):
        redemption_value = self.redemption_val
        
        if not pd.isna(self.call_date) and redemption_value != self.call_price:
            redemption_value = self.call_price
        
        return self.payment + redemption_value
    
    def _apply_notional(self):        
        cashflows = self.cashflow
        
        for cashflow in cashflows:
            cashflow.payment *= self.notional / 100

        return cashflows
    
class Cashflow:
    def __init__(self, date, payment):
        self.date = date
        self.payment = payment
        self.year = math.ceil(relativedelta(date, ss.selected_comparison_date).years) + 1