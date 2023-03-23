from random import choice

from data import ssh_connect, sql_connect

server = ssh_connect()
server.start()

conn = sql_connect(server)

###

def query_by_tag(tag, conn):
    query_by_tag = """
    SELECT filename FROM filename AS f
        LEFT JOIN tag_filename AS tf
        ON f.id = tf.filename_id
            LEFT JOIN tag
            ON tf.tag_id = tag.id
    WHERE tag.tag = %s"""

    with conn.cursor() as curs:
        curs.execute(query_by_tag, (tag,))
        result = curs.fetchall()
        
    if result:
        images = [im[0] for im in result]
        imageChoice = choice(images)
        success = "1"
    else:
        query_random_filename = """
        SELECT filename
        FROM filename TABLESAMPLE SYSTEM_ROWS(1)"""

        with conn.cursor() as curs:
            curs.execute(query_random_filename)
            imageChoice = curs.fetchone()[0]
            success = "0"

    return(imageChoice, success)


imageChoice, success = query_by_tags("zzz", conn)

print(imageChoice)
print(success)

