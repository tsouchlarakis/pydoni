def connect_odbc(driver, server, db, user, pw):
    """
    Establish ODBC database connection.
    
    Arguments:
        driver {str} -- driver name
        server {str} -- server name
        db {str} -- database name
        user {str} -- username
        pw {str} -- password
    
    Returns:
        [type] -- [description]
    """
    import pyodbc
    con_string = 'Driver={%s};Server=%s;Database=%s;uid=%s;pwd=%s' % \
        (driver, server, db, user, pw)
    dbhandle = pyodbc.connect(con_string)
    return dbhandle


class MySQL(object):
    """
    Interact with a MySQL database through Python.
    
    Arguments:
        user   {str} -- username for database
        pw     {str} -- password for database
        dbname {str} -- target database name
    """

    def __init__(self, user, pw, dbname):
        self.user = user
        self.pw = pw
        self.dbname = dbname
        self.dbcon = self.connect()

    def connect(self):
        """
        Connect to MySQL database.
        
        Returns:
            [pmysql] -- MySQL database connection object
        """
        import pymysql
        dbhandle = pymysql.connect(
            host        = 'localhost',
            user        = self.user,
            password    = self.pw,
            db          = self.dbname,
            charset     = 'utf8mb4',
            cursorclass = pymysql.cursors.DictCursor)
        return dbhandle


class Postgres(object):
    """
    Interact with PostgreSQL database through Python.
    
    Arguments:
        pg_user {str} -- username for database to connect
        pg_dbname {str} -- name of database to connect to
    """

    def __init__(self, pg_user, pg_dbname):
        self.dbuser = pg_user
        self.dbname = pg_dbname
        self.dbcon = self.connect()

    def connect(self):
        """
        Connect to Postgres database.
        
        Returns:
            [sqlalchemy] -- database connection
        """
        from sqlalchemy import create_engine
        return create_engine('postgresql://{}@localhost:5432/{}'.format(
            self.dbuser, self.dbname))

    def execute(self, sql, logfile=None, log_timestamp=False, progress=False):
        """
        Execute list of SQL statements or a single statement, in a transaction.
        
        Arguments:
            sql {str} -- string or list of strings of SQL to execute
        
        Keyword Arguments:
            logfile {str} -- [optional] path to log file to save executed SQL to (default: {None})
            log_timestamp {bool} if True, append timestamp to each SQL log entry
            progress {bool} -- if True, execute with `tqdm` progress bar (default: {False})
        
        Returns:
            {bool} -- always return True
        """
        import datetime
        from sqlalchemy import text
        assert isinstance(sql, str) or isinstance(sql, list)
        if logfile is not None:
            from os.path import isfile
            assert isinstance(logfile, str)
            assert isfile(logfile)
            write_log = True
        else:
            write_log = False
        
        sql = [sql] if isinstance(sql, str) else sql
        with self.dbcon.begin() as con:
            if progress:
                from tqdm import tqdm
                for stmt in tqdm(sql):
                    con.execute(text(stmt))
                    if write_log:
                        with open(logfile, 'a') as f:
                            entry = stmt + '\n'
                            if log_timestamp:
                                entry = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' ' + entry
                            f.write(entry)
                    
            else:
                for stmt in sql:
                    con.execute(text(stmt))
                    if write_log:
                        with open(logfile, 'a') as f:
                            entry = stmt + '\n'
                            if log_timestamp:
                                entry = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' ' + entry
                            f.write(entry)

        return True

    def read_sql(self, sql):
        """
        Execute SQL and read results using Pandas.
        
        Arguments:
            sql {str} -- SQL string to execute and read results from
        
        Returns::
            {pd.DataFrame} or {pd.Series}
        """
        import pandas as pd
        return pd.read_sql(sql, con=self.dbcon)

    def validate_dtype(self, schema, table, col, val):
        """
        Query database for datatype of value and validate that the Python value to
        insert to that column is compatible with the SQL datatype.
        
        Arguments:
            schema {str} -- table schema (schema of `table` parameter)
            table  {str} -- table name
            col    {str} -- column name
            val    {<any>} -- value to check against the datatype of column `col`

        Returns:
            {bool}
        """
        from pydoni.vb import echo

        # If value is 'NULL', return True automatically, as NULL may exist in a column of
        # any datatype
        if val == 'NULL':
            return True

        # Check that input value datatype matches queried table column datatype
        dtype = self.coldtypes(schema, table)[col]
        dtype_map = {
            'bigint'                     : 'int',
            'int8'                       : 'int',
            'bigserial'                  : 'int',
            'serial8'                    : 'int',
            'integer'                    : 'int',
            'int'                        : 'int',
            'int4'                       : 'int',
            'smallint'                   : 'int',
            'int2'                       : 'int',
            'double precision'           : 'float',
            'float'                      : 'float',
            'float4'                     : 'float',
            'float8'                     : 'float',
            'numeric'                    : 'float',
            'decimal'                    : 'float',
            'character'                  : 'str',
            'char'                       : 'str',
            'character varying'          : 'str',
            'varchar'                    : 'str',
            'text'                       : 'str',
            'date'                       : 'str',
            'timestamp'                  : 'str',
            'timestamp with time zone'   : 'str',
            'timestamp without time zone': 'str',
            'boolean'                    : 'bool',
            'bool'                       : 'bool'}

        # Get python equivalent of SQL column datatype according to dtype_map above
        python_dtype = [v for k, v in dtype_map.items() if dtype in k]
        if not len(python_dtype):
            echo("Column {}.{}.{} is datatype '{}' which is not in 'dtype_map' in class method Postgres.validate_dtype".format(
                schema, table, col, dtype), abort=True)
        else:
            python_dtype = python_dtype[0]

        # Prepare message (most likely will not be used)
        msg = "SQL column {}.{}.{} is type '{}' but Python value '{}' is type '{}'".format(
            schema, table, col, dtype, val, type(val).__name__)

        # Begin validation
        if python_dtype == 'bool':
            if isinstance(val, bool):
                return True
            else:
                if isinstance(val, str):
                    if val.lower() in ['t', 'true', 'f', 'false']:
                        return True
                    else:
                        echo(msg, abort=True,
                             fn_name='Postgres.validate_dtype')
                        return False
                else:
                    echo(msg, abort=True,
                         fn_name='Postgres.validate_dtype')
                    return False
        elif python_dtype == 'int':
            if isinstance(val, int):
                return True
            else:
                if isinstance(val, str):
                    try:
                        test = int(val)
                        return True
                    except:
                        echo(msg, abort=True,
                             fn_name='Postgres.build_update.validate_dtype')
                        return False
                else:
                    echo(msg, abort=True,
                         fn_name='Postgres.build_update.validate_dtype')
                    return False
        elif python_dtype == 'float':
            if isinstance(val, float):
                return True
            else:
                if val == 'inf':
                    echo(msg, abort=True,
                         fn_name='Postgres.build_update.validate_dtype')
                    return False
                try:
                    test = float(val)
                    return True
                except:
                    echo(msg, abort=True,
                         fn_name='Postgres.build_update.validate_dtype')
                    return False
        elif python_dtype == 'str':
            if isinstance(val, str):
                return True
        else:
            return True

    def build_update(self, schema, table, pkey_name, pkey_value, columns, values, validate=True):
        """
        Construct SQL UPDATE statement.
        By default, this method will:
        - Attempt to coerce a date value to proper format if the input value is detect_dtype as a date but possibly in the improper format. Ex: '2019:02:08' -> '2019-02-08'
        - Quote all values passed in as strings. This will include string values that are coercible to numerics. Ex: '5', '7.5'.
        - Do not quote all values passed in as integer or boolean values.
        - Primary key value is quoted if passed in as a string. Otherwise, not quoted.
        
        Arguments:
            schema     {str} -- schema name
            table      {str} -- table name
            pkey_name  {str} -- name of primary key in table
            pkey_value {<any>} -- value of primary key for value to update
            columns    {list} -- columns to consider in UPDATE statement
            values     {list} -- values to consider in UPDATE statement
            
        Keyword Arguments:
            validate {bool} -- if True, query column type from DB, validate that datatypes of existing column and value to insert are the same
        
        Returns:
            str
        """
        import re
        from pydoni.vb import echo
        from pydoni.classes import DoniDt

        # Get columns and values
        columns = [columns] if isinstance(columns, str) else columns
        values = [values] if isinstance(values, str) else values
        if len(columns) != len(values):
            echo("Parameters 'column' and 'value' must be of equal length", abort=True)

        # Escape quotes in primary key val
        pkey_value = self.__handle_single_quote__(pkey_value)
        lst = []
        for i in range(len(columns)):
            col = columns[i]
            val = values[i]
            if validate:
                self.validate_dtype(schema, table, col, val)
            if DoniDt(val).is_exact():
                val = DoniDt(val).extract_first(apply_tz=True)
            if str(val).lower() in ['nan', 'n/a', 'null', '']:
                val = 'NULL'
            else:
                # Get datatype
                if isinstance(val, bool) or str(val).lower() in ['true', 'false']:
                    pass
                elif isinstance(val, int) or isinstance(val, float):
                    pass
                else:  # Assume string, handle quotes
                    val = self.__handle_single_quote__(val)
            lst.append('"{}"={}'.format(col, val))
        sql = "UPDATE {}.{} SET {} WHERE {} = {};"
        return sql.format(
            schema,
            table,
            ', '.join(lst),
            '"' + pkey_name + '"',
            pkey_value)

    def build_insert(self, schema, table, columns, values, validate=False):
        """
        Construct SQL INSERT statement.
        By default, this method will:
        - Attempt to coerce a date value to proper format if the input value is detect_dtype as a date but possibly in the improper format. Ex: '2019:02:08' -> '2019-02-08'
        - Quote all values passed in as strings. This will include string values that are coercible to numerics. Ex: '5', '7.5'.
        - Do not quote all values passed in as integer or boolean values.
        - Primary key value is quoted if passed in as a string. Otherwise, not quoted.
        
        Arguments:
            schema     {str} -- schema name
            table      {str} -- table name
            pkey_name  {str} -- name of primary key in table
            pkey_value {<any>} -- value of primary key for value to update
            columns    {list} -- columns to consider in UPDATE statement
            values     {list} -- values to consider in UPDATE statement
            
        Keyword Arguments:
            validate {bool} -- if True, query column type from DB, validate that datatypes of existing column and value to insert are the same (default: {False})
        
        Returns:
            str
        """
        import re
        from pydoni.vb import echo
        from pydoni.classes import DoniDt

        # Get columns and values
        columns = [columns] if isinstance(columns, str) else columns
        values = [values] if isinstance(values, str) else values
        if len(columns) != len(values):
            echo("Parameters 'column' and 'value' must be of equal length", abort=True)
        lst = []

        for i in range(len(values)):
            val = values[i]
            col = columns[i]
            if validate:
                self.validate_dtype(schema, table, col, val)
            if DoniDt(val).is_exact():
                val = DoniDt(val).extract_first(apply_tz=True)
            if str(val) in ['nan', 'N/A', 'null', '']:
                val = 'NULL'
            elif isinstance(val, bool) or str(val).lower() in ['true', 'false']:
                pass
            elif isinstance(val, int) or isinstance(val, float):
                pass
            else:  # Assume string, handle quotes
                val = self.__handle_single_quote__(val)
            lst.append(val)

        values_final = ', '.join(str(x) for x in lst)
        values_final = values_final.replace("'NULL'", 'NULL')
        columns = ', '.join(['"' + x + '"' for x in columns])
        sql = "INSERT INTO {}.{} ({}) VALUES ({});"
        return sql.format(schema, table, columns, values_final)

    def build_delete(self, schema, table, pkey_name, pkey_value):
        """
        Construct SQL DELETE FROM statement.
        
        Arguments:
            schema     {str} -- schema name
            table      {str} -- table name
            pkey_name  {str} -- name of primary key in table
            pkey_value {<any>} -- value of primary key for value to update
        
        Returns:
            str
        """
        pkey_value = self.__handle_single_quote__(pkey_value)
        return "DELETE FROM {}.{} WHERE {} = {};".format(schema, table, pkey_name, pkey_value)

    def colnames(self, schema, table):
        """
        Get column names of table as a list.
        
        Arguments:
            schema {str} -- schema name
            table  {str} -- table name
        
        Returns:
            list
        """
        column_sql = "SELECT column_name FROM information_schema.columns WHERE table_schema = '{}' AND table_name = '{}'"
        return self.read_sql(column_sql.format(schema, table)).squeeze().tolist()

    def coldtypes(self, schema, table):
        """
        Get column datatypes of table as a dictionary.
        
        Arguments:
            schema {str} -- schema name
            table  {str} -- table name
        
        Returns:
            {dict} -- dictionary of key:value pairs of column_name:column_datatype
        """
        import pandas as pd
        dtype = self.read_sql("""
            SELECT column_name, data_type
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE table_schema = '{}'
                AND table_name = '{}'
            """.format(schema, table)).squeeze()
        return dtype.set_index('column_name')['data_type'].to_dict()

    def read_table(self, schema, table):
        """
        Read entire SQL table.
        
        Arguments:
            schema {str} -- schema name to query from
            table {str} -- table name to query from
        
        Returns:
            {pd.DataFrame} or {pd.Series} -- will only return a Series if table has one column, else a DataFrame
        """
        return self.read_sql("SELECT * FROM {}.{}".format(schema, table))

    def dump(self, backup_dir_abspath):
        """
        Execute pg_dump command on connected database. Create .sql backup file.
        
        Arguments:
            backup_dir_abspath {str} -- absolute path to directory to dump Postgres database to
        """
        import subprocess
        import os
        backup_dir_abspath = os.path.expanduser(backup_dir_abspath)
        cmd = 'pg_dump {} > "{}/{}.sql"'.format(
            self.dbname, backup_dir_abspath, self.dbname)
        out = subprocess.call(cmd, shell=True)

    def dump_tables(self, backup_dir_abspath, sep=',', coerce_csv=False):
        """
        Dump each table in database to a textfile with specified separator.
        https://stackoverflow.com/questions/17463299/export-database-into-csv-file?answertab=oldest#tab-top
        
        Arguments:
            backup_dir_abspath {str} -- absolute path to directory to dump Postgres database to
            sep {str} -- output datafile separator, defaults to comma
            coerce_csv {bool} -- if True, read in each file outputted, then write as a quoted CSV
        """
        
        db_to_csv = """
        CREATE OR REPLACE FUNCTION db_to_csv(path TEXT) RETURNS void AS $$
        DECLARE
           tables RECORD;
           statement TEXT;
        BEGIN
        FOR tables IN 
           SELECT (table_schema || '.' || table_name) AS schema_table
           FROM information_schema.tables t
               INNER JOIN information_schema.schemata s ON s.schema_name = t.table_schema 
           WHERE t.table_schema NOT IN ('pg_catalog', 'information_schema')
               AND t.table_type NOT IN ('VIEW')
           ORDER BY schema_table
        LOOP
           statement := 'COPY ' || tables.schema_table || ' TO ''' || path || '/' || tables.schema_table || '.csv' ||''' DELIMITER ''{}'' CSV HEADER';
           EXECUTE statement;
        END LOOP;
        RETURN;  
        END;
        $$ LANGUAGE plpgsql;""".format(sep)
        self.execute(db_to_csv)

        # Execute function, dumping each table to a textfile.
        # Function is used as follows: SELECT db_to_csv('/path/to/dump/destination');
        self.execute("SELECT db_to_csv('{}')".format(backup_dir_abspath))

        # If coerce_csv is True, read in each file outputted, then write as a quoted CSV.
        # Replace 'sep' if different from ',' and quote each text field.
        if coerce_csv:
            if sep != ',':
                import os
                import csv
                import pandas as pd
                from pydoni.os import listfiles
                wd = os.getcwd()
                os.chdir(backup_dir_abspath)

                # Get tables that were dumped and build filenames
                get_dumped_tables = """SELECT (table_schema || '.' || table_name) AS schema_table
                FROM information_schema.tables t
                   INNER JOIN information_schema.schemata s ON s.schema_name = t.table_schema 
                WHERE t.table_schema NOT IN ('pg_catalog', 'information_schema')
                   AND t.table_type NOT IN ('VIEW')
                ORDER BY schema_table"""
                dumped_tables = self.read_sql(get_dumped_tables).squeeze()
                if isinstance(dumped_tables, pd.Series):
                    dumped_tables = dumped_tables.tolist()
                elif isinstance(dumped_tables, str):
                    dumped_tables = [dumped_tables]
                dumped_tables = [x + '.csv' for x in dumped_tables]

                # Read in each table and overwrite file with comma sep and quoted text values
                for csvfile in dumped_tables:
                    pd.read_csv(csvfile, sep=sep).to_csv(
                        csvfile, quoting=csv.QUOTE_NONNUMERIC, index=False)
                os.chdir(wd)

    def __handle_single_quote__(self, val):
        """
        Escape single quotes and put single quotes around value if string value.
        
        Arguments:
            val {<any>} -- if `type(val)` is `str`, surround with single quotes, used in building SQL
        
        Returns:
            {`type(val)`}
        """
        if isinstance(val, str):
            val = val.replace("'", "''")
            val = "'" + val + "'"
        return val
