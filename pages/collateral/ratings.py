def convert_csa_valuation_ratings(csa_valuations, agencies, agency_names):
    agency_columns = {agency: [item for item in list(csa_valuations.columns) if agency_names[agency] in item] for agency in agencies.keys()}
    
    for index, row in csa_valuations.iterrows():
        for agency, mapping in agencies.items():
            columns = agency_columns[agency]
            
            for column in columns:
                if row[column] == '':
                    continue
                
                csa_valuations.loc[index, column] = agencies[agency][row[column]]
    
    return csa_valuations