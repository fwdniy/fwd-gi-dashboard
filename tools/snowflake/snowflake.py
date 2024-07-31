import snowflake.connector
from datetime import datetime
import pandas as pd
import streamlit as st

def connect_snowflake():
    st.session_state["conn"] = snowflake.connector.connect(
        user=st.secrets["snowflake"]["username"],
        password=st.secrets["snowflake"]["password"],
        account='FWD-PROD',
        host='FWD-PROD.snowflakecomputing.com',
        role='GROUP_DASHBOARD_ROLE',
        warehouse='STREAMLIT',
        database='FUNNEL_PILOT',
        schema='FUNNEL'
    )

def get_schema(cur):
    schema = cur.description
    columns = {}

    for column in schema:
        column_type = None
        if column[1] == 0:
            column_type = float
        elif column[1] == 2:
            column_type = str
        elif column[1] == 3:
            column_type = datetime
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
    
    conn = st.session_state["conn"]
    cur = conn.cursor()
    cur.execute(query)
    df = cur.fetch_pandas_all()

    if sort_columns != []:
        convert_columns(df, cur).sort_values(by=sort_columns)
    else:
        convert_columns(df, cur)

    return df