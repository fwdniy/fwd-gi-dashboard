import streamlit as st
from tools import filter

columns = ['LBU_GROUP', 'LBU_CODE', 'L1_ASSET_TYPE', 
               'L2_ASSET_TYPE', 'L3_ASSET_TYPE', 'L4_ASSET_TYPE', 
               'FINAL_RATING', 'INDUSTRY_SECTOR', 'INDUSTRY_GROUP', 
               'INDUSTRY', 'MANAGER']
    
default_columns = ['LBU_GROUP', 'L1_ASSET_TYPE']

values = ['CLEAN_MV_USD', 'NET_MV']

default_values = ['NET_MV']

display_names = {'CLOSING_DATE': 'Closing Date', 'LBU_GROUP': 'LBU Group', 'LBU_CODE': 'LBU Code', 'L1_ASSET_TYPE': 'L1 Asset Type', 
            'L2_ASSET_TYPE': 'L2 Asset Type', 'L3_ASSET_TYPE': 'L3 Asset Type', 'L4_ASSET_TYPE': 'L4 Asset Type', 
            'FINAL_RATING': 'Final Rating', 'INDUSTRY_SECTOR': 'Industry Sector', 'INDUSTRY_GROUP': 'Industry Group', 
            'INDUSTRY': 'Industry', 'MANAGER': 'Manager', 'CLEAN_MV_USD': 'Clean MV', 'NET_MV': 'Net MV'}

filter.build_custom_cascader([display_names[column] for column in columns], [display_names[column] for column in default_columns], 'Columns', 'breakdown_columns')
filter.build_custom_cascader([display_names[column] for column in values], [display_names[column] for column in default_values], 'Values', 'breakdown_values')