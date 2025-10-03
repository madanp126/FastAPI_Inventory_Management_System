import pyodbc

def get_connection():
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=sharedmssql8.securehostdns.com,1234;'
        'DATABASE=kankavli_learning;'
        'UID=kankavli_team;'
        'PWD=igzno.cjebphNmuxrkfq;'
        'TrustServerCertificate=yes;'
    )
    return conn