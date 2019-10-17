import re
import os
import csv
import click
# import pyodbc
import pymysql
import datetime
import subprocess
import pandas as pd
from os.path import isfile, isdir, expanduser
from os import getcwd, chdir
from sqlalchemy import create_engine, text
from tqdm import tqdm


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
            {pmysql} -- MySQL database connection object
        """
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
            {sqlalchemy} -- database connection
        """
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
        assert isinstance(sql, str) or isinstance(sql, list)
        if logfile is not None:
            assert isinstance(logfile, str)
            assert isfile(logfile)
            write_log = True
        else:
            write_log = False
        
        sql = [sql] if isinstance(sql, str) else sql
        with self.dbcon.begin() as con:
            if progress:
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

    def read_sql(self, sql, simplify=True):
        """
        Execute SQL and read results using Pandas.
        
        Arguments:
            sql {str} -- SQL string to execute and read results from

        Keyword Arguments:
            simplify {bool} -- if True, return pd.Series if pd.DataFrame returned only has 1 column (default: {True})
        
        Returns::
            {pd.DataFrame} or {pd.Series}
        """
        res = pd.read_sql(sql, con=self.dbcon)
        if res.shape[1] == 1:
            if simplify:
                res = res.iloc[:, 0]
        return res

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

    def build_update(self, schema, table, pkey_name, pkey_value, columns, values, validate=True, newlines=False):
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
            newlines {bool} -- if True, add newlines to query string (default: {False})
        
        Returns:
            {str}
        """

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
                else:
                    # Assume string, handle quotes
                    val = self.__handle_single_quote__(val)
            if newlines:
                lst.append('\n    "{}"={}'.format(col, val))
            else:
                lst.append('"{}"={}'.format(col, val))

        if newlines:
            lst[0] = lst[0].strip()
            sql = "UPDATE {}.{}\nSET {}\nWHERE {} = {};"
        else:
            sql = "UPDATE {}.{} SET {} WHERE {} = {};"
        
        return sql.format(
            schema,
            table,
            ', '.join(lst),
            '"' + pkey_name + '"',
            pkey_value)

    def build_insert(self, schema, table, columns, values, validate=False, newlines=False):
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
            newlines {bool} -- if True, add newlines to query string (default: {False})
        
        Returns:
            {str}
        """

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
            # if DoniDt(val).is_exact():
            #     val = DoniDt(val).extract_first(apply_tz=True)
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
        
        if newlines:
            sql = "INSERT INTO {}.{} ({})\nVALUES ({});"
        else:
            sql = "INSERT INTO {}.{} ({}) VALUES ({});"
        
        return sql.format(schema, table, columns, values_final)

    def build_delete(self, schema, table, pkey_name, pkey_value, newlines=False):
        """
        Construct SQL DELETE FROM statement.
        
        Arguments:
            schema     {str} -- schema name
            table      {str} -- table name
            pkey_name  {str} -- name of primary key in table
            pkey_value {<any>} -- value of primary key for value to update

        Keyword Arguments:
            newlines {bool} -- if True, add newlines to query string (default: {False})
        
        Returns:
            {str}
        """
        pkey_value = self.__handle_single_quote__(pkey_value)
        if newlines:
            return "DELETE FROM {}.{}\nWHERE {} = {};".format(schema, table, pkey_name, pkey_value)
        else:
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
            table {str} -- table name
        
        Returns:
            {dict} -- dictionary of key:value pairs of column_name:column_datatype
        """
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
        backup_dir_abspath = expanduser(backup_dir_abspath)
        assert isdir(backup_dir_abspath)

        cmd = '/usr/local/bin/pg_dump {} > "{}/{}.sql"'.format(
            self.dbname, backup_dir_abspath, self.dbname)
        syscmd(cmd)

    def dump_tables(self, backup_dir_abspath, sep=',', coerce_csv=False):
        """
        Dump each table in database to a textfile with specified separator.
        
        Arguments:
            backup_dir_abspath {str} -- absolute path to directory to dump Postgres database to
            sep {str} -- output datafile separator, defaults to comma
            coerce_csv {bool} -- if True, read in each file outputted, then write as a quoted CSV

        Source:
            https://stackoverflow.com/questions/17463299/export-database-into-csv-file?answertab=oldest#tab-top
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
                wd = getcwd()
                chdir(backup_dir_abspath)

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
                chdir(wd)

    def __handle_single_quote__(self, val):
        """
        Escape single quotes and put single quotes around value if string value.
        
        Arguments:
            val {<any>} -- if `type(val)` is `str`, surround with single quotes, used in building SQL
        
        Returns:
            {`type(val)`}
        """
        if type(val) not in [bool, int, float]:
            val = str(val).replace("'", "''")
            val = "'" + val + "'"
        return val


def colorize_sql(sql):
    """
    Colorize SQL by detecting keywords.
    
    Arguments:
        sql {str} -- SQL string to colorize

    Returns:
        {str}
    """

    keywords = dict(
        logical = ['true', 'false'],
        sql = ['ABORT', 'ABS', 'ABSOLUTE', 'ACCESS', 'ACTION', 'ADA', 'ADD', 'ADMIN', 'AFTER', 'AGGREGATE', 'ALIAS', 'ALL', 'ALLOCATE', 'ALSO', 'ALTER', 'ALWAYS', 'ANALYSE', 'ANALYZE', 'AND', 'ANY', 'ARE', 'ARRAY', 'AS', 'ASC', 'ASENSITIVE', 'ASSERTION', 'ASSIGNMENT', 'ASYMMETRIC', 'AT', 'ATOMIC', 'ATTRIBUTE', 'ATTRIBUTES', 'AUTHORIZATION', 'AVG', 'BACKWARD', 'BEFORE', 'BEGIN', 'BERNOULLI', 'BETWEEN', 'BIGINT', 'BINARY', 'BIT', 'BITVAR', 'BIT_LENGTH', 'BLOB', 'BOOLEAN', 'BOTH', 'BREADTH', 'BY', 'C', 'CACHE', 'CALL', 'CALLED', 'CARDINALITY', 'CASCADE', 'CASCADED', 'CASE', 'CAST', 'CATALOG', 'CATALOG_NAME', 'CEIL', 'CEILING', 'CHAIN', 'CHAR', 'CHARACTER', 'CHARACTERISTICS', 'CHARACTERS', 'CHARACTER_LENGTH', 'CHARACTER_SET_CATALOG', 'CHARACTER_SET_NAME', 'CHARACTER_SET_SCHEMA', 'CHAR_LENGTH', 'CHECK', 'CHECKED', 'CHECKPOINT', 'CLASS', 'CLASS_ORIGIN', 'CLOB', 'CLOSE', 'CLUSTER', 'COALESCE', 'COBOL', 'COLLATE', 'COLLATION', 'COLLATION_CATALOG', 'COLLATION_NAME', 'COLLATION_SCHEMA', 'COLLECT', 'COLUMN', 'COLUMN_NAME', 'COMMAND_FUNCTION', 'COMMAND_FUNCTION_CODE', 'COMMENT', 'COMMIT', 'COMMITTED', 'COMPLETION', 'CONDITION', 'CONDITION_NUMBER', 'CONNECT', 'CONNECTION', 'CONNECTION_NAME', 'CONSTRAINT', 'CONSTRAINTS', 'CONSTRAINT_CATALOG', 'CONSTRAINT_NAME', 'CONSTRAINT_SCHEMA', 'CONSTRUCTOR', 'CONTAINS', 'CONTINUE', 'CONVERSION', 'CONVERT', 'COPY', 'CORR', 'CORRESPONDING', 'COUNT', 'COVAR_POP', 'COVAR_SAMP', 'CREATE', 'CREATEDB', 'CREATEROLE', 'CREATEUSER', 'CROSS', 'CSV', 'CUBE', 'CUME_DIST', 'CURRENT', 'CURRENT_DATE', 'CURRENT_DEFAULT_TRANSFORM_GROUP', 'CURRENT_PATH', 'CURRENT_ROLE', 'CURRENT_TIME', 'CURRENT_TIMESTAMP', 'CURRENT_TRANSFORM_GROUP_FOR_TYPE', 'CURRENT_USER', 'CURSOR', 'CURSOR_NAME', 'CYCLE', 'DATA', 'DATABASE', 'DATE', 'DATETIME_INTERVAL_CODE', 'DATETIME_INTERVAL_PRECISION', 'DAY', 'DEALLOCATE', 'DEC', 'DECIMAL', 'DECLARE', 'DEFAULT', 'DEFAULTS', 'DEFERRABLE', 'DEFERRED', 'DEFINED', 'DEFINER', 'DEGREE', 'DELETE', 'DELIMITER', 'DELIMITERS', 'DENSE_RANK', 'DEPTH', 'DEREF', 'DERIVED', 'DESC', 'DESCRIBE', 'DESCRIPTOR', 'DESTROY', 'DESTRUCTOR', 'DETERMINISTIC', 'DIAGNOSTICS', 'DICTIONARY', 'DISABLE', 'DISCONNECT', 'DISPATCH', 'DISTINCT', 'DO', 'DOMAIN', 'DOUBLE', 'DROP', 'DYNAMIC', 'DYNAMIC_FUNCTION', 'DYNAMIC_FUNCTION_CODE', 'EACH', 'ELEMENT', 'ELSE', 'ENABLE', 'ENCODING', 'ENCRYPTED', 'END', 'END-EXEC', 'EQUALS', 'ESCAPE', 'EVERY', 'EXCEPT', 'EXCEPTION', 'EXCLUDE', 'EXCLUDING', 'EXCLUSIVE', 'EXEC', 'EXECUTE', 'EXISTING', 'EXISTS', 'EXP', 'EXPLAIN', 'EXTERNAL', 'EXTRACT', 'FALSE', 'FETCH', 'FILTER', 'FINAL', 'FIRST', 'FLOAT', 'FLOOR', 'FOLLOWING', 'FOR', 'FORCE', 'FOREIGN', 'FORTRAN', 'FORWARD', 'FOUND', 'FREE', 'FREEZE', 'FROM', 'FULL', 'FUNCTION', 'FUSION', 'G', 'GENERAL', 'GENERATED', 'GET', 'GLOBAL', 'GO', 'GOTO', 'GRANT', 'GRANTED', 'GREATEST', 'GROUP', 'GROUPING', 'HANDLER', 'HAVING', 'HEADER', 'HIERARCHY', 'HOLD', 'HOST', 'HOUR', 'IDENTITY', 'IGNORE', 'ILIKE', 'IMMEDIATE', 'IMMUTABLE', 'IMPLEMENTATION', 'IMPLICIT', 'IN', 'INCLUDING', 'INCREMENT', 'INDEX', 'INDICATOR', 'INFIX', 'INHERIT', 'INHERITS', 'INITIALIZE', 'INITIALLY', 'INNER', 'INOUT', 'INPUT', 'INSENSITIVE', 'INSERT', 'INSTANCE', 'INSTANTIABLE', 'INSTEAD', 'INT', 'INTEGER', 'INTERSECT', 'INTERSECTION', 'INTERVAL', 'INTO', 'INVOKER', 'IS', 'ISNULL', 'ISOLATION', 'ITERATE', 'JOIN', 'K', 'KEY', 'KEY_MEMBER', 'KEY_TYPE', 'LANCOMPILER', 'LANGUAGE', 'LARGE', 'LAST', 'LATERAL', 'LEADING', 'LEAST', 'LEFT', 'LENGTH', 'LESS', 'LEVEL', 'LIKE', 'LIMIT', 'LISTEN', 'LN', 'LOAD', 'LOCAL', 'LOCALTIME', 'LOCALTIMESTAMP', 'LOCATION', 'LOCATOR', 'LOCK', 'LOGIN', 'LOWER', 'M', 'MAP', 'MATCH', 'MATCHED', 'MAX', 'MAXVALUE', 'MEMBER', 'MERGE', 'MESSAGE_LENGTH', 'MESSAGE_OCTET_LENGTH', 'MESSAGE_TEXT', 'METHOD', 'MIN', 'MINUTE', 'MINVALUE', 'MOD', 'MODE', 'MODIFIES', 'MODIFY', 'MODULE', 'MONTH', 'MORE', 'MOVE', 'MULTISET', 'MUMPS', 'NAME', 'NAMES', 'NATIONAL', 'NATURAL', 'NCHAR', 'NCLOB', 'NESTING', 'NEW', 'NEXT', 'NO', 'NOCREATEDB', 'NOCREATEROLE', 'NOCREATEUSER', 'NOINHERIT', 'NOLOGIN', 'NONE', 'NORMALIZE', 'NORMALIZED', 'NOSUPERUSER', 'NOT', 'NOTHING', 'NOTIFY', 'NOTNULL', 'NOWAIT', 'NULL', 'NULLABLE', 'NULLIF', 'NULLS', 'NUMBER', 'NUMERIC', 'OBJECT', 'OCTETS', 'OCTET_LENGTH', 'OF', 'OFF', 'OFFSET', 'OIDS', 'OLD', 'ON', 'ONLY', 'OPEN', 'OPERATION', 'OPERATOR', 'OPTION', 'OPTIONS', 'OR', 'ORDER', 'ORDERING', 'ORDINALITY', 'OTHERS', 'OUT', 'OUTER', 'OUTPUT', 'OVER', 'OVERLAPS', 'OVERLAY', 'OVERRIDING', 'OWNER', 'PAD', 'PARAMETER', 'PARAMETERS', 'PARAMETER_MODE', 'PARAMETER_NAME', 'PARAMETER_ORDINAL_POSITION', 'PARAMETER_SPECIFIC_CATALOG', 'PARAMETER_SPECIFIC_NAME', 'PARAMETER_SPECIFIC_SCHEMA', 'PARTIAL', 'PARTITION', 'PASCAL', 'PASSWORD', 'PATH', 'PERCENTILE_CONT', 'PERCENTILE_DISC', 'PERCENT_RANK', 'PLACING', 'PLI', 'POSITION', 'POSTFIX', 'POWER', 'PRECEDING', 'PRECISION', 'PREFIX', 'PREORDER', 'PREPARE', 'PREPARED', 'PRESERVE', 'PRIMARY', 'PRIOR', 'PRIVILEGES', 'PROCEDURAL', 'PROCEDURE', 'PUBLIC', 'QUOTE', 'RANGE', 'RANK', 'READ', 'READS', 'REAL', 'RECHECK', 'RECURSIVE', 'REF', 'REFERENCES', 'REFERENCING', 'REGR_AVGX', 'REGR_AVGY', 'REGR_COUNT', 'REGR_INTERCEPT', 'REGR_R2', 'REGR_SLOPE', 'REGR_SXX', 'REGR_SXY', 'REGR_SYY', 'REINDEX', 'RELATIVE', 'RELEASE', 'RENAME', 'REPEATABLE', 'REPLACE', 'RESET', 'RESTART', 'RESTRICT', 'RESULT', 'RETURN', 'RETURNED_CARDINALITY', 'RETURNED_LENGTH', 'RETURNED_OCTET_LENGTH', 'RETURNED_SQLSTATE', 'RETURNS', 'REVOKE', 'RIGHT', 'ROLE', 'ROLLBACK', 'ROLLUP', 'ROUTINE', 'ROUTINE_CATALOG', 'ROUTINE_NAME', 'ROUTINE_SCHEMA', 'ROW', 'ROWS', 'ROW_COUNT', 'ROW_NUMBER', 'RULE', 'SAVEPOINT', 'SCALE', 'SCHEMA', 'SCHEMA_NAME', 'SCOPE', 'SCOPE_CATALOG', 'SCOPE_NAME', 'SCOPE_SCHEMA', 'SCROLL', 'SEARCH', 'SECOND', 'SECTION', 'SECURITY', 'SELECT', 'SELF', 'SENSITIVE', 'SEQUENCE', 'SERIALIZABLE', 'SERVER_NAME', 'SESSION', 'SESSION_USER', 'SET', 'SETOF', 'SETS', 'SHARE', 'SHOW', 'SIMILAR', 'SIMPLE', 'SIZE', 'SMALLINT', 'SOME', 'SOURCE', 'SPACE', 'SPECIFIC', 'SPECIFICTYPE', 'SPECIFIC_NAME', 'SQL', 'SQLCODE', 'SQLERROR', 'SQLEXCEPTION', 'SQLSTATE', 'SQLWARNING', 'SQRT', 'STABLE', 'START', 'STATE', 'STATEMENT', 'STATIC', 'STATISTICS', 'STDDEV_POP', 'STDDEV_SAMP', 'STDIN', 'STDOUT', 'STORAGE', 'STRICT', 'STRUCTURE', 'STYLE', 'SUBCLASS_ORIGIN', 'SUBLIST', 'SUBMULTISET', 'SUBSTRING', 'SUM', 'SUPERUSER', 'SYMMETRIC', 'SYSID', 'SYSTEM', 'SYSTEM_USER', 'TABLE', 'TABLESAMPLE', 'TABLESPACE', 'TABLE_NAME', 'TEMP', 'TEMPLATE', 'TEMPORARY', 'TERMINATE', 'THAN', 'THEN', 'TIES', 'TIME', 'TIMESTAMP', 'TIMEZONE_HOUR', 'TIMEZONE_MINUTE', 'TO', 'TOAST', 'TOP_LEVEL_COUNT', 'TRAILING', 'TRANSACTION', 'TRANSACTIONS_COMMITTED', 'TRANSACTIONS_ROLLED_BACK', 'TRANSACTION_ACTIVE', 'TRANSFORM', 'TRANSFORMS', 'TRANSLATE', 'TRANSLATION', 'TREAT', 'TRIGGER', 'TRIGGER_CATALOG', 'TRIGGER_NAME', 'TRIGGER_SCHEMA', 'TRIM', 'TRUE', 'TRUNCATE', 'TRUSTED', 'TYPE', 'UESCAPE', 'UNBOUNDED', 'UNCOMMITTED', 'UNDER', 'UNENCRYPTED', 'UNION', 'UNIQUE', 'UNKNOWN', 'UNLISTEN', 'UNNAMED', 'UNNEST', 'UNTIL', 'UPDATE', 'UPPER', 'USAGE', 'USER', 'USER_DEFINED_TYPE_CATALOG', 'USER_DEFINED_TYPE_CODE', 'USER_DEFINED_TYPE_NAME', 'USER_DEFINED_TYPE_SCHEMA', 'USING', 'VACUUM', 'VALID', 'VALIDATOR', 'VALUE', 'VALUES', 'VARCHAR', 'VARIABLE', 'VARYING', 'VAR_POP', 'VAR_SAMP', 'VERBOSE', 'VIEW', 'VOLATILE', 'WHEN', 'WHENEVER', 'WHERE', 'WIDTH_BUCKET', 'WINDOW', 'WITH', 'WITHIN', 'WITHOUT', 'WORK', 'WRITE', 'YEAR', 'ZONE']
    )

    csql = sql.split(' ')
    csql2 = []
    for token in csql:
        if token.lower() in [x.lower() for x in keywords['sql']]:
            # SQL keywords
            csql2.append(click.style(token, fg='blue'))
        elif any([x.lower() in token.lower() for x in keywords['logical']]):
            # Boolean values
            for kwd in keywords['logical']:
                logical_token = re.search(r'.*({}).*'.format('|'.join(keywords['logical'])), token, flags=re.IGNORECASE).group(1)
                token = re.sub(kwd, click.style(logical_token, fg='yellow'), token, flags=re.IGNORECASE)
            csql2.append(token)
        elif re.match(r'".*"', token):
            # Within double quotes ""
            csql2.append(re.sub(r'(.*?)(".*")(.*)', r'\1' + click.style(r'\2', fg='red') + r'\3', token))
        elif re.match(r'.*\..*', token):
            # schema.table
            csql2.append('.'.join([click.style(x, fg='magenta') for x in token.split('.')]))
        else:
            csql2.append(token)

    return ' '.join(csql2)


def progrun_update(name, started, ended, args):
    """
    Update code.progrun with program run information.

    Arguments:
        name {str} -- name of program
        started {datetime} -- timestamp of program start time
        ended {datetime} -- timestamp of program end time
        args {str} -- string of dictionary (str(dict(...))) containing program arguments

    Returns:
        nothing
    """
    try:
        pg = Postgres('Andoni', 'Andoni')
        pg.execute(
            pg.build_insert(
                schema='code',
                table='progrun',
                columns=['name', 'started', 'ended', 'args'],
                values=[name, started, ended, args],
                validate=True))
    except Exception as e:
        echo("Unable to update Postgres database for program '%s'" % prog,
            warn=True, fn_name='pydoni.db.progrun_update', error_msg=str(e))


from pydoni.classes import DoniDt
from pydoni.os import listfiles
from pydoni.vb import echo
from pydoni.db import Postgres
from pydoni.sh import syscmd
