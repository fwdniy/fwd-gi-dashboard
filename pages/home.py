import streamlit as st
from tools.snowflake import connect_snowflake

st.write("# Welcome to Stilson Dashboard! 👋")
st.write("For any bugs, please report them to Nicolas Au-Yeung via Teams or email (nicolas.au.yeung@fwd.com)")

st.session_state["conn"] = connect_snowflake()