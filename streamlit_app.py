#https://discuss.streamlit.io/t/streamlit-qs-make-permalinks-and-take-names-query-string-utils/44630
#https://discuss.streamlit.io/t/new-library-streamlit-server-state-a-new-way-to-share-states-across-sessions-on-the-server/14981
#https://discuss.streamlit.io/t/streamlit-on-hover-tabs-for-custom-navigation-bar/23879
#https://discuss.streamlit.io/t/new-component-streamlit-oauth/40364
#https://discuss.streamlit.io/t/new-component-streamlit-navigation-bar/66032
#https://github.com/Schluca/streamlit_tree_select

import streamlit as st
from tools import snowflake
import streamlit.components.v1 as components
from streamlit_js_eval import streamlit_js_eval
from streamlit_oauth import OAuth2Component

st.set_page_config(layout="wide", page_title='Stilson Dashboard', page_icon='styles/fwd_ico.png')
streamlit_js_eval(js_expressions="window.innerWidth", key='SCR')

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

    fwdoauth = st.secrets["fwdoauth"]
    oauth2 = OAuth2Component(fwdoauth["client_id"], fwdoauth["client_secret"], fwdoauth["authorization_endpoint"], fwdoauth["token_endpoint"], None, None)

    if "ST_OAUTH" not in st.session_state:
        result = oauth2.authorize_button("Continue with Okta SSO", fwdoauth["redirect_uri"], fwdoauth["scope"])

        if result and 'token' in result:
            print(result)
            # If authorization successful, save token in session state
            st.session_state["ST_OAUTH"] = result.get('token')
            st.rerun()

if ("ST_OAUTH" in st.session_state or "fwdoauth" not in st.secrets) and "callback_removed" not in st.session_state:
    pages = st.session_state["pages"] = {'Home': 
                                            [st.Page("pages/home.py", title="Home")
                                             ],
                                         'Group': 
                                            [st.Page("pages/asset_allocation.py", title="Asset Allocation"), 
                                            #st.Page("pages/breakdown.py", title="Breakdown"), 
                                            #st.Page("pages/repo.py", title="Repos"),
                                            #st.Page("pages/snapshot.py", title="Snapshot")
                                            ],
                                            'Hong Kong':
                                            [st.Page("pages/asset_allocation_hk.py", title="Asset Allocation and Sensitivity"),
                                            st.Page("pages/ratings_profile.py", title="Ratings Profile")
                                            ]}
    st.session_state["callback_removed"] = True
    st.rerun()

nav = st.navigation(pages)
nav.run()

if "conn" not in st.session_state:
    snowflake.connect_snowflake()