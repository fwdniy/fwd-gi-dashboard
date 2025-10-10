import streamlit as st

def calculate_forward_rates_for_tenor(tenor, rate, tenors, tenor_rates, all_tenors):
    forward_rates = {}

    for tenor2 in all_tenors:
        f_tenor = tenor + tenor2

        if tenor2 == 0:
            forward_rates[str(tenor2)] = rate
            continue
        elif f_tenor > max(all_tenors):
            continue

        smaller_tenor = max([t for t in tenors if t < f_tenor], default=min(tenors))
        bigger_tenor = min([t for t in tenors if t > f_tenor], default=max(tenors))

        if smaller_tenor != bigger_tenor:
            forward_rates[str(tenor2)] = _interpolate_forward_rate(
                tenor, rate, f_tenor, smaller_tenor, bigger_tenor, tenor_rates
            )

    return forward_rates

def _interpolate_forward_rate(tenor, rate, f_tenor, smaller_tenor, bigger_tenor, tenor_rates):
    smaller_rate = tenor_rates[smaller_tenor]
    bigger_rate = tenor_rates[bigger_tenor]

    interpolated_rate = smaller_rate + (
        (f_tenor - smaller_tenor) / (bigger_tenor - smaller_tenor)
        * (bigger_rate - smaller_rate)
    )

    return (interpolated_rate * f_tenor - rate * tenor) / (f_tenor - tenor)

@st.cache_data(show_spinner=False)
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

@st.cache_data(show_spinner=False)
def convert_floats_to_tenor(tenors: list[float]):
    # Round tenor_mapping values to 6 decimal places
    tenor_mapping: dict[str, float] = {key: round(value, 6) for key, value in {"1m": 1 / 12, "3m": 3 / 12, "6m": 6 / 12}.items()}
    tenors_converted: list[str] = []

    for tenor in tenors:
        # Round tenor to 6 decimal places for comparison
        rounded_tenor = round(tenor, 6)
        
        if rounded_tenor in tenor_mapping.values():
            index = list(tenor_mapping.values()).index(rounded_tenor)
            tenors_converted.append(list(tenor_mapping.keys())[index])
        else:
            tenors_converted.append(f'{int(tenor)}y')

    return tenors_converted