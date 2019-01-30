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

def pg_connect(pg_user, pg_db):
    from sqlalchemy import create_engine
    return create_engine('postgresql://{}@localhost:5432/{}'.format(pg_user, pg_db))

def pg_execute(sql, con):
    from sqlalchemy import text
    with con.begin() as con:
        con.execute(text(sql))

