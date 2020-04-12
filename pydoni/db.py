import pydoni


class Postgres(object):
    """
    Interact with PostgreSQL database through Python.
    
    :param pg_user: username for database to connect
    :type pg_user: str
    :param pg_dbname: name of database to connect to
    :type pg_dbname: str
    """

    def __init__(self, pg_user=None, pg_dbname=None):
        
        self.logger = pydoni.logger_setup(
            name=pydoni.what_is_my_name(classname=self.__class__.__name__, with_modname=True),
            level=pydoni.modloglev)
        
        self.dbuser = pg_user
        self.dbname = pg_dbname
        self.dbcon = self.connect()
        
        self.logger.logvars(locals())

        self.ischema = self.infoschema(
            columns=['table_schema', 'table_name', '"column_name"', 'data_type', 'is_nullable'],
            infoschema_table='columns')

    def connect(self):
        """
        Connect to Postgres database.
        
        :return: database connection
        :rtype: sqlalchemy DB connection
        """
        import sqlalchemy

        if self.dbuser is None and self.dbname is None:
            # Try to parse ~/.pgpass file
            hostname, port, pg_dbname, pg_user, pg_pass = self.read_pgpass()
            if pg_dbname > '' and pg_user > '':
                self.dbuser = pg_user
                self.dbname = pg_dbname
            else:
                error_msg = 'Could not connect to Postgres database! Check your PG credentials' + \
                ' and/or you ~/.pgpass file.'
                self.logger.error(error_msg)
                raise Exception(error_msg)

        con_str = "postgresql://%s@localhost:5432/%s" % (self.dbuser, self.dbname)
        self.logger.logvars(locals())

        return sqlalchemy.create_engine(con_str)

    def read_pgpass(self):
        """
        Read ~/.pgpass file if it exists and extract Postgres credentials.
        """
        import os

        pgpass_file = os.path.expanduser('~/.pgpass')
        if os.path.isfile(pgpass_file):
            with open(pgpass_file, 'r') as f:
                pgpass_contents = f.read()
            
            return pgpass_contents.split(':')

    def execute(self, sql, logfile=None, log_ts=False, progress=False):
        """
        Execute list of SQL statements or a single statement, in a transaction.
        
        :param sql: string or list of strings of SQL to execute
        :type sql: str, list
        :param logfile: path to log file to save executed SQL to
        :type logfile: str
        :param log_ts: append timestamp to each SQL log entry
        :type log_ts: bool
        :param progress: display `tqdm` progress bar
        :type param: bool
        :return: True or None
        :rtype: bool
        """
        import os
        import sqlalchemy

        if progress:
            from tqdm import tqdm

        self.logger.logvars(locals())

        if logfile is None:
            write_log = False
        else:
            assert isinstance(logfile, str)
            write_log = True

        if write_log:
            self.logger.info("Writing output to file: " + logfile)
                
        sql = pydoni.ensurelist(sql)

        with self.dbcon.begin() as con:
            if progress:
                pbar = tqdm(total=len(sql), unit='query')

            for stmt in sql:
                con.execute(sqlalchemy.text(stmt))

                if write_log:
                    with open(logfile, 'a') as f:
                        entry = stmt + '\n'

                        if log_ts:
                            entry = pydoni.systime() + ' ' + entry

                        f.write(entry)

                if progress:
                    pbar.update(1)

        if progress:
            pbar.close()

        self.logger.info("All SQL statement(s) executed successfully")
        return True

    def read_sql(self, sql, simplify=True):
        """
        Execute SQL and read results using Pandas.
        
        :param sql: SQL string to execute and read results from
        :type sql: str, list
        :param simplify: return pd.Series if pd.DataFrame returned only has 1 column
        :type simplify: bool
        :return: data queried from DB
        :rtype: DataFrame if 2D, Series if 1D
        """
        import pandas as pd

        self.logger.logvars(locals())
        res = pd.read_sql(sql, con=self.dbcon)
        self.logger.info('Queried data frame, shape: %s' % str(res.shape))

        if res.shape[1] == 1:
            if simplify:
                self.logger.info("Simplifying result data to pd.Series, length: %s" % str(len(res)))
                res = res.iloc[:, 0]
        
        return res

    def validate_dtype(self, schema, table, col, val):
        """
        Query database for datatype of value and validate that the Python value to
        insert to that column is compatible with the SQL datatype.
        
        :param schema: table schema (schema of `table` parameter)
        :type schema: str
        :param table: table name
        :type table: str
        :param col: column name
        :type col: str
        :param val: value to check against the datatype of column `col`
        :type val: any
        :return: indicator as to whether python value is compatible with SQL datatype
        :rtype: bool
        """
        import pandas as pd

        self.logger.logvars(locals())
        full_col = '.'.join([schema, table, col])

        infoschema = self.ischema
        infoschema = infoschema.loc[
            (infoschema['table_schema'] == schema) &
            (infoschema['table_name'] == table) &
            (infoschema['column_name'] == col)]
        infoschema = infoschema.squeeze().to_dict()

        if val == 'NULL' or val is None:
            if bool(infoschema['is_nullable']) is True:
                return True
            else:
                self.logger.error("Value 'NULL' (dtype: {}) not allowed for column {}".format(
                    val.__class__.__name__, full_col))
                return False

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

        if dtype == 'date':
            import pdb;pdb.set_trace()
        # Get python equivalent of SQL column datatype according to dtype_map above
        python_dtype = [v for k, v in dtype_map.items() if dtype in k]
        if not len(python_dtype):
            self.logger.error("Column {} is datatype {}, which is not one of: {}".format(
                full_col, python_dtype, str(list(set([v for k, v in dtype_map.items()])))))
            return False
        else:
            python_dtype = python_dtype[0]

        # Prepare message to be used in event of incompatible datatypes
        msg = 'Incompatible datatypes! SQL column {} has type `{}`, and Python value `{}` is of type `{}`.'.format(
            full_col, dtype, str(val), val.__class__.__name__)

        # Begin validation
        if python_dtype == 'bool':
            
            if isinstance(val, bool):
                return True
            
            else:
                if isinstance(val, str):
                    if val.lower() in ['t', 'true', 'f', 'false']:
                        return True

        elif python_dtype == 'int':
            
            if isinstance(val, int):
                return True
            
            else:
                if isinstance(val, str):
                    try:
                        test = int(val)
                        return True
                    except:
                        pass

        elif python_dtype == 'float':

            if isinstance(val, float):
                return True
            
            else:
                if val == 'inf':
                    pass
                try:
                    test = float(val)
                    return True
                except:
                    pass

        elif python_dtype == 'str':
        
            if isinstance(val, str):
                return True
        
        else:
            return True

        self.logger.error(msg)
        return False

    def build_update(self, schema, table, pkey_name, pkey_value, columns, values, validate=True, newlines=False):
        """
        Construct SQL UPDATE statement.
        By default, this method will:
        
            - Attempt to coerce a date value to proper format if the input value is detect_dtype
              as a date but possibly in the improper format. Ex: '2019:02:08' -> '2019-02-08'
            - Quote all values passed in as strings. This will include string values that
              are coercible to numerics. Ex: '5', '7.5'.
            - Do not quote all values passed in as integer or boolean values.
            - Primary key value is quoted if passed in as a string. Otherwise, not quoted.
        
        :param schema: name of schema
        :type schema: str
        :param table: SQL table name
        :type table: str
        :param pkey_name: name of primary key in table
        :type pkey_name: str
        :param pkey_value: value of primary key for value to update
        :type pkey_value: str
        :param columns: columns to consider in UPDATE statement
        :type columns: list
        :param values: values to consider in UPDATE statement
        :type values: list
        :param validate: validate that each value may be inserted to destination column
        :type validate: bool
        :param newlines: add newlines to query string to make more human-readable
        :type newlines: true
        :return: SQL UPDATE statement
        :rtype: str
        """

        self.logger.logvars(locals())

        columns = pydoni.ensurelist(columns)
        values = pydoni.ensurelist(values)
        if len(columns) != len(values):
            raise Exception("Parameters `columns` and `values` must be of equal length")

        pkey_value = self.__single_quote__(pkey_value)
        lst = []

        for col, val in zip(columns, values):

            if validate:
                test = self.validate_dtype(schema, table, col, val)
                if not test:
                    dtype = type(val).__name__
                    raise Exception("Dtype mismatch. Value: {val}, dtype: {dtype}, column: {col}".format(**locals()))
            
            if str(val).lower() in ['nan', 'n/a', 'null', 'none', '']:
                val = 'NULL'

            elif pydoni.test(val, 'bool') or pydoni.test(val, 'int') or pydoni.test(val, 'float'):
                pass

            else:
                # Assume string
                val = self.__single_quote__(val)
            
            if newlines:
                lst.append('\n    "{}"={}'.format(col, str(val)))
            
            else:
                lst.append('"{}"={}'.format(col, str(val)))

        sql = ["UPDATE {}.{}", "SET {}", "WHERE {} = {};"]
        if newlines:
            lst[0] = lst[0].strip()
            sql = '\n'.join(sql)
        else:
            sql = ' '.join(sql)
        
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
        
            - Attempt to coerce a date value to proper format if the input value is
              detect_dtype as a date but possibly in the improper format.
              Ex: '2019:02:08' -> '2019-02-08'
            - Quote all values passed in as strings. This will include string values
              that are coercible to numerics. Ex: '5', '7.5'.
            - Do not quote all values passed in as integer or boolean values.
            - Primary key value is quoted if passed in as a string. Otherwise, not quoted.
        
        :param schema: name of schema
        :type schema: str
        :param table: SQL table name
        :type table: str
        :param columns: columns to consider in UPDATE statement
        :type columns: list
        :param values: values to consider in UPDATE statement
        :type values: list
        :param validate: validate that each value may be inserted to destination column
        :type validate: bool
        :param newlines: add newlines to query string to make more human-readable
        :type newlines: true
        :return: SQL UPDATE statement
        :rtype: str
        """

        self.logger.logvars(locals())

        columns = pydoni.ensurelist(columns)
        values = pydoni.ensurelist(values)
        if len(columns) != len(values):
            raise Exception("Parameters `columns` and `values` must be of equal length")
        
        lst = []

        for col, val in zip(columns, values):

            if validate:
                test = self.validate_dtype(schema, table, col, val)
                if not test:
                    raise Exception('Dtype mismatch')

            if str(val) in ['nan', 'N/A', 'null', '']:
                val = 'null'

            elif pydoni.test(val, 'bool') or pydoni.test(val, 'int') or pydoni.test(val, 'float'):
                pass

            else:
                # Assume string, handle quotes
                val = self.__single_quote__(val)
            
            lst.append(val)

        values_final = ', '.join(str(x) for x in lst)
        values_final = values_final.replace("'null'", 'null')
        columns = ', '.join(['"' + x + '"' for x in columns])
        
        sql = ["insert into {}.{} ({})", "values ({});"]
        sql = "\n".join(sql) if newlines else " ".join(sql)
        
        return sql.format(schema, table, columns, values_final)

    def build_delete(self, schema, table, pkey_name, pkey_value, newlines=False):
        """
        Construct SQL DELETE FROM statement.
        
        :param schema: name of schema
        :type schema: str
        :param table: SQL table name
        :type table: str
        :param pkey_name: name of primary key in table
        :type: str
        :param pkey_value: value of primary key for value to update
        :type pkey_value: any
        :param newlines: add newlines to query string
        :type newlines: bool
        :return: SQL DELETE statement
        :rtype: str
        """

        self.logger.logvars(locals())

        pkey_value = self.__single_quote__(pkey_value)
        sql = ["delete from {schema}.{table}", "where {pkey_name} = {pkey_value};"]
        sql = "\n".join(sql) if newlines else " ".join(sql)

        return sql.format(**locals())

    def infoschema(self, columns=[], infoschema_table='columns'):
        """
        Query from information_schema. Vanilla call to this function executes:

            select * from information_schema.columns;

        :param columns: column(s) to select form information schema table
        :type columns: list
        :param infoschema_table: information schema table to query
        :type infoschema_table: str
        :return: information schema table requested
        :rtype: DataFrame
        """

        self.logger.logvars(locals())
        
        assert isinstance(infoschema_table, str)

        columns = ', '.join(pydoni.ensurelist(columns))
        if columns in ['', '*']:
            columns = '*'
        
        sql = "select %s\nfrom information_schema.%s;" % (columns, infoschema_table)
        df = self.read_sql(sql, simplify=False)

        self.logger.info("Retrieved information_schema.{}".format(infoschema_table))

        # Format known column datatypes
        bool_cols = ['is_nullable']
        for bcol in bool_cols:
            if bcol in df.columns:
                df[bcol] = df[bcol].map(lambda x: dict(YES=True, NO=False)[x])

        return df

    def colnames(self, schema, table):
        """
        Get column names of table as a list.
        
        :param schema: schema name
        :type :schema str
        :param table: table name
        :type table: str
        :return: list of column names
        :rtype: list
        """
        self.logger.logvars(locals())
        
        df_cols = self.infoschema(
            columns=['table_schema', 'table_name', '"column_name"'],
            infoschema_table='columns')
        
        df_cols = df_cols.loc[(df_cols['table_schema'] == schema) & (df_cols['table_name'] == table)]
        cols = df_cols['column_name'].squeeze().tolist()

        self.logger.info('Columns retrieved from {schema}.{table}: {cols}'.format(**locals()))
        return cols

    def coldtypes(self, schema, table):
        """
        Get column datatypes of table as a dictionary.
    
        :param schema: schema name
        :type :schema str
        :param table: table name
        :type table: str
        :return: dictionary of key: value pairs of column_name: column_datatype
        :rtype: dict
        """

        self.logger.logvars(locals())
        
        dtype = self.infoschema(
            columns=['"column_name"', 'data_type'],
            infoschema_table='columns').squeeze()
        dtype = dtype.set_index('column_name')['data_type'].to_dict()
        
        self.logger.info('Dtypes retrieved from {schema}.{table} for columns: {columns}'.format(
            schema=schema, table=table, columns=[k for k, v in dtype.items()]))
        
        return dtype

    def read_table(self, schema, table):
        """
        Read entire SQL table.
        
        :param schema: schema name
        :type :schema str
        :param table: table name
        :type table: str
        :return: entire SQL table as DataFrame (or Series if only one column)
        :rtype: DataFrame, Series
        """

        self.logger.logvars(locals())

        df = self.read_sql("select * from {schema}.{table}".format(**locals()))
        self.logger.info("Read dataframe {schema}.{table}, shape: {df.shape}".format(**locals()))
        
        return df

    def dump(self, backup_dir_abspath):
        """
        Execute pg_dump command on connected database. Create .sql backup file.
        
        :param backup_dir_abspath: absolute path to directory to dump Postgres database to
        :type backup_dir_abspath: str
        """
        import os
        
        self.logger.logvars(locals())
        
        backup_dir_abspath = os.path.expanduser(backup_dir_abspath)
        assert os.path.isdir(backup_dir_abspath)

        bin = pydoni.sh.find_binary('pg_dump', abort=True)
        cmd = '{bin} {self.dbname} > "{backup_dir_abspath}/{self.dbname}.sql"'.format(**locals())
        
        self.logger.var('bin', bin)
        self.logger.var('cmd', cmd)

        pydoni.syscmd(cmd)
        self.logger.info("Dumped database to dir: " + backup_dir_abspath)

    def dump_tables(self, backup_dir_abspath, sep=',', coerce_csv=False):
        """
        Dump each table in database to a textfile with specified separator.
        
        Source:
            https://stackoverflow.com/questions/17463299/export-database-into-csv-file?answertab=oldest#tab-top
        
        :param backup_dir_abspath: absolute path to directory to dump Postgres database to
        :type backup_dir_abspath: str
        :param sep: output datafile separator, defaults to comma
        :type sep: str
        :param coerce_csv: read in each file outputted, then write as a quoted CSV
        :type coerce_csv: bool
        """
        import os
        
        self.logger.logvars(locals())

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
           statement := 'COPY ' || tables.schema_table || ' TO ''' || path || '/' || tables.schema_table || '.csv' ||''' DELIMITER ''{sep}'' CSV HEADER';
           EXECUTE statement;
        END LOOP;
        RETURN;  
        END;
        $$ LANGUAGE plpgsql;""".format(**locals())
        self.execute(db_to_csv)

        # Execute function, dumping each table to a textfile.
        # Function is used as follows: SELECT db_to_csv('/path/to/dump/destination');
        self.execute("select db_to_csv('{}')".format(backup_dir_abspath))
        self.logger.info("Successfully dumped database")

        # If coerce_csv is True, read in each file outputted, then write as a quoted CSV.
        # Replace 'sep' if different from ',' and quote each text field.
        if coerce_csv:
            if sep != ',':
                owd = os.getcwd()
                os.chdir(backup_dir_abspath)

                # Get tables that were dumped and build filenames
                get_dumped_tables = """
                select (table_schema || '.' || table_name) as schema_table
                from information_schema.tables t
                join information_schema.schemata s
                on s.schema_name = t.table_schema 
                where t.table_schema not in ('pg_catalog', 'information_schema')
                   and t.table_type not in ('view')
                order by schema_table"""
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
                
                os.chdir(owd)
            
            else:
                self.logger.warn("`coerce_csv` is True but desired sep is not a comma!")

    def __single_quote__(self, val):
        """
        Escape single quotes and put single quotes around value if string value.
        
        :param val: if `type(val)` is `str`, surround with single quotes, used in building SQL
        :type val: any
        :return: quoted string or original value
        :rtype: str or `type(val)`
        """

        if type(val) not in [bool, int, float]:
            val = str(val).replace("'", "''")
            val = "'" + val + "'"
        
        return val


def colorize_sql(sql):
    """
    Colorize SQL by detecting keywords.
    
    :param sql: SQL string to colorize
    :type sql: str
    :return: string with colorized SQL keywords embedded
    :rtype: str
    """

    import click

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    keywords = dict(
        logical = ['true', 'false'],
        sql = [
            'ABORT', 'ABS', 'ABSOLUTE', 'ACCESS', 'ACTION', 'ADA', 'ADD', 'ADMIN', 'AFTER',
            'AGGREGATE', 'ALIAS', 'ALL', 'ALLOCATE', 'ALSO', 'ALTER', 'ALWAYS', 'ANALYSE',
            'ANALYZE', 'AND', 'ANY', 'ARE', 'ARRAY', 'AS', 'ASC', 'ASENSITIVE', 'ASSERTION',
            'ASSIGNMENT', 'ASYMMETRIC', 'AT', 'ATOMIC', 'ATTRIBUTE', 'ATTRIBUTES',
            'AUTHORIZATION', 'AVG', 'BACKWARD', 'BEFORE', 'BEGIN', 'BERNOULLI', 'BETWEEN',
            'BIGINT', 'BINARY', 'BIT', 'BITVAR', 'BIT_LENGTH', 'BLOB', 'BOOLEAN', 'BOTH',
            'BREADTH', 'BY', 'C', 'CACHE', 'CALL', 'CALLED', 'CARDINALITY', 'CASCADE',
            'CASCADED', 'CASE', 'CAST', 'CATALOG', 'CATALOG_NAME', 'CEIL', 'CEILING',
            'CHAIN', 'CHAR', 'CHARACTER', 'CHARACTERISTICS', 'CHARACTERS', 'CHARACTER_LENGTH',
            'CHARACTER_SET_CATALOG', 'CHARACTER_SET_NAME', 'CHARACTER_SET_SCHEMA',
            'CHAR_LENGTH', 'CHECK', 'CHECKED', 'CHECKPOINT', 'CLASS', 'CLASS_ORIGIN', 'CLOB',
            'CLOSE', 'CLUSTER', 'COALESCE', 'COBOL', 'COLLATE', 'COLLATION',
            'COLLATION_CATALOG', 'COLLATION_NAME', 'COLLATION_SCHEMA', 'COLLECT', 'COLUMN',
            'COLUMN_NAME', 'COMMAND_FUNCTION', 'COMMAND_FUNCTION_CODE', 'COMMENT', 'COMMIT',
            'COMMITTED', 'COMPLETION', 'CONDITION', 'CONDITION_NUMBER', 'CONNECT', 
            'CONNECTION', 'CONNECTION_NAME', 'CONSTRAINT', 'CONSTRAINTS', 'CONSTRAINT_CATALOG', 
            'CONSTRAINT_NAME', 'CONSTRAINT_SCHEMA', 'CONSTRUCTOR', 'CONTAINS', 'CONTINUE', 
            'CONVERSION', 'CONVERT', 'COPY', 'CORR', 'CORRESPONDING', 'COUNT', 'COVAR_POP', 
            'COVAR_SAMP', 'CREATE', 'CREATEDB', 'CREATEROLE', 'CREATEUSER', 'CROSS', 'CSV', 
            'CUBE', 'CUME_DIST', 'CURRENT', 'CURRENT_DATE', 'CURRENT_DEFAULT_TRANSFORM_GROUP', 
            'CURRENT_PATH', 'CURRENT_ROLE', 'CURRENT_TIME', 'CURRENT_TIMESTAMP', 
            'CURRENT_TRANSFORM_GROUP_FOR_TYPE', 'CURRENT_USER', 'CURSOR', 'CURSOR_NAME', 
            'CYCLE', 'DATA', 'DATABASE', 'DATE', 'DATETIME_INTERVAL_CODE', 
            'DATETIME_INTERVAL_PRECISION', 'DAY', 'DEALLOCATE', 'DEC', 'DECIMAL', 
            'DECLARE', 'DEFAULT', 'DEFAULTS', 'DEFERRABLE', 'DEFERRED', 'DEFINED', 
            'DEFINER', 'DEGREE', 'DELETE', 'DELIMITER', 'DELIMITERS', 'DENSE_RANK', 
            'DEPTH', 'DEREF', 'DERIVED', 'DESC', 'DESCRIBE', 'DESCRIPTOR', 'DESTROY', 
            'DESTRUCTOR', 'DETERMINISTIC', 'DIAGNOSTICS', 'DICTIONARY', 'DISABLE', 
            'DISCONNECT', 'DISPATCH', 'DISTINCT', 'DO', 'DOMAIN', 'DOUBLE', 'DROP', 
            'DYNAMIC', 'DYNAMIC_FUNCTION', 'DYNAMIC_FUNCTION_CODE', 'EACH', 'ELEMENT', 
            'ELSE', 'ENABLE', 'ENCODING', 'ENCRYPTED', 'END', 'END-EXEC', 'EQUALS', 
            'ESCAPE', 'EVERY', 'EXCEPT', 'EXCEPTION', 'EXCLUDE', 'EXCLUDING', 'EXCLUSIVE', 
            'EXEC', 'EXECUTE', 'EXISTING', 'EXISTS', 'EXP', 'EXPLAIN', 'EXTERNAL', 
            'EXTRACT', 'FALSE', 'FETCH', 'FILTER', 'FINAL', 'FIRST', 'FLOAT', 'FLOOR', 
            'FOLLOWING', 'FOR', 'FORCE', 'FOREIGN', 'FORTRAN', 'FORWARD', 'FOUND', 'FREE', 
            'FREEZE', 'FROM', 'FULL', 'FUNCTION', 'FUSION', 'G', 'GENERAL', 'GENERATED', 
            'GET', 'GLOBAL', 'GO', 'GOTO', 'GRANT', 'GRANTED', 'GREATEST', 'GROUP', 
            'GROUPING', 'HANDLER', 'HAVING', 'HEADER', 'HIERARCHY', 'HOLD', 'HOST', 
            'HOUR', 'IDENTITY', 'IGNORE', 'ILIKE', 'IMMEDIATE', 'IMMUTABLE', 'IMPLEMENTATION', 
            'IMPLICIT', 'IN', 'INCLUDING', 'INCREMENT', 'INDEX', 'INDICATOR', 'INFIX', 
            'INHERIT', 'INHERITS', 'INITIALIZE', 'INITIALLY', 'INNER', 'INOUT', 'INPUT', 
            'INSENSITIVE', 'INSERT', 'INSTANCE', 'INSTANTIABLE', 'INSTEAD', 'INT', 
            'INTEGER', 'INTERSECT', 'INTERSECTION', 'INTERVAL', 'INTO', 'INVOKER', 'IS', 
            'ISNULL', 'ISOLATION', 'ITERATE', 'JOIN', 'K', 'KEY', 'KEY_MEMBER', 'KEY_TYPE', 
            'LANCOMPILER', 'LANGUAGE', 'LARGE', 'LAST', 'LATERAL', 'LEADING', 'LEAST', 
            'LEFT', 'LENGTH', 'LESS', 'LEVEL', 'LIKE', 'LIMIT', 'LISTEN', 'LN', 'LOAD', 
            'LOCAL', 'LOCALTIME', 'LOCALTIMESTAMP', 'LOCATION', 'LOCATOR', 'LOCK', 'LOGIN', 
            'LOWER', 'M', 'MAP', 'MATCH', 'MATCHED', 'MAX', 'MAXVALUE', 'MEMBER', 'MERGE', 
            'MESSAGE_LENGTH', 'MESSAGE_OCTET_LENGTH', 'MESSAGE_TEXT', 'METHOD', 'MIN', 
            'MINUTE', 'MINVALUE', 'MOD', 'MODE', 'MODIFIES', 'MODIFY', 'MODULE', 'MONTH', 
            'MORE', 'MOVE', 'MULTISET', 'MUMPS', 'NAME', 'NAMES', 'NATIONAL', 'NATURAL', 
            'NCHAR', 'NCLOB', 'NESTING', 'NEW', 'NEXT', 'NO', 'NOCREATEDB', 'NOCREATEROLE', 
            'NOCREATEUSER', 'NOINHERIT', 'NOLOGIN', 'NONE', 'NORMALIZE', 'NORMALIZED', 
            'NOSUPERUSER', 'NOT', 'NOTHING', 'NOTIFY', 'NOTNULL', 'NOWAIT', 'NULL', 
            'NULLABLE', 'NULLIF', 'NULLS', 'NUMBER', 'NUMERIC', 'OBJECT', 'OCTETS', 
            'OCTET_LENGTH', 'OF', 'OFF', 'OFFSET', 'OIDS', 'OLD', 'ON', 'ONLY', 'OPEN', 
            'OPERATION', 'OPERATOR', 'OPTION', 'OPTIONS', 'OR', 'ORDER', 'ORDERING', 
            'ORDINALITY', 'OTHERS', 'OUT', 'OUTER', 'OUTPUT', 'OVER', 'OVERLAPS', 
            'OVERLAY', 'OVERRIDING', 'OWNER', 'PAD', 'PARAMETER', 'PARAMETERS', 
            'PARAMETER_MODE', 'PARAMETER_NAME', 'PARAMETER_ORDINAL_POSITION', 
            'PARAMETER_SPECIFIC_CATALOG', 'PARAMETER_SPECIFIC_NAME', 'PARAMETER_SPECIFIC_SCHEMA', 
            'PARTIAL', 'PARTITION', 'PASCAL', 'PASSWORD', 'PATH', 'PERCENTILE_CONT', 
            'PERCENTILE_DISC', 'PERCENT_RANK', 'PLACING', 'PLI', 'POSITION', 'POSTFIX', 
            'POWER', 'PRECEDING', 'PRECISION', 'PREFIX', 'PREORDER', 'PREPARE', 'PREPARED', 
            'PRESERVE', 'PRIMARY', 'PRIOR', 'PRIVILEGES', 'PROCEDURAL', 'PROCEDURE', 'PUBLIC', 
            'QUOTE', 'RANGE', 'RANK', 'READ', 'READS', 'REAL', 'RECHECK', 'RECURSIVE', 'REF', 
            'REFERENCES', 'REFERENCING', 'REGR_AVGX', 'REGR_AVGY', 'REGR_COUNT', 
            'REGR_INTERCEPT', 'REGR_R2', 'REGR_SLOPE', 'REGR_SXX', 'REGR_SXY', 'REGR_SYY', 
            'REINDEX', 'RELATIVE', 'RELEASE', 'RENAME', 'REPEATABLE', 'REPLACE', 'RESET', 
            'RESTART', 'RESTRICT', 'RESULT', 'RETURN', 'RETURNED_CARDINALITY', 
            'RETURNED_LENGTH', 'RETURNED_OCTET_LENGTH', 'RETURNED_SQLSTATE', 'RETURNS', 
            'REVOKE', 'RIGHT', 'ROLE', 'ROLLBACK', 'ROLLUP', 'ROUTINE', 'ROUTINE_CATALOG', 
            'ROUTINE_NAME', 'ROUTINE_SCHEMA', 'ROW', 'ROWS', 'ROW_COUNT', 'ROW_NUMBER', 
            'RULE', 'SAVEPOINT', 'SCALE', 'SCHEMA', 'SCHEMA_NAME', 'SCOPE', 'SCOPE_CATALOG', 
            'SCOPE_NAME', 'SCOPE_SCHEMA', 'SCROLL', 'SEARCH', 'SECOND', 'SECTION', 'SECURITY', 
            'SELECT', 'SELF', 'SENSITIVE', 'SEQUENCE', 'SERIALIZABLE', 'SERVER_NAME', 
            'SESSION', 'SESSION_USER', 'SET', 'SETOF', 'SETS', 'SHARE', 'SHOW', 'SIMILAR', 
            'SIMPLE', 'SIZE', 'SMALLINT', 'SOME', 'SOURCE', 'SPACE', 'SPECIFIC', 
            'SPECIFICTYPE', 'SPECIFIC_NAME', 'SQL', 'SQLCODE', 'SQLERROR', 'SQLEXCEPTION', 
            'SQLSTATE', 'SQLWARNING', 'SQRT', 'STABLE', 'START', 'STATE', 'STATEMENT', 
            'STATIC', 'STATISTICS', 'STDDEV_POP', 'STDDEV_SAMP', 'STDIN', 'STDOUT', 
            'STORAGE', 'STRICT', 'STRUCTURE', 'STYLE', 'SUBCLASS_ORIGIN', 'SUBLIST', 
            'SUBMULTISET', 'SUBSTRING', 'SUM', 'SUPERUSER', 'SYMMETRIC', 'SYSID', 'SYSTEM', 
            'SYSTEM_USER', 'TABLE', 'TABLESAMPLE', 'TABLESPACE', 'TABLE_NAME', 'TEMP', 
            'TEMPLATE', 'TEMPORARY', 'TERMINATE', 'THAN', 'THEN', 'TIES', 'TIME', 'TIMESTAMP', 
            'TIMEZONE_HOUR', 'TIMEZONE_MINUTE', 'TO', 'TOAST', 'TOP_LEVEL_COUNT', 'TRAILING', 
            'TRANSACTION', 'TRANSACTIONS_COMMITTED', 'TRANSACTIONS_ROLLED_BACK', 
            'TRANSACTION_ACTIVE', 'TRANSFORM', 'TRANSFORMS', 'TRANSLATE', 'TRANSLATION', 
            'TREAT', 'TRIGGER', 'TRIGGER_CATALOG', 'TRIGGER_NAME', 'TRIGGER_SCHEMA', 
            'TRIM', 'TRUE', 'TRUNCATE', 'TRUSTED', 'TYPE', 'UESCAPE', 'UNBOUNDED', 
            'UNCOMMITTED', 'UNDER', 'UNENCRYPTED', 'UNION', 'UNIQUE', 'UNKNOWN', 
            'UNLISTEN', 'UNNAMED', 'UNNEST', 'UNTIL', 'UPDATE', 'UPPER', 'USAGE', 
            'USER', 'USER_DEFINED_TYPE_CATALOG', 'USER_DEFINED_TYPE_CODE', 
            'USER_DEFINED_TYPE_NAME', 'USER_DEFINED_TYPE_SCHEMA', 'USING', 'VACUUM', 
            'VALID', 'VALIDATOR', 'VALUE', 'VALUES', 'VARCHAR', 'VARIABLE', 'VARYING', 
            'VAR_POP', 'VAR_SAMP', 'VERBOSE', 'VIEW', 'VOLATILE', 'WHEN', 'WHENEVER', 
            'WHERE', 'WIDTH_BUCKET', 'WINDOW', 'WITH', 'WITHIN', 'WITHOUT', 'WORK', 
            'WRITE', 'YEAR', 'ZONE'
        ]
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
                logical_token = re.search(r'.*({}).*'.format(
                    '|'.join(keywords['logical'])), token, flags=re.IGNORECASE).group(1)
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

    self.logger.info("Colorized SQL")
    return ' '.join(csql2)


def progrun_update(name, started, ended, args, res={}):
    """
    Update code.progrun with program run information.

    :param name: name of program
    :type name: str
    :param started: timestamp of program start time
    :type started: datetime.datetime
    :param ended: timestamp of program end time
    :type ended: datetime.datetime
    :param args: dictionary containing program arguments to log
    :type args: str
    :param res: optional dictionary containing result summary
    :type: dict
    """

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)

    pg = Postgres('Andoni', 'Andoni')
    args = str(args) if isinstance(args, dict) else args

    schema = 'code'
    table = 'progrun'
    columns = ['name', 'started', 'ended', 'args', 'res']
    values = [name, started, ended, args, res]
    validate = True

    logger.logvars(locals())

    # pg.execute(
    #     pg.build_insert(schema=schema, table=table, columns=columns, values=values, validate=True))
    pg.execute(pg.build_insert(**locals()))

    logger.info("Successfully inserted record into {schema}.{table}".format(**locals()))

