import pandas as pd
from utils.snowflake.snowflake import query
from datetime import datetime

class Curve:
    name: str
    fx: str
    type: str
    rates: pd.DataFrame

    def __init__(self, row):
        self.name = row['NAME']
        self.fx = row['FX']
        self.type = row['TYPE']

    def get_rates(self, date: datetime, converted: bool = False) -> float:
        df = self.rates

        df = df[df['VALUATION_DATE'] == date]

        if not converted:
            return dict(zip(df['TENOR'], df['RATE']))
        else:
            return convert_tenors_to_float(dict(zip(df['TENOR'], df['RATE'])))

def build_curves() -> list[Curve]:
    query_string: str = 'SELECT name, fx, type FROM supp.curve_name WHERE enabled = true;'
    df: pd.DataFrame = query(query_string)
    
    curves: list[Curve] = []
    curve_names: list[str] = []

    for index, row in df.iterrows():
        curves.append(Curve(row))
        curve_names.append(row['NAME'])
    
    query_string = 'SELECT valuation_date, curve, tenor, rate FROM supp.curve_rates WHERE valuation_date >= \'2021-12-31\' ORDER BY valuation_date, curve, tenor;'
    df = query(query_string)
    df['VALUATION_DATE'] = df['VALUATION_DATE'].dt.date

    for curve in curves:
        curve_name = curve.name
        curve.rates = df.loc[df['CURVE'] == curve_name]

    return curves

def convert_tenors_to_float(rates: dict[str, float]):
    tenor_mapping: dict[str, float] = {"1m": 1 / 12, "3m": 3 / 12, "6m": 6 / 12}
    rates_converted: dict[float, float] = {}

    for tenor, rate in rates.items():
        if tenor.isdigit():
            rates_converted[float(tenor)] = float(rate)
        elif tenor in tenor_mapping.keys():
            rates_converted[tenor_mapping[tenor]] = float(rate)
        else:
            print(f"Unknown tenor name '{tenor}'!")

    rates_converted = dict(sorted(rates_converted.items()))

    return rates_converted

def convert_floats_to_tenor(tenors: list[float]):
    tenor_mapping: dict[str, float] = {"1m": 1 / 12, "3m": 3 / 12, "6m": 6 / 12}
    tenors_converted: list[str] = []

    for tenor in tenors:
        if tenor in tenor_mapping.values():
            index = list(tenor_mapping.values()).index(tenor)
            tenors_converted.append(list(tenor_mapping.keys())[index])
        else:
            tenors_converted.append(f'{int(tenor)}y')

    return tenors_converted