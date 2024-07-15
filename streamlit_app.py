import streamlit as st
from st_oauth import st_oauth

st.title("🎈 My new app")
st.write(
    "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
)

id = st_oauth(label='Click to login via Okta')