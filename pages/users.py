import streamlit as st
from utils.interface.menu import menu
from streamlit_js_eval import streamlit_js_eval
from streamlit import session_state as ss
from utils.interface.grid import AgGridBuilder
from utils.interface.menu import get_permissions
from utils.snowflake.snowflake import non_query

menu('pages/users.py')

df = ss['streamlit_permissions']
df['ID'] = df['ID'].astype('int64')

if 'reset' not in ss:
    ss['reset'] = False

grid = AgGridBuilder(df)
grid.add_options(pivot_mode=False, group_total=False, cell_value_change='onCellValueChanged', pinned_top=[{'ADMIN': False}])
grid.add_columns(['EMAIL', 'NAME', 'PERMISSIONS'], False, None, editable=not ss['reset'])
grid.show_grid(400, reload_data=ss['reset'])

st.write('To add a new user, please add the email, name and permissions in the top row.')
st.write('To edit, please double click any email, name or permissions cell.')

if ss['reset']:
    ss['reset'] = False
    st.rerun()

updated_df = grid.grid["data"]
addData = grid.grid.grid_options["pinnedTopRowData"]

differences = {}

for i in range(len(df)):
    row1 = df.iloc[i]
    row2 = updated_df.iloc[i]
    
    row_differences = {}
    
    if row1['EMAIL'] != row2['EMAIL']:
        row_differences['EMAIL'] = [row1['EMAIL'], row2['EMAIL']]
    if row1['NAME'] != row2['NAME']:
        row_differences['NAME'] = [row1['NAME'], row2['NAME']]
    if row1['PERMISSIONS'] != row2['PERMISSIONS']:
        row_differences['PERMISSIONS'] = [row1['PERMISSIONS'], row2['PERMISSIONS']]
        
    if len(row_differences) != 0:
        differences[row1['ID']] = row_differences
        
if len(differences) != 0:
    st.write('The changes to be made are:')
    
    for key, value in differences.items():
        for key2, value2 in value.items():
            st.write(f' - ID {key}: \'{key2}\' change from {value2[0]} to {value2[1]}')
    
    if st.button('Apply changes'):
        
        for key, value in differences.items():
            for key2, value2 in value.items():
                non_query(f'UPDATE supp.streamlit_users SET {key2} = \'{value2[1]}\' WHERE id = {key}')
        
        get_permissions(True)
        st.rerun()

if len(addData[0]) == 4:
    if st.button('Add User'):
        non_query(f'INSERT INTO supp.streamlit_users (EMAIL, NAME, PERMISSIONS, ADMIN) VALUES (\'{addData[0]["EMAIL"]}\', \'{addData[0]["NAME"]}\', \'{addData[0]["PERMISSIONS"]}\', {addData[0]["ADMIN"]})')
        ss['reset'] = True
        get_permissions(True)
        st.rerun()