import os
from random import choice

import boto3
from psycopg import connect

def boto_ssm(Name, ssm):
    value = ssm.get_parameter(Name=Name,
    WithDecryption=True)["Parameter"]["Value"]
    return(value)

def sql_connect():

    port = 5432
    user = "postgres"
    dbname = "MemeToaster"

    pm2 = os.getenv("PM2_HOME")

    ssm = boto3.client("ssm",region_name="us-west-1")

    if pm2:

        POSTGRESQL_HOST = boto_ssm("POSTGRESQL_HOST_EC2", ssm)
        POSTGRESQL_PASSWORD = boto_ssm("POSTGRESQL_PASSWORD_EC2", ssm)

    else:

        POSTGRESQL_HOST = boto_ssm("POSTGRESQL_HOST_LOCAL", ssm)
        POSTGRESQL_PASSWORD = boto_ssm("POSTGRESQL_PASSWORD_LOCAL", ssm)

    conn = connect(
        host = POSTGRESQL_HOST,
        port = port,
        user = user,
        password = POSTGRESQL_PASSWORD,
        dbname = dbname
    )

    return(conn)


def sql_tags(conn,
             tagsOnly = True):

    if tagsOnly == True:
        query = "SELECT tag FROM tag"
    else:
        query = "SELECT * FROM tag"

    with conn.cursor() as curs:
        curs.execute(query)
        tags = curs.fetchall()

    return(tags)


def sql_tags_counts(conn):

    query_str = """
SELECT tg.tag, count(tf.filename_id)
FROM tag_filename AS tf
LEFT JOIN tag AS tg
ON tf.tag_id = tg.id
WHERE tg.tag <> ''
GROUP BY tg.tag
ORDER BY count(tf.filename_id) DESC, tg.tag;"""

    with conn.cursor() as curs:
        curs.execute(query_str)
        tags = curs.fetchall()

    return(tags)


def log_request(tag, caption, success, conn):

    log_tag_string = """
    INSERT INTO request_log (tag, caption, success)
    VALUES (%s, %s, %s)"""

    with conn.cursor() as curs:
        curs.execute(log_tag_string, (tag, caption, success,))
    conn.commit()


def query_filename_by_tag(tag, conn):
    query_by_tag = """
    SELECT filename FROM filename AS f
        LEFT JOIN tag_filename AS tf
        ON f.id = tf.filename_id
            LEFT JOIN tag
            ON tf.tag_id = tag.id
    WHERE tag.tag = %s;"""

    with conn.cursor() as curs:
        curs.execute(query_by_tag, (tag,))
        result = curs.fetchall()
        
    if result:
        images = [im[0] for im in result]
        imageChoice = choice(images)
        success = "1"
    else:
        with conn.cursor() as curs:
            curs.execute("SELECT filename FROM filename")
            result = curs.fetchall()
            imageChoice = choice(result)[0]
            success = "0"

    return(imageChoice, success)


def query_tag_by_filename(filename, conn):
    query_by_filename = """
SELECT tag FROM tag as tg
LEFT JOIN tag_filename AS tf
ON tg.id = tf.tag_id
LEFT JOIN filename AS f
ON tf.filename_id = f.id
WHERE f.filename = %s;"""

    with conn.cursor() as curs:
        curs.execute(query_by_filename, (filename,))
        result = curs.fetchall()

    if result:
        tags = [tg[0] for tg in result]
    else:
        tags = []

    return(tags)





def create_tag_list(conn):

    ##### Create tags list
    tagsList = sql_tags_counts(conn = conn)

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(id) FROM tag;")
        num_tags = cur.fetchone()[0]
        cur.execute("SELECT COUNT(id) FROM filename;")
        num_pics = cur.fetchone()[0]

    # Write to StringIO, Create S3 session, and upload
    inptstr = 'data/tags.txt'
    with open(inptstr, 'w') as newfile:

        newfile.write(f"Number of tags: {num_tags}\n\n")
        newfile.write(f"Total number of pictures: {num_pics}\n\n")
        newfile.write("Number of pictures per tag:\n\n")

        for tag, count in tagsList:
            newfile.write(f"{tag}\n{count}\n\n")

conn = sql_connect()
create_tag_list(conn)
conn.close()