import streamlit as st
from streamlit import session_state as ss
from .snowflake_conn import SnowflakeClient
import pandas as pd

class SnowflakeStreamlit:
    def __init__(self):
        config = st.secrets["snowflake"]
        snowflake_client = SnowflakeClient(config)
        st.toast('Connected to Snowflake')
        self.client = snowflake_client
        
        self.sql = ''
        self.df = pd.DataFrame()
    
    def query(self, sql: str, sort_columns: list = [], refresh: bool = False):
        if sql == self.sql and not self.df.empty and not refresh:
            return self.df
        
        with st.spinner('Fetching your requested data...'):
            df = self.client.query(sql, sort_columns)
        
        return df
    
    def execute(self, sql: str):
        with st.spinner('Executing SQL command...'):
            self.client.execute(sql)