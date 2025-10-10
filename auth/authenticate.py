import streamlit as st
from streamlit_oauth import OAuth2Component
from streamlit import session_state as ss
import json
import base64

def authenticate_user():
    if "oauth" in st.secrets:
        authenticated = _check_sso_authentication()
    
        if authenticated == False:
            st.error("Unable to authenticate user. Please contact the administrator.")
        
        if not authenticated:
            st.sidebar.empty()
            st.stop()
        
    _get_permissions()
    
    if "oauth" not in st.secrets:
        _set_debug_permissions()
    
def _set_debug_permissions():
    ss['permissions'] = ['Admin', 'Fees']
    ss['lbu'] = 'Group'
    ss['nickname'] = ' to Debug Mode'

def _check_sso_authentication():
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

    fwdoauth = st.secrets["oauth"]
    oauth2 = OAuth2Component(fwdoauth["client_id"], fwdoauth["client_secret"], fwdoauth["authorization_endpoint"], fwdoauth["token_endpoint"], None, None)

    if "ST_OAUTH" in ss:
        return True

    result = oauth2.authorize_button("Continue with Okta SSO", fwdoauth["redirect_uri"], fwdoauth["scope"])

    if not result or 'token' not in result:
        return None
    
    # If authorization successful, save token in session state
    ss["ST_OAUTH"] = result.get('token')
    
    id_token = ss["ST_OAUTH"]["id_token"]
    payload = id_token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    payload = json.loads(base64.b64decode(payload))
    ss["ST_OAUTH_EMAIL"] = payload["email"]

    st.rerun()

@st.cache_data(show_spinner=False)
def get_user_permissions():
    sql = 'SELECT id, email, name, lbu, permissions, admin FROM supp.streamlit_users ORDER BY id;'
    df = ss.snowflake.query(sql)
        
    return df

def _get_permissions():
    df = get_user_permissions()
    
    email = st.secrets["admin"]["email"].lower()
    
    if 'ST_OAUTH_EMAIL' in ss:
        email = ss['ST_OAUTH_EMAIL'].lower()
    
    df['EMAIL'] = df['EMAIL'].str.lower()
    df = df[df['EMAIL'] == email].reset_index(drop=True)
    
    if len(df) == 1:
        ss['nickname'] = df.at[0, 'NAME']
        ss['permissions'] = list(df.at[0, 'PERMISSIONS'].split(';'))
        ss['lbu'] = df.at[0, 'LBU']
        admin = df.at[0, 'ADMIN']
        
        if admin:
            ss['permissions'].append('Admin')
        
    elif len(df) == 0:
        st.write(f'You have no permissions set... Please contact {st.secrets["admin"]["name"]} to get access!')
        st.stop()
        
def add_login_name():
    footer_text = f'Debug mode'
    
    if "ST_OAUTH_EMAIL" in st.session_state:
        footer_text = f'Logged in as {st.session_state["ST_OAUTH_EMAIL"]}'
    
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
            <p>{footer_text}</p>
        </div>
        """

    st.sidebar.markdown(footer, unsafe_allow_html=True)