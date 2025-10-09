import snowflake.connector
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

class SnowflakeClient:
    def __init__(self, config: dict):
        
        private_key_str = config["private_key"]
    
        private_key = serialization.load_pem_private_key(
            private_key_str.encode(),
            password=None,
            backend=default_backend()
        )
        
        self.conn = snowflake.connector.connect(
            user=config.get("user"),
            account=config.get("account"),
            host=config.get("host"),
            role=config.get("role"),
            warehouse=config.get("warehouse"),
            database=config.get("database"),
            schema=config.get("schema"),
            authenticator=config.get("authenticator"),
            private_key=private_key
        )
    
    def query(self, sql: str, sort_columns: list = []):
        with self.conn.cursor() as cur:
            cur.execute(sql)
            
            df = cur.fetch_pandas_all()

            if sort_columns != []:
                self._convert_columns(df, cur).sort_values(by=sort_columns)
            else:
                self._convert_columns(df, cur)
                
            return df
    
    def _get_schema(self, cur):
        schema = cur.description
        columns = {}

        for column in schema:
            dtype = column[1]
            if dtype == 0:
                columns[column[0]] = float
            elif dtype == 2:
                columns[column[0]] = str
            elif dtype in [3, 8]:
                columns[column[0]] = datetime
            elif dtype == 6:
                columns[column[0]] = ZoneInfo
            elif dtype == 13:
                columns[column[0]] = bool
            else:
                print(f"Unknown datatype for column '{column[0]}'")

        return columns

    def _convert_columns(self, df, cur):
        columns = self._get_schema(cur)
        
        for key, dtype in columns.items():
            if dtype == datetime:
                df[key] = pd.to_datetime(df[key])
            elif dtype == ZoneInfo:
                df[key] = pd.to_datetime(df[key]).dt.tz_convert('Asia/Hong_Kong').dt.tz_localize(None)
            else:
                df[key] = df[key].astype(dtype)
        return df

        
    def execute(self, sql: str):
        with self.conn.cursor() as cur:
            cur.execute(sql)