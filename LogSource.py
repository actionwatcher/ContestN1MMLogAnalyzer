from typing import Protocol, Any
import pandas as pd
import os
import sqlite3
import helpers as hl

class LogSource(Protocol):
    def initialize(self, files: list):
        """Initialize object with files"""
        ...
    def get_contests(self, sorted_by: str, dir: str) -> pd.DataFrame:
        ...
    def get_contest_qsos(self, contest_id: int) -> pd.DataFrame:
        """Retrieve all qsos for the contest."""
        ...
    
    def get_contest_info(self, contest_id: int) -> pd.DataFrame:
        """Retrieve a specific item by ID."""
        ...


class SQLLogSource:
    def __init__(self):
        self.isvalid_ = False
        self.db_connection_ = None
        self.cursor_ = None
        self.contests_ = None
    
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()
    
    def close(self):
        if not self.db_connection_:
            return
        self.db_connection_.close()
        self.isvalid_ = False
        self.db_connection_ = None
        self.cursor_ = None
        self.contests_ = None


    def initialize(self, files: list) -> bool:
        db_path = files[0]
        if not os.path.exists(db_path):
            hl.log('ERROR', f'File not found: <{db_path}>')
            return False
        self.close()
        self.db_connection_ = sqlite3.connect(db_path)
        try:
            q = 'SELECT StartDate, ContestName from ContestInstance'
            self.db_connection_.execute(q)
            self.cursor_ = self.db_connection_.cursor()
            self.isvalid_ = True
        except sqlite3.Error as e:
            self.db_connection_ = None
            hl.log('INFO', f"Connection is not valid: {e}")
            return False
        return True

    def get_contests(self, sorted_by: str, dir: str) -> pd.DataFrame:
        """Retrieve list of available contests"""
        if not self.isvalid_:
            return {}
        if not self.contests_:
            q = f'select * from ContestInstance order by {sorted_by} {dir}'
            self.contests_ = pd.read_sql_query(q, self.db_connection_)
        elif self.sorted_by_ != sorted_by or self.sorted_dir_ != dir:
            isasc = (dir.lower() == 'asc')
            self.contests_.sort_values(by=sorted_by, ascending=isasc) 
        self.sorted_by_ = sorted_by
        self.sorted_dir_ = dir
        return self.contests_
    
    def get_contest_qsos(self, contest_id: int) -> pd.DataFrame:
        """Retrieve all qsos for the contest."""
        if not self.isvalid_:
            return {}
        q = f'select * from DXLOG where ContestNR={contest_id}'
        df = pd.read_sql_query(q, self.db_connection_)
        return df
    
    def get_contest_info(self, contest_id: int) -> pd.DataFrame:
        """Retrieve a specific item by ID."""
        if not self.isvalid_:
            hl.log('ERROR', 'No database connected')
            return pd.DataFrame()
        q = f'select * from ContestInstance where ContestNR={contest_id}'
        contest_df = pd.read_sql_query(q, self.db_connection_)
        return contest_df
    
if __name__ == "__main__":
    ds = SQLLogSource()
    if not ds.initialize(['./db/nu6n.s3db']):
        print("did not initialized the SQL object")
        exit()
    df = ds.get_contests('ContestName', 'desc')
    c = ds.get_contest_info(contest_id=df.ContestNR.iloc[-1])
    print(c)
    q = ds.get_contest_qsos(contest_id=df.ContestNR.iloc[-1])
    print(q.head(20))

