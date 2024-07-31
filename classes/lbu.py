import streamlit_antd_components as sac

class LbuGroup:
    def __init__(self, row):
        self.lbu_group_code = row["LBU_GROUP"]
        self.lbu_group_name = row["GROUP_NAME"]
        self.lbus = [Lbu(row)]
    
    def add(self, row):
        lbu_code = row["BLOOMBERG_NAME"]
        index = next((i for i, group in enumerate(self.lbus) if group.lbu_code == lbu_code), -1)

        if index == -1:
            self.lbus.append(Lbu(row))
        else:
            self.lbus[index].add(row)

    def build_cas_item(self):
        children = [lbu.casItem for lbu in self.lbus]
        self.casItem = sac.CasItem(self.lbu_group_name, children=children)

    def filter(self, df, mapping):
        df.loc[df['LBU_FILTER'] == False, 'LBU_FILTER'] = df[mapping['LBU_GROUP']] == self.lbu_group_code
    
    def lower_level_exists(self, selections):
        for selection in selections:
            if selection == self:
                continue

            if selection.lbu_group_code == self.lbu_group_code:
                return True
        
        return False

class Lbu:
    def __init__(self, row):
        self.lbu_group_code = row["LBU_GROUP"]
        self.lbu_group_name = row["GROUP_NAME"]
        self.lbu_code = row["BLOOMBERG_NAME"]
        self.lbu_name = row["LBU"]
        self.fundTypes = [FundType(row)]

    def add(self, row):
        fund_type = row["TYPE"]
        index = next((i for i, fundType in enumerate(self.fundTypes) if fundType.fund_type == fund_type), -1)

        if index == -1:
            self.fundTypes.append(FundType(row))
        else:
            self.fundTypes[index].add(row)

    def build_cas_item(self):
        children = [type.casItem for type in self.fundTypes]
        self.casItem = sac.CasItem(self.lbu_name, children=children)

    def filter(self, df, mapping):
        df.loc[df['LBU_FILTER'] == False, 'LBU_FILTER'] = (df[mapping['LBU_GROUP']] == self.lbu_group_code) & (df[mapping['LBU']] == self.lbu_code)
    
    def lower_level_exists(self, selections):
        for selection in selections:
            if selection == self or type(selection) == LbuGroup:
                continue

            if selection.lbu_group_code == self.lbu_group_code and selection.lbu_code == self.lbu_code:
                return True
        
        return False

class FundType:
    def __init__(self, row):
        self.lbu_group_code = row["LBU_GROUP"]
        self.lbu_group_name = row["GROUP_NAME"]
        self.lbu_code = row["BLOOMBERG_NAME"]
        self.lbu_name = row["LBU"]
        self.fund_type = row["TYPE"]
        self.funds = [Fund(row)]

    def add(self, row):
        self.funds.append(Fund(row))

    def build_cas_item(self):
        children = [sac.CasItem(fund.fund_code) for fund in self.funds]
        self.casItem = sac.CasItem(self.fund_type, children=children)

    def filter(self, df, mapping):
        df.loc[df['LBU_FILTER'] == False, 'LBU_FILTER'] = (df[mapping['LBU_GROUP']] == self.lbu_group_code) & (df[mapping['LBU']] == self.lbu_code) & (df[mapping['FUND_TYPE']] == self.fund_type)
    
    def lower_level_exists(self, selections):
        for selection in selections:
            if selection == self or type(selection) == LbuGroup or type(selection) == Lbu:
                continue

            if selection.lbu_group_code == self.lbu_group_code and selection.lbu_code == self.lbu_code and selection.fund_type == self.fund_type:
                return True
        
        return False
        
class Fund:
    def __init__(self, row):
        self.lbu_group_code = row["LBU_GROUP"]
        self.lbu_group_name = row["GROUP_NAME"]
        self.lbu_code = row["BLOOMBERG_NAME"]
        self.lbu_name = row["LBU"]
        self.fund_type = row["TYPE"]
        self.fund_code = row["SHORT_NAME"]
    
    def filter(self, df, mapping):
        df.loc[df['LBU_FILTER'] == False, 'LBU_FILTER'] = (df[mapping['LBU_GROUP']] == self.lbu_group_code) & (df[mapping['LBU']] == self.lbu_code) & (df[mapping['FUND_TYPE']] == self.fund_type) & (df[mapping['FUND']] == self.fund_code)
    
    def lower_level_exists(self, selections):
        return False