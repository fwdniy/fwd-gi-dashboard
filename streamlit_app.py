import streamlit as st
from st_oauth import st_oauth
from tools import snowflake
import streamlit.components.v1 as components

st.set_page_config(layout="wide", page_title='Stilson Dashboard', page_icon='styles/fwd_ico.png')

if "pages" not in st.session_state:
    pages = st.session_state["pages"] = [st.Page("pages/callback.py", title="Callback")]
    nav = st.navigation(pages)
    nav.run()
else:
    pages = st.session_state["pages"]

if "fwdoauth" in st.secrets:
    st.markdown(
    """
        <style>
            div[class="st-emotion-cache-1p1m4ay e3g6aar0"] {
                display: none;
            }
        </style>
    """,
    unsafe_allow_html=True
    )

    id = st_oauth('fwdoauth')

if "ST_OAUTH" in st.session_state:
    st.sidebar.write(f"Logged in as {st.session_state['ST_OAUTH']}")
else:
    st.sidebar.write(f"Local Debugging")

if ("ST_OAUTH" in st.session_state or "fwdoauth" not in st.secrets) and "callback_removed" not in st.session_state:
    pages = st.session_state["pages"] = [st.Page("pages/home.py", title="Home"), st.Page("pages/asset_allocation.py", title="Asset Allocation"), st.Page("pages/breakdown.py", title="Breakdown")]
    st.session_state["callback_removed"] = True
    st.rerun()

nav = st.navigation(pages)
nav.run()

if "conn" not in st.session_state:
    snowflake.connect_snowflake()