import streamlit as st
from utils.authenticate import authenticate
from utils.snowflake.snowflake import query
from streamlit import session_state as ss

def menu(page_name):
    apply_formatting()
    #set_title(page_name)
    auth = authenticate()

    if not auth:
        st.stop()

    get_permissions()

    authenticated_menu(page_name)

    add_login_name()

def authenticated_menu(page_name):
    with st.sidebar:
        st.page_link("streamlit_app.py", label="Home")

        permissions = ss['permissions']
        admin = ss['admin']
        group = permissions == 'Group'

        pages = {"Group": {"pages/asset_allocation.py": "Asset Allocation", "pages/pivot.py": "Funnelweb Pivot Table", "pages/curves.py": "Curves", "pages/repo.py": "Repos"},
                 "Hong Kong": {"pages/hk_asset_allocation.py": "Asset Allocation"},
                 "Admin": {"pages/users.py": "Users"}}#, "pages/funnelweb_monitor.py": "Funnelweb Monitor"}}

        page_permissions = {"Group": "Group", "Hong Kong": "HK", "Admin": "Admin"}
        
        verified = False

        for key, value in pages.items():
            permission = page_permissions[key]

            if permission not in permissions and not group or key == "Admin" and not admin:
                continue

            with st.expander(key, True):
                for key2, value2 in value.items():
                    st.page_link(key2, label=value2)

                    if key2 == page_name:
                        verified = True

    if not verified and page_name != "streamlit_app.py":
        st.write("You are not authorized to view this page!")
        st.stop()

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

def apply_formatting():
        # Read the CSS file
    with open("styles/styles.css") as f:
        css = f.read()

    # Inject the CSS into the Streamlit app
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    
    try:
        st.set_page_config(layout="wide", page_title='Stilson Dashboard', page_icon='styles/fwd_ico.png')
    except:
        pass

def get_permissions(force=False):
    if 'streamlit_permissions' not in ss or force:
        query_string = 'SELECT id, email, name, permissions, admin FROM supp.streamlit_users;'
        ss['streamlit_permissions'] = query(query_string)

    df = ss['streamlit_permissions']
    
    if 'ST_OAUTH_EMAIL' in ss:
        email = ss['ST_OAUTH_EMAIL'].lower()
    else:
        email = st.secrets["admin"]["email"].lower()
        
    df['EMAIL'] = df['EMAIL'].str.lower()
    df = df[df['EMAIL'] == email].reset_index(drop=True)

    if len(df) == 1:
        ss['nickname'] = df.at[0, 'NAME']
        ss['permissions'] = df.at[0, 'PERMISSIONS']
        ss['admin'] = df.at[0, 'ADMIN']
    elif len(df) == 0:
        st.write(f'You have no permissions set... Please contact {st.secrets["admin"]["name"]} to get access!')
        st.stop()
