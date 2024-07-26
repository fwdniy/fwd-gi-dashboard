import streamlit as st

st.session_state["pages"] = st.session_state["pages"][1:]
st.switch_page("pages/home.py")