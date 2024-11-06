import streamlit as st

st.write("# Welcome to the Stilson Dashboard! 👋")
st.write("For any enhancements or bugs, please contact Nicolas Au-Yeung via Teams or email (nicolas.au.yeung@fwd.com)")

from cryptography.fernet import Fernet
import json
import base64

# Decrypt the data
'''
def decrypt_data(encrypted_data):
    key = st.secrets["fwdoauth"]["client_secret"]
    f = Fernet(key)
    decrypted_data = f.decrypt(encrypted_data)
    return decrypted_data.decode()

# Example usage
encrypted_message = st.session_state["ST_OAUTH"]["access_token"]
print(decrypt_data(encrypted_message))
'''

id_token = st.session_state["token"]["id_token"]
# verify the signature is an optional step for security
payload = id_token.split(".")[1]
# add padding to the payload if needed
payload += "=" * (-len(payload) % 4)
payload = json.loads(base64.b64decode(payload))
email = payload["email"]

st.write()