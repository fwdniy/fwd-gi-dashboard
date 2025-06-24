import streamlit as st
from streamlit import session_state as ss
import pandas as pd
import numpy as np
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode
import math

from utils.interface.menu import menu
from utils.snowflake.funnelweb import get_funnelweb_dates
from utils.filter.filter import build_lbu_filter, build_date_filter_buttons
from utils.snowflake.snowflake import query
from utils.interface.grid import AgGridBuilder, format_numbers, conditional_formatting
from utils.snowflake.columns import read_json_columns
from utils.interface.download import create_download_button

menu('pages/lbu_manager.py')

LBU_COLUMNS = read_json_columns('column_definitions/lbu.json')

FUND_COLUMNS = read_json_columns('column_definitions/fund.json')

SAA_COLUMNS = read_json_columns('column_definitions/saa.json')

SAA_ALLOC_COLUMNS = read_json_columns('column_definitions/saa_alloc.json')

ACCOUNT_COLUMNS = read_json_columns('column_definitions/bbg_account.json')

FWD_ASSET_TYPE_COLUMNS = read_json_columns('column_definitions/asset_type_fwd.json')

HK_ASSET_TYPE_COLUMNS = read_json_columns('column_definitions/hk_asset_type.json')

def get_data():
    if st.button('Refresh') or 'lbu_data' not in ss:
        return __refresh_data()    
    elif 'lbu_data' in ss:
        return ss['lbu_data']

def __refresh_data():
    lbu_df = __get_table_data('supp.lbu', LBU_COLUMNS)
    fund_df = __get_table_data('supp.fund', FUND_COLUMNS)    
    saa_df = __get_table_data('supp.saa', SAA_COLUMNS)
    saa_alloc_df = __get_table_data('supp.saa_alloc', SAA_ALLOC_COLUMNS)
    account_df = __get_table_data('supp.bbg_account', ACCOUNT_COLUMNS)
    fwd_asset_type_df = __get_table_data('supp.asset_type_fwd', FWD_ASSET_TYPE_COLUMNS)
    hk_asset_type_df = __get_table_data('supp.hk_asset_type', HK_ASSET_TYPE_COLUMNS)
    
    return (lbu_df, fund_df, saa_df, saa_alloc_df, account_df, fwd_asset_type_df, hk_asset_type_df)

def __get_table_data(table, columns):
    df = query(f'SELECT * FROM {table} ORDER BY id;')
    
    __check_column_definitions(df, table, columns)
    
    df = __remove_none_values(df, columns)
        
    return df

def __check_column_definitions(df, table, columns):
    df_columns = df.columns.to_list()
    
    columns = [column.name for column in columns]
    
    missing_columns = [item for item in df_columns if item not in columns]
    
    if len(missing_columns) != 0:
        st.write(f'Check if the new columns below in table \'{table}\' need additional logic! Otherwise just add them to the list...')
        st.write(missing_columns)

def __remove_none_values(df, columns):
    for index, row in df.iterrows():
        for column in columns:
            if column.datatype != 'str':
                continue
            
            if row[column.name] == 'None':
                df.loc[index, column.name] = ''
                
    return df

def display_tables():
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(['LBU', 'Fund', 'SAA', 'SAA Allocation', 'Bloomberg Accounts', 'FWD Asset Type', 'HK Asset Type'])
    
    with tab1:
        __display_table(lbu_df, 'LBU', LBU_COLUMNS)
        __upload_data('LBU', LBU_COLUMNS)
    
    with tab2:
        __display_table(fund_df, 'FUND', FUND_COLUMNS)
        __upload_data('FUND', FUND_COLUMNS, __add_to_hk_fund)
        
    with tab3:
        __display_table(saa_df, 'SAA', SAA_COLUMNS)
        __upload_data('SAA', SAA_COLUMNS)
        
    with tab4:
        __display_table(saa_alloc_df, 'SAA_ALLOC', SAA_ALLOC_COLUMNS)
        __upload_data('SAA_ALLOC', SAA_ALLOC_COLUMNS)
        
    with tab5:
        __display_table(account_df, 'BBG_ACCOUNT', ACCOUNT_COLUMNS)
        __upload_data('BBG_ACCOUNT', ACCOUNT_COLUMNS)
        
    with tab6:
        __display_table(fwd_asset_type_df, 'ASSET_TYPE_FWD', FWD_ASSET_TYPE_COLUMNS)
        __upload_data('ASSET_TYPE_FWD', FWD_ASSET_TYPE_COLUMNS)
        
    with tab7:
        __display_table(hk_asset_type_df, 'HK_ASSET_TYPE', HK_ASSET_TYPE_COLUMNS)
        __upload_data('HK_ASSET_TYPE', HK_ASSET_TYPE_COLUMNS)
    
def __filter_df_per_column_definitions(df, columns):
    df = df[[column.name for column in columns if column.type != 'legacy']]
    return df

def __display_table(df, title, columns):
    st.write(f'### {title}')
    df = __filter_df_per_column_definitions(df, columns)
    
    __build_grid(df)
    
    __build_definitions_expander(title, columns)
    
def __build_definitions_expander(title, columns):
    with st.expander(f'{title} column definitions'):
        for column in columns:
            st.write(f'**{column.name}**: ({column.type} / {column.datatype}) {column.definition}')

def __download_template(title, columns):
    df = pd.DataFrame(columns=[column.name for column in columns if column.type != 'legacy' and column.type != 'automatic'])
    create_download_button(df, f'{title.lower()}_template', f'Download {title} template')

def __upload_data(title, columns, func = None):
    
    __download_template(title, columns)
    
    uploaded_data = st.file_uploader(f'{title}_uploader', 'xlsx', label_visibility='hidden', key=f'{title}_uploader')
    
    if uploaded_data is not None:
        upload_df = pd.read_excel(uploaded_data)
        
        if len(upload_df) == 0:
            return
        
        error = __check_columns(upload_df, title, columns)
        
        if error:
            return
        
        st.write('Double check the data below, the cells can be edited')
        
        __build_grid(upload_df, True, True)
        
        __build_sql(upload_df, title, columns, func)
                
def __build_sql(df, title, columns, func = None):
    if st.button(f'Build {title} SQL'):
        df_columns = list(df.columns)
        df_columns_string = ", ".join(df_columns)
        
        sql = f'INSERT INTO supp.{title.lower()} ({df_columns_string}) VALUES '
        
        datatypes = {column.name: column.datatype for column in columns}
        
        sql_values = []
        
        for index, row in df.iterrows():
            values = []
            
            for column in df_columns:
                datatype = datatypes[column]
                                
                value = str(row[column])
                
                if value == 'nan':
                    value = ''
                if datatype == 'str':
                    value = f"'{value}'"
                elif datatype == 'date':
                    if value == '':
                        value = 'null'
                    else:
                        value = f"'{value}'"
                
                values.append(value)
            
            sql_value = f"({', '.join(values)})"
            
            sql_values.append(sql_value)
            
        sql += (", ".join(sql_values))
        sql += ";"
        
        st.write(sql)
        
        if func != None:
            func(df)
        
def __check_columns(df, title, columns):
    df_columns = list(df.columns)
    missing_columns = []
    unknown_values = {}
        
    for column in columns:
        if column.name not in df_columns and column.type == 'compulsory':
            missing_columns.append(column.name)
        elif column.sql != '' and column.split == '':
            options = query(column.sql).iloc[:, 0]
            not_in_options = df[~df[column.name].isin(options)]
            
            if len(not_in_options) > 0:
                unknown_values[column.name] = list(not_in_options[column.name].unique())
        elif column.sql != '' and column.split != '':
            options = list(query(column.sql).iloc[:, 0])
            not_in_options = []
            
            for index, row in df.iterrows():
                split = row[column.name].split(column.split)
                for item in split:
                    if item not in options:
                        not_in_options.append(item)
            
            if len(not_in_options) > 0:
                unknown_values[column.name] = list(set(not_in_options))
        elif column.options != []:
            options = column.options
            not_in_options = df[~df[column.name].isin(options)]
            
            if len(not_in_options) > 0:
                unknown_values[column.name] = list(not_in_options[column.name].unique())
    
    if len(unknown_values) > 0 or len(missing_columns) > 0:
        if len(unknown_values) > 0:
            for key, value in unknown_values.items():
                st.error(f'Unknown values for column \'{key}\': {", ".join(value)}')
        if len(missing_columns) > 0:
            st.error(f'The {title} upload data is missing the following columns: {", ".join(missing_columns)}!')
            
        return True
    
    return False
    
def __build_grid(df, detect_rows=False, editable=False):
    grid = AgGridBuilder(df, min_width=100, editable=editable)
    #grid.add_options(pivot_mode=False, group_total=None, group_expanded=0, pinned_top=[{'ID': df['ID'].max() + 1}])
    #grid.add_columns([column for column in df.columns if column not in 'ID'], False, None, editable=True, filter=True)
    
    height = 339
    
    if detect_rows:
        rows = len(df)
        
        if rows <= 10:
            height = (rows + 1) * 29 + 20
    
    grid.show_grid(height, update_mode='MODEL_CHANGED')
    #st.write(grid.grid['data'])
    #st.write(grid.grid.grid_options["pinnedTopRowData"])

def __add_cell_editing_check():
    onCellEditingStopped = """
        function onCellEditingStopped(params) {
            function isPinnedRowDataCompleted(params) {
                let colDef = params.api.getColumnDefs();
                let inputRow = params.data;
                return colDef.every((def) => inputRow[def.field]);
            }
            
            console.log(params);
        }
    """
    
    return JsCode(onCellEditingStopped)

def __add_to_hk_fund(df):
    options = query("SELECT name FROM supp.lbu WHERE lbu_group = 'HK';").iloc[:, 0]
    hk_df = df[df['LBU'].isin(options)]
    
    if len(hk_df) == 0:
        return
    
    funds = "'), ('".join(hk_df['SHORT_NAME'])
    sql = f"INSERT INTO supp.hk_fund (fund) VALUES ('{funds}');"
    st.write(sql)

(lbu_df, fund_df, saa_df, saa_alloc_df, account_df, fwd_asset_type_df, hk_asset_type_df) = ss['lbu_data'] = get_data()

display_tables()