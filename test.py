
import psycopg

port = 5432
user = "kenny"
dbname = "MemeToasterTest"

POSTGRESQL_HOST = "localhost"
POSTGRESQL_PASSWORD = "admin"   

conn = psycopg.connect(
    host = POSTGRESQL_HOST,
    port = port,
    user = user,
    password = POSTGRESQL_PASSWORD,
    dbname = dbname
)

cursor = conn.cursor()

tagsFetch = cursor.execute("SELECT tag FROM tag").fetchall()
tags = set(
    [i[0] for i in tagsFetch]
)

print(tags)

conn.close()
