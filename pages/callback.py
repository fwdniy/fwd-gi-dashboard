import streamlit as st
from utils.interface.menu import menu

menu('Verified')
st.switch_page('./streamlit_app.py')