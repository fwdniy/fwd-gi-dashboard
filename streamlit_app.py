import streamlit as st
from utils.interface.menu import menu
from streamlit_js_eval import streamlit_js_eval

st.set_page_config(layout="wide", page_title='Stilson Dashboard', page_icon='styles/fwd_ico.png')
streamlit_js_eval(js_expressions="window.innerWidth", key='SCR')

st.markdown(
    """
    <style>
    .css-1jc7ptx, .e1ewe7hr3, .viewerBadge_container__1QSob,
    .styles_viewerBadge__1yB5_, .viewerBadge_link__1S137,
    .viewerBadge_text__1JaDK {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)

menu('Home')

st.write("# Welcome to the Stilson Dashboard! 👋")
st.write("For any enhancements or bugs, please contact Nicolas Au-Yeung via Teams or email (nicolas.au.yeung@fwd.com)")