import streamlit as st
from streamlit import session_state as ss

import pandas as pd
from io import BytesIO
from datetime import datetime

@st.cache_data(show_spinner=False)
def _to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Data')
        
    return output.getvalue()

@st.fragment(run_every=3)
def create_download_button(df, file_name, key, label = 'Data', add_time: bool = False):
    if 'excel_downloads' not in ss:
        ss.excel_downloads = {}    
            
    if key not in ss.excel_downloads:
        if  st.button(f"Generate {label}"):
            if add_time:
                file_name = f'{file_name}_{datetime.now().strftime("%Y%m%d%H%M%S")}'
            
            excel_data = _to_excel(df)
            ss.excel_downloads[key] = excel_data
    else:
        excel_data = ss.excel_downloads[key]
        
        st.download_button(
            label=f"Download {label}",
            data=excel_data,
            file_name=f'{file_name}.xlsx',
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            on_click=ss.excel_downloads.pop,
            args=[key])