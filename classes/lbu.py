import pandas as pd
from utils.snowflake.snowflake import query

class Fund:
    name: str
    type: str

    def __init__(self, df):
        self.name = df['SHORT_NAME'][0]
        self.type = df['TYPE'][0]

    def build_tree_data(self):
        data = {'label': self.name, 'value': f'f:{self.name}'}
        return data

class Lbu:
    name: str
    code: str
    funds: list[Fund] = []

    def __init__(self, df, entity=False):
        self.name = df['LBU'][0]
        self.code = df['BLOOMBERG_NAME'][0]
        self.funds = []

        if entity:
            self.code = self.name = df['SUB_LBU'][0]

        unique_funds = df['SHORT_NAME'].unique()

        for fund in unique_funds:
            self.funds.append(Fund(df[df['SHORT_NAME'] == fund].reset_index(drop=True)))
    
    def build_tree_data(self):
        data = {'label': self.name, 'value': f'l:{self.code}'}

        children = []

        fund_types = list(set([fund.type for fund in self.funds]))

        for type in fund_types:
            type_children = []

            for fund in self.funds:
                if fund.type == type:
                    type_children.append(fund.build_tree_data())
            
            children.append({'label': type, 'value': f't:{self.code}/{type}', 'children': type_children})

        data['children'] = children

        return data

class LbuGroup:
    name: str
    code: str
    lbus: list[Lbu] = []
    entities: list[Lbu] = []

    def __init__(self, df):
        self.name = df['GROUP_NAME'][0]
        self.code = df['LBU_GROUP'][0]
        self.lbus = []
        self.entities = []
        unique_lbus = df['LBU'].unique()

        for lbu in unique_lbus:
            self.lbus.append(Lbu(df[df['LBU'] == lbu].reset_index(drop=True)))

        entities = df['SUB_LBU'].unique()

        for entity in entities:
            self.entities.append(Lbu(df[df['SUB_LBU'] == entity].reset_index(drop=True), True))
    
    def build_tree_data(self, entities: bool = False):
        data = {'label': self.name, 'value': f'lg:{self.code}'}

        children = []

        if entities:
            lbus = self.entities
        else:
            lbus = self.lbus 
        
        for lbu in lbus:
            children.append(lbu.build_tree_data())

        data['children'] = children

        return data
    
    def build_entity_mapping(self):
        entity_mapping = {}

        for entity in self.entities:
            for fund in entity.funds:
                entity_mapping[fund.name] = entity.name

        return entity_mapping

def build_lbu() -> list[LbuGroup]:
    query_string: str = 'SELECT l.group_name, f.lbu, f.type, f.short_name, l.bloomberg_name, l.lbu_group, f.sub_lbu FROM supp.fund AS f LEFT JOIN supp.lbu AS l ON l.name = f.lbu WHERE l.bloomberg_name <> \'LT\' ORDER BY group_name, lbu, sub_lbu, type, short_name;'
    df: pd.DataFrame = query(query_string)

    groups = df['GROUP_NAME'].unique()

    lbu_groups = []

    for group in groups:
        lbu_groups.append(LbuGroup(df[df['GROUP_NAME'] == group].reset_index(drop=True)))

    return lbu_groups