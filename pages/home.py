import streamlit as st
from tools import snowflake

st.write("# Welcome to the Stilson Dashboard! 👋")
st.write("For any enhancements or bugs, please contact Nicolas Au-Yeung via Teams or email (nicolas.au.yeung@fwd.com)")

st.session_state["conn"] = snowflake.connect_snowflake()