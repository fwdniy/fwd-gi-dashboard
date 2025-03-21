import pandas as pd
import io
import streamlit as st
from datetime import datetime

def create_download_button(df: pd.DataFrame, file_name: str, label: str = 'Download Data', add_time: bool = False):
    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Data', index=False)

    buffer.seek(0)
    
    if add_time:
        file_name = f'{file_name}_{datetime.now().strftime("%Y%m%d%H%M%S")}'

    st.download_button(
        label=label,
        data=buffer,
        file_name=f'{file_name}.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )