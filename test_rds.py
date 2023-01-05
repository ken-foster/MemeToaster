import psycopg

host = "localhost"
port = 5432
user = "kenny"
password = "admin"
dbname = "MemeToasterTest"

connection = psycopg.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=dbname,
        connect_timeout=5)

print("connection established")

cursor = connection.cursor()

# Create Tables

create_tables_query = """

DROP TABLE IF EXISTS filename;

CREATE TABLE filename (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL);


DROP TABLE IF EXISTS tag;

CREATE TABLE tag (
    id SERIAL PRIMARY KEY,
    tag TEXT NOT NULL);


DROP TABLE IF EXISTS tag_filename;

CREATE TABLE tag_filename (
	id SERIAL PRIMARY KEY,
	filename_id INTEGER NOT NULL,
	tag_id INTEGER NOT NULL);
"""

cursor.execute(create_tables_query)
connection.commit()

# Insert Values

insert_values_query = """
INSERT INTO filename (filename)
VALUES
	('angry7.jpg'),
	('boob5.jpg'),
	('devil0.jpg');

INSERT INTO tag (tag)
VALUES
	('angry'),
	('pingu'),
	('boob'),
	('devil'),
	('demon'),
	('evil');

INSERT INTO tag_filename (filename_id, tag_id)
VALUES
    (1,1),
    (1,2),
    (2,3),
    (3,4),
    (3,5),
    (3,6);
"""

cursor.execute(insert_values_query)
connection.commit()
print("values entered")

# Retrieve table values
# filename
cursor.execute("SELECT * FROM filename")
print(cursor.fetchall())

# tag
cursor.execute("SELECT * FROM tag")
print(cursor.fetchall())

# filename_tag
cursor.execute("SELECT * FROM tag_filename")
print(cursor.fetchall())

connection.close()

print("connection closed")