def ConnectODBC(driver, server, db, user, pw):
    import pyodbc
    con_string = 'Driver={%s};Server=%s;Database=%s;uid=%s;pwd=%s' % \
        (driver, server, db, user, pw)
    dbhandle = pyodbc.connect(con_string)
    return dbhandle

def ConnectMySQL(user, pw, dbname):
    import pymysql
    dbhandle = pymysql.connect(
        host='localhost',
        user=user,
        password=pw,
        db=dbname,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor)
    return dbhandle

class Postgres(object):
    def __init__(self, pg_user, pg_dbname):
        self.user = pg_user
        self.db = pg_dbname
        self.con = self.connect()
    def connect(self,):
        from sqlalchemy import create_engine
        return create_engine('postgresql://{}@localhost:5432/{}'.format(
            self.user, self.db))
    def execute(self, sql):
        from sqlalchemy import text
        with self.con.begin() as con:
            con.execute(text(sql))
    def read_sql(self, sql):
        import pandas as pd
        return pd.read_sql(sql, con=self.con)
    def build_update(self, schema, table, pkey_name, pkey_value, columns, values):
        """Construct SQL UPDATE statement"""
        from pydoni.vb import echo
        columns = [columns] if isinstance(columns, str) else columns
        values = [values] if isinstance(values, str) else values
        if len(columns) != len(values):
            echo("Parameters 'column' and 'value' must be of equal length", abort=True)
        lst = []
        for i in range(len(columns)):
            col = columns[i]
            val = values[i]
            if str(val).lower() in ['nan', 'n/a', 'null', '']:
                val = 'NULL'
            else:
                # Get datatype
                if isinstance(val, bool) or str(val).lower() in ['true', 'false']:
                    pass
                elif isinstance(val, int):
                    pass
                else:  # Assume string, handle quotes
                    val = val.replace("'", "''")  # Escape single quotes
                    val = val = "'" + val + "'"  # Single quote string values
            lst.append('{}={}'.format(col, val))
        # Escape quotes in primary key val
        pkey_value = pkey_value.replace("'", "''") if "'" in pkey_value else pkey_value
        pkey_value = "'" + pkey_value + "'" if isinstance(pkey_value, str) else pkey_value
        sql = "UPDATE {}.{} SET {} WHERE {} = {};"
        return sql.format(schema, table, ', '.join(str(x) for x in lst), pkey_name, pkey_value)
    def build_insert(self, schema, table, columns, values):
        """Construct SQL INSERT statement"""
        from pydoni.vb import echo
        columns = [columns] if isinstance(columns, str) else columns
        values = [values] if isinstance(values, str) else values
        if len(columns) != len(values):
            echo("Parameters 'column' and 'value' must be of equal length", abort=True)
        columns = ', '.join(columns)
        vals_cleaned = []
        for val in values:
            if str(val) in ['nan', 'N/A', 'null', '']:
                val = 'NULL'
            elif isinstance(val, bool) or str(val).lower() in ['true', 'false']:
                pass
            elif isinstance(val, int):
                pass
            else:  # Assume string, handle quotes
                val = val.replace("'", "''")  # Escape single quotes
                val = val = "'" + val + "'"  # Single quote string values
            vals_cleaned.append(val)
        values_final = ', '.join(str(x) for x in vals_cleaned)
        sql = "INSERT INTO {}.{} ({}) VALUES ({});"
        return sql.format(schema, table, columns, values_final)
    def extract_datetime(self, value):
        """Given a string with a date or datetime value, extract datetime value and
        apply any timezone adjustment if necessary"""
        import datefinder, re
        from datetime import datetime, timedelta
        def clean_value(value):
            value = str(value) if not isinstance(value, str) else value
            value = value.strip()
            return value
        value = clean_value(value)
        rgx = dict(
            date = r'^(\d{4}).(\d{2}).(\d{2}).*',
            datetime = r'^(\d{4}).(\d{2}).(\d{2})\s+(\d{2}).(\d{2}).(\d{2}).*',
            datetime_tz = r'^(\d{4}).(\d{2}).(\d{2})\s+(\d{2}).(\d{2}).(\d{2}).(\d+).(\d+).*')
        if re.search(rgx['datetime_tz'], value):
            return re.sub(rgx['datetime_tz'], r'\1-\2-\3 \4:\5:\6-\7:\8', value)
        elif re.search(rgx['datetime'], value):
            return re.sub(rgx['datetime'], r'\1-\2-\3 \4:\5:\6', value)
        elif re.search(rgx['date'], value):
            return re.sub(rgx['date'], r'\1-\2-\3', value)
        else:
            return None
