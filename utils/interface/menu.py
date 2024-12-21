import streamlit as st
from utils.authenticate import authenticate

def menu(page_name):    
    #set_title(page_name)    
    auth = authenticate()

    if not auth:
        st.stop()

    authenticated_menu()

    add_login_name()

def authenticated_menu():
    with st.sidebar:
        st.page_link("streamlit_app.py", label="Home")

        with st.expander("Group", True):
            st.page_link("nav/asset_allocation.py", label="Asset Allocation")
            st.page_link("nav/pivot.py", label="Funnelweb Pivot Table")
            st.page_link("nav/curves.py", label="Curves")

        with st.expander("Hong Kong", True):
            st.page_link("nav/hk_asset_allocation.py", label='Asset Allocation')

def set_title(page_name):
    '''st.markdown(r"""
        <style>
            div[data-testid="stDecoration"]::after {
                content: '""" + page_name + r"""';
                display: block;
            }
        </style>
        """, unsafe_allow_html=True)'''

def add_login_name():
    if "ST_OAUTH_EMAIL" not in st.session_state:
        return
    
    footer = f"""
        <style>
            .footer {{
                position: fixed;
                bottom: 0;
                width: 100%;
                text-align: left;
            }}
        </style>
        <div class="footer">
            <p>Logged in as {st.session_state["ST_OAUTH_EMAIL"]}</p>
        </div>
        """

    st.sidebar.markdown(footer, unsafe_allow_html=True)