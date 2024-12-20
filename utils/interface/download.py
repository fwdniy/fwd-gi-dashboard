import pandas as pd
import io
import streamlit as st

def create_download_button(df: pd.DataFrame, label: str = 'Download Data'):
    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Data', index=False)

    buffer.seek(0)

    st.download_button(
        label=label,
        data=buffer,
        file_name='curve_rates.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )