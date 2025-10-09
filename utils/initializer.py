from streamlit import session_state as ss

def initialize_variables(initialize_dict: dict):
    for key, value in initialize_dict.items():
        if key in ss:
            continue
        
        ss[key] = value