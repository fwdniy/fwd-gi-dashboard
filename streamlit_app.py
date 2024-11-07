#https://discuss.streamlit.io/t/streamlit-qs-make-permalinks-and-take-names-query-string-utils/44630
#https://discuss.streamlit.io/t/new-library-streamlit-server-state-a-new-way-to-share-states-across-sessions-on-the-server/14981
#https://discuss.streamlit.io/t/streamlit-on-hover-tabs-for-custom-navigation-bar/23879
#https://discuss.streamlit.io/t/new-component-streamlit-oauth/40364
#https://discuss.streamlit.io/t/new-component-streamlit-navigation-bar/66032
#https://github.com/Schluca/streamlit_tree_select

import streamlit as st
from tools.snowflake import connect_snowflake
from tools.auth import authenticate
import streamlit.components.v1 as components
from streamlit_js_eval import streamlit_js_eval
from styles.formatting import add_login_name

st.set_page_config(layout="wide", page_title='Stilson Dashboard', page_icon='styles/fwd_ico.png')
streamlit_js_eval(js_expressions="window.innerWidth", key='SCR')

if "pages" not in st.session_state:
    pages = st.session_state["pages"] = [st.Page("pages/callback.py", title="Callback")]
    nav = st.navigation(pages)
    nav.run()
else:
    pages = st.session_state["pages"]

authenticate()

if "ST_OAUTH_EMAIL" not in st.session_state and "fwdoauth" in st.secrets:
    st.stop()

pages = {'Home': 
            [st.Page("pages/home.py", title="Home")
        ],
        'Group': 
            [st.Page("pages/asset_allocation.py", title="Asset Allocation"),
            #st.Page("pages/monitor.py", title="Funnelweb Monitor"),
            st.Page("pages/curves.py", title="Curves"),
            #st.Page("pages/breakdown.py", title="Breakdown"), 
            #st.Page("pages/repo.py", title="Repos"),
            #st.Page("pages/snapshot.py", title="Snapshot")
        ],
        'Hong Kong':
            [st.Page("pages/asset_allocation_hk.py", title="Asset Allocation, Sensitivity and Ratings Profile")
        ]}

if ("ST_OAUTH" in st.session_state or "fwdoauth" not in st.secrets) and "callback_removed" not in st.session_state:
    st.session_state["pages"] = pages
    st.session_state["callback_removed"] = True
    st.rerun()

nav = st.navigation(pages)
nav.run()

add_login_name()

connect_snowflake()