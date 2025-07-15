from streamlit import session_state as ss

def initialize_variables(label, default):
    if label in ss:
        return
    
    ss[label] = default