import streamlit as st
from streamlit import session_state as ss

@st.cache_data(ttl=3600, show_spinner=False)
def get_ratings_mapping(agencies):
    sql = """
        SELECT 
            rating, 
            index 
        FROM 
            supp.ratings_ladder;
    """
    rating_ladder_df = ss.snowflake.query(sql)

    rating_ladder = dict(zip(rating_ladder_df['RATING'], rating_ladder_df['INDEX']))
    
    sql = """
        SELECT 
            agency, 
            rating, 
            equivalent_rating 
        FROM 
            supp.ratings_mapping;
    """
    rating_mapping_df = ss.snowflake.query(sql)
    
    agency_mappings = {}
    
    for agency in rating_mapping_df['AGENCY'].unique():
        if agency not in agencies:
            continue
        
        agency_df = rating_mapping_df[(rating_mapping_df['AGENCY'] == agency)].reset_index(drop=True)
        
        stop_index = agency_df[agency_df['EQUIVALENT_RATING'] == 'Default'].index[0] + 1
        agency_mapping_df = agency_df.iloc[:stop_index]
        agency_mapping = dict(zip(agency_mapping_df['RATING'], agency_mapping_df['EQUIVALENT_RATING'].map(rating_ladder)))
        agency_mappings[agency] = agency_mapping
    
    return agency_mappings

@st.cache_data(ttl=3600, show_spinner=False)
def get_ratings_index():    
    sql = f"""
        SELECT 
            id,
            rating
        FROM 
            supp.ratings_ladder;
    """
    df = ss.snowflake.query(sql)
    
    return df