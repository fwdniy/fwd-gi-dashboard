import pandas as pd
from io import BytesIO
import streamlit as st
from datetime import datetime

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Data')
        
    return output.getvalue()

def create_download_button(df: pd.DataFrame, file_name: str, label: str = 'Data', add_time: bool = False):
    if add_time:
        file_name = f'{file_name}_{datetime.now().strftime("%Y%m%d%H%M%S")}'
        
    if st.button(f"Generate {label}"):
        excel_data = to_excel(df)
        st.download_button(
            label=f"Download {label}",
            data=excel_data,
            file_name=f'{file_name}.xlsx',
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")