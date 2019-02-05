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
