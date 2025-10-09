import streamlit as st
from streamlit import session_state as ss
from db.snowflake_streamlit import SnowflakeStreamlit
from auth.authenticate import authenticate_user, add_login_name
import inspect
import os

PAGES = {
    "General": {
        "pages/activity_monitor.py": "Activity Monitor",
        "pages/asset_allocation.py": "Asset Allocation",
        "pages/curves.py": "Curves",
        "pages/pivot.py": "Funnelweb Pivot Table",
        "pages/repos.py": "Repos",
    },
    "Hong Kong": {
        "pages/hk_asset_allocation.py": "Asset Allocation",
        "pages/collateral.py": "Collateral Calculator",
        "pages/projector.py": "Projector"
    },
    "Fees": {
        "pages/fees.py": "Fees Dashboard"
    },
    "Admin": {
        "pages/users.py": "Users",
        "pages/lbu_manager.py": "LBU Manager"
    },
    "Dev": {
        
    },
}

PAGE_PERMS = {
    "General": {},
    "Hong Kong": {"LBU": "HK" },
    "Admin": {"Permission": "Admin"},
    "Dev": {"Permission": "Admin"},
    "Fees": {"Permission": "Fees"}
}

def initialize():
    frame = inspect.stack()[1]
    caller_file = frame.filename
    page_name = caller_file.replace(f"{os.getcwd()}\\", "").replace("\\", "/")
    page_name = "/".join(caller_file.split("/")[-2:])
    
    _apply_formatting()
    _initialize_snowflake()
    authenticate_user()
    _build_nav_bar(page_name)
    
def _initialize_snowflake():
    if 'snowflake' in ss:
        return
    
    ss.snowflake = SnowflakeStreamlit()

def _apply_formatting():
    try:
        st.set_page_config(layout="wide", page_title='Stilson Dashboard', page_icon='assets/fwd_ico.png')
    except:
        pass
    
    add_login_name()

def _build_nav_bar(page_name: str):
    with open("assets/style.css") as css:
        st.html(f"<style>{css.read()}</style>")
    
    with st.container(key="app_title"):        
        matches = [inner[page_name] for inner in PAGES.values() if page_name in inner]
        page_title = matches[0] if matches else ''

        st.title(page_title)
    
    permissions = ss['permissions']
    lbu = ss['lbu']
    group = 'Group' == lbu
    verified = False
    
    with st.sidebar:
        st.page_link("streamlit_app.py", label="Home")

        for key, value in PAGES.items():            
            empty_section = len(value) == 0
            lbu_mismatch = PAGE_PERMS[key].get("LBU") is not None and PAGE_PERMS[key]["LBU"] != lbu and not group
            permission_mismatch = PAGE_PERMS[key].get("Permission") is not None and PAGE_PERMS[key]["Permission"] not in permissions
            
            if permission_mismatch or lbu_mismatch or empty_section:
                continue
                        
            with st.expander(key, True):
                for key2, value2 in value.items():
                    st.page_link(key2, label=value2)

                    if key2 == page_name:
                        verified = True

    if not verified and page_name != "streamlit_app.py":
        st.write("You are not authorized to view this page!")
        st.stop()