import streamlit as st
from streamlit import session_state as ss
import pandas as pd
from auth.authenticate import get_user_permissions

def get_permissions():
    df = get_user_permissions()
    return df

def edit_data(grid, df):
    data = grid.grid['data']
    columns = [column for column in df.columns if column != '::auto_unique_id::']
    df = df[columns]
    
    comparison = pd.concat([data, df], axis=0, keys=['NEW', 'OLD'], names=['Source']).reset_index(level=0)
    differences = comparison.drop_duplicates(subset=data.columns, keep=False)
    
    difference_ids = list(differences['ID'].unique())
    
    result = pd.merge(
            data,
            df,
            on='ID',
            how='inner',
            suffixes=('_NEW', '_OLD')
        )
    
    result = result[result['ID'].isin(difference_ids)]
    
    with st.expander('Edit User'):
        if len(result) == 0:
            st.write('No data changes detected.')
            return
        
        st.write(result)
        
        if st.button('Apply Changes'):
            if 'edit_user_details' not in ss:
                _confirm_edit_user(result)
                return
            
        if 'edit_user_details' in ss:
            _edit_user()
            
def _edit_user():
    df = ss.edit_user_details
    
    for _, row in df.iterrows():
        sql = f"UPDATE supp.streamlit_users SET email = '{row['EMAIL_NEW']}', name = '{row['NAME_NEW']}', lbu = '{row['LBU_NEW']}', permissions = '{row['PERMISSIONS_NEW']}' WHERE id = {row['ID']};"
        ss.snowflake.execute(sql)
        
    ss.pop('edit_user_details')
    st.success('User data modified successfully.')
    get_user_permissions.clear()
    st.rerun()

def build_form(df):
    with st.expander('Add User'):
        permissions_list = list(set([perm.strip() for sublist in list(df['PERMISSIONS']) for perm in sublist.split(';')]))
        permissions_list.remove('')
        lbus = list(set(df['LBU'].dropna().tolist()))
        
        with st.form('add_user_form', True):
            email = st.text_input('Email', key='new_user_email')
            name = st.text_input('Name', key='new_user_name')
            lbu = st.pills('LBU', options=sorted(lbus), key='new_user_lbu')
            permissions = st.pills('Permissions', options=sorted(permissions_list), key='new_user_permissions', selection_mode='multi')
            custom_permissions = st.text_input('Custom Permissions (; separated)', key='new_user_permissions_text')
            submitted = st.form_submit_button('Add User')
            
            error = True
            
            if submitted:
                error = _check_form(email, name, lbu)

            if not error or 'user_details' in ss:
                _add_user(email, name, permissions, lbu, custom_permissions)
                    
def _check_form(email, name, lbu):
    error_messages = []
    if email == '':
        error_messages.append('Email is required.')
    if name == '':
        error_messages.append('Name is required.')
    if lbu is None:
        error_messages.append('LBU is required.')

    error = False
    
    if error_messages:
        for error in error_messages:
            st.error(error)
            error = True
            
    return error

def _add_user(email, name, permissions, lbu, custom_permissions):
    permissions = ';'.join(permissions + [perm.strip() for perm in custom_permissions.split(';') if perm.strip()])
        
    if 'user_details' not in ss:
        _confirm_add_user(email, name, lbu, permissions)
        return
    
    sql = f"INSERT INTO supp.streamlit_users (email, name, permissions, lbu, admin) VALUES ('{email}', '{name}', '{permissions}', '{lbu}', false);"
    
    ss.snowflake.execute(sql)
    ss.pop('user_details')
    st.success('User added successfully.')
    get_user_permissions.clear()
    st.rerun()

@st.dialog('Confirm Add User')
def _confirm_add_user(email, name, lbu, permissions):
    st.write('Confirm the following details')
    st.write(f"**Email:** {email}")
    st.write(f"**Name:** {name}")
    st.write(f"**LBU:** {lbu}")
    st.write(f"**Permissions:** {permissions}")
    
    if st.button('Confirm'):
        ss.user_details = {'email': email, 'name': name, 'lbu': lbu, 'permissions': permissions}
        st.rerun()
        
@st.dialog('Confirm Edit User')
def _confirm_edit_user(df):
    st.write('Confirm the following details')
    
    columns = list(set([col.replace('_NEW', '').replace('_OLD', '') for col in df.columns if col != 'ID']))
    
    for _, row in df.iterrows():
        st.write(f"**ID:** {row['ID']}")
        for col in columns:
            if row[col + '_NEW'] != row[col + '_OLD']:
                st.write(f"**{col}:** {row[col + '_NEW']} (was: {row[col + '_OLD']})")
            else:
                st.write(f"**{col}:** {row[col + '_NEW']}")

        st.write('---')
    
    if st.button('Confirm'):
        ss.edit_user_details = df
        st.rerun()