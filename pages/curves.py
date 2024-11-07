import streamlit as st
from tools import filter, snowflake
from tools.filter.filter import build_tree_selectors
from datetime import datetime
import plotly.graph_objects as go

def get_curve_data():
    if "curves_rates_df" in st.session_state or "curve_names_df" in st.session_state:
        return
    
    df = snowflake.query("SELECT curve, valuation_date, tenor, rate, timestamp FROM supp.curve_rates;")
    df['VALUATION_DATE'] = df['VALUATION_DATE'].dt.date

    st.session_state["curves_rates_df"] = df

    df = snowflake.query("SELECT name, fx, type FROM supp.curve_name WHERE type <> 'requested';")
    st.session_state["curves_names_df"] = df

def build_curve_filter():
    get_curve_data()

    df_rates = st.session_state["curves_rates_df"]
    df_names = st.session_state["curves_names_df"]

    currencies = sorted(df_names['FX'].unique())

    currency = st.selectbox("Currency", currencies, index=currencies.index('USD'))

    currency_curves = sorted(df_names[df_names['FX'] == currency]['NAME'])

    curve_name = st.selectbox("Curve", currency_curves, index=next((i for i, item in enumerate(currency_curves) if 'govt' in item), 0))

    return curve_name

with st.expander("Filters"):
    with st.spinner('Fetching curve data...'):
        curve_name = build_curve_filter()
        filter.build_date_filter(True)

    current_date = st.session_state['Valuation Date']

    if "selected_curves" not in st.session_state:
        st.session_state["selected_curves"] = []

    if st.button("Add"):
        name = f"{current_date}/{curve_name}"
        if name not in st.session_state["selected_curves"]:
            st.session_state["selected_curves"].append(name)

def map_tenor_to_double(tenors):
    tenor_mapping = {"1m": 1 / 12, "3m": 3 / 12, "6m": 6 / 12}
    tenor_ignore = ["50"]
    tenor_list = []
    for tenor in tenors:
        if tenor in tenor_ignore:
            continue
        elif tenor.isdigit():
            tenor_list.append(float(tenor))
        elif tenor in tenor_mapping.keys():
            tenor_list.append(tenor_mapping[tenor])
        else:
            st.write(f"Unknown tenor name '{tenor}'!")

    return tenor_list

if len(st.session_state["selected_curves"]) == 0:
    st.write("Pick a curve!")
else:
    fig = go.Figure()

    for item in st.session_state["selected_curves"]:
        df = st.session_state["curves_rates_df"]
        split_list = item.split('/')
        date = split_list[0].replace("'", "")
        curve_name = split_list[1]
        values = df[(df['VALUATION_DATE'] == datetime.strptime(date, '%Y-%m-%d').date()) & (df['CURVE'] == curve_name)]

        tenors = map_tenor_to_double(values['TENOR'])
        
        name = f"{curve_name} - {date}"

        # Add the yield curve trace
        fig.add_trace(go.Scatter(x=tenors, y=values['RATE'], mode='lines+markers', name=name))

    # Add titles and labels
    fig.update_layout(
        title='Yield Curve',
        xaxis_title='Tenor (Years)',
        yaxis_title='Zero Coupon Rate (Continuous) (%)',
        template='plotly_dark',
        showlegend=True
    )

    st.plotly_chart(fig)

    for item in st.session_state["selected_curves"]:
        split_list = item.split('/')
        date = split_list[0].replace("'", "")
        curve_name = split_list[1]
        name = f"{curve_name} - {date}"
        
        if st.button(f"Remove {name}"):
            st.session_state["selected_curves"].remove(item)
            st.rerun()
        
