import streamlit as st
from streamlit_oauth import OAuth2Component
import json
import base64
from streamlit import session_state as ss

def authenticate():    
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

    st.page_link("streamlit_app.py", label="Home")
    st.page_link("pages/callback.py", label="Callback")

    fwdoauth = st.secrets["fwdoauth"]
    oauth2 = OAuth2Component(fwdoauth["client_id"], fwdoauth["client_secret"], fwdoauth["authorization_endpoint"], fwdoauth["token_endpoint"], None, None)

    if "ST_OAUTH" in ss:
        return

    result = oauth2.authorize_button("Continue with Okta SSO", fwdoauth["redirect_uri"], fwdoauth["scope"])

    if not result or 'token' not in result:
        return
    
    # If authorization successful, save token in session state
    ss["ST_OAUTH"] = result.get('token')
    
    id_token = ss["ST_OAUTH"]["id_token"]
    payload = id_token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    payload = json.loads(base64.b64decode(payload))
    ss["ST_OAUTH_EMAIL"] = payload["email"]

    st.rerun()