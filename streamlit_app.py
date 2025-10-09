import streamlit as st
from streamlit import session_state as ss
from interface import initialize

initialize()

st.write(f'## Welcome {ss["nickname"]}! 👋')
st.write(f'For any enhancements or bugs, please contact {st.secrets["admin"]["name"]} via Teams or email ({st.secrets["admin"]["email"]})')
st.write(f'Your permissions are set to {" / ".join(ss["permissions"])}.')

with open("assets/release_notes.md", "r") as f:
    notes_md = f.read()

with st.expander("📝 Release Notes", expanded=True):
    st.markdown(notes_md)