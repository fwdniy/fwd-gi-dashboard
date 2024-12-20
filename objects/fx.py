import pandas as pd
from utils.snowflake.snowflake import query
from datetime import datetime

class Currency:
    name: str
    rates: dict[datetime, float] = {}

    def __init__(self, row):
        self.name = row['FX']
        self.rates = {}
        self.rates[row['VALUATION_DATE'].date()] = row['RATE']

    def add_data(self, row):
        self.name = row['FX']
        self.rates[row['VALUATION_DATE'].date()] = row['RATE']

    def get_fx_rate(self, date: datetime) -> float:
        if date in self.rates:
            return self.rates[date]
        
        for date_key in self.rates.keys():
            if date_key > date:
                return self.rates[date_key]

def build_currencies() -> list[Currency]:
    query_string: str = 'SELECT valuation_date, fx, rate FROM supp.fx_rates WHERE valuation_date >= \'2021-12-31\' ORDER BY valuation_date, fx;'
    df: pd.DataFrame = query(query_string)
    df['VALUATION_DATE'] = pd.to_datetime(df['VALUATION_DATE'])

    currencies: list[Currency] = []
    currency_names: list[str] = []

    for index, row in df.iterrows():
        fx_name = row['FX']
        
        if fx_name in currency_names:
            currencies[currency_names.index(fx_name)].add_data(row)
        else:
            currencies.append(Currency(row))
            currency_names.append(fx_name)

    return currencies

def get_fx_rate(currencies: list[Currency], currency_name, date):
    for currency in currencies:
        if currency.name != currency_name:
            continue

        return currency.get_fx_rate(date)