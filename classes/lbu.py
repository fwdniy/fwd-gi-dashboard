import streamlit_antd_components as sac

class LbuGroup:
    def __init__(self, row):
        self.code = row["LBU_GROUP"]
        self.name = row["GROUP_NAME"]
        self.lbus = [Lbu(row)]
    
    def add(self, row):
        lbu_code = row["BLOOMBERG_NAME"]
        index = next((i for i, group in enumerate(self.lbus) if group.code == lbu_code), -1)

        if index == -1:
            self.lbus.append(Lbu(row))
        else:
            self.lbus[index].add(row)

    def build_cas_item(self):
        children = [lbu.casItem for lbu in self.lbus]
        self.casItem = sac.CasItem(self.name, children=children)

class Lbu:
    def __init__(self, row):
        self.code = row["BLOOMBERG_NAME"]
        self.name = row["LBU"]
        self.fundTypes = [FundType(row)]

    def add(self, row):
        fund_type = row["TYPE"]
        index = next((i for i, fundType in enumerate(self.fundTypes) if fundType.type == fund_type), -1)

        if index == -1:
            self.fundTypes.append(FundType(row))
        else:
            self.fundTypes[index].add(row)

    def build_cas_item(self):
        children = [type.casItem for type in self.fundTypes]
        self.casItem = sac.CasItem(self.name, children=children)

class FundType:
    def __init__(self, row):
        self.type = row["TYPE"]
        self.funds = [Fund(row)]

    def add(self, row):
        self.funds.append(Fund(row))

    def build_cas_item(self):
        children = [sac.CasItem(fund.code) for fund in self.funds]
        self.casItem = sac.CasItem(self.type, children=children)
        
class Fund:
    def __init__(self, row):
        self.code = row["SHORT_NAME"]