import snowflake.connector
from datetime import datetime
import pandas as pd
import streamlit as st
from streamlit import session_state as ss
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

def connect_snowflake():
    if "conn" in st.session_state:
        return

    private_key_str = st.secrets["snowflake"]["private_key"]
    
    private_key = serialization.load_pem_private_key(
        private_key_str.encode(),
        password=None,
        backend=default_backend()
    )
    
    st.session_state["conn"] = snowflake.connector.connect(
        user=st.secrets["snowflake"]["username"],
        account='FWD-PROD',
        host='FWD-PROD.snowflakecomputing.com',
        role='GROUP_DASHBOARD_ROLE',
        warehouse='STREAMLIT',
        database='FUNNEL_PILOT',
        schema='FUNNEL',
        authenticator='snowflake_jwt',
        private_key=private_key
    )
    
    st.success('Connected to Snowflake via RSA')

def get_schema(cur):
    schema = cur.description
    columns = {}

    for column in schema:
        column_type = None
        if column[1] == 0:
            column_type = float
        elif column[1] == 2:
            column_type = str
        elif column[1] in [3, 8]:
            column_type = datetime
        elif column[1] == 13:
            column_type = bool
        else:
            print(f"error datatype for column '{column[0]}'")

        columns[column[0]] = column_type
    
    return columns

def convert_columns(df, cur):
    columns = get_schema(cur)

    for key, value in columns.items():
        if (value == datetime):
            df[key] = pd.to_datetime(df[key])
        else:
            df[key] = df[key].astype(value)

    return df

def query(query, sort_columns = []):
    if "conn" not in st.session_state:
        connect_snowflake()
    
    def query_data(query_string: str):            
        if 'sql_statement' in ss and query_string == ss['sql_statement']:
            return ss['query_df']
        
        with st.spinner('Fetching your requested data...'):
            conn = st.session_state["conn"]
            cur = conn.cursor()
            cur.execute(query)
            df = cur.fetch_pandas_all()

            if sort_columns != []:
                convert_columns(df, cur).sort_values(by=sort_columns)
            else:
                convert_columns(df, cur)
            
            ss['query_df'] = df

        ss['sql_statement'] = query_string

        return df
    
    df = query_data(query)
    
    return df

def non_query(query):
    if "conn" not in st.session_state:
        connect_snowflake()
    
    conn = st.session_state["conn"]
    cur = conn.cursor()
    cur.execute(query)