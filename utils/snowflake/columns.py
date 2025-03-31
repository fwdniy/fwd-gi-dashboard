import json

def read_json_columns(path):
    with open(path, 'r') as json_file:
        data = json.load(json_file)
        
        return [SnowflakeColumn(**item) for item in data]

class SnowflakeColumn:
    def __init__(self, name, type, datatype, definition, options=[], sql='', split=''):
        self.name = name
        self.type = type
        self.datatype = datatype
        self.definition = definition
        self.options = options
        self.sql = sql
        self.split = split