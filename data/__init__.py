import itertools
import os
from random import choice
import string

import boto3
from psycopg import connect
from sshtunnel import SSHTunnelForwarder


with open("data/stopwords.txt") as file:
    stopwords = file.readlines()


def filter_stopwords(tags: list) -> list:

    # Filter stopwords
    tags_filtered = [tag for tag in tags if not tag in stopwords]

    # Return
    return(tags_filtered)


def boto_ssm(Name, ssm):
    value = ssm.get_parameter(Name=Name,
    WithDecryption=True)["Parameter"]["Value"]
    return(value)


def ssh_connect():
    ssm = boto3.client("ssm",region_name="us-west-1")

    EC2_HOST = boto_ssm("EC2_HOST", ssm)
    POSTGRESQL_HOST = boto_ssm("POSTGRESQL_HOST_EC2", ssm)

    print("creating ssh tunnel")
    server = SSHTunnelForwarder(
        ssh_address_or_host=(EC2_HOST, 22),
        ssh_username="ubuntu",
        ssh_pkey="../MemeToaster.pem",
        remote_bind_address=(POSTGRESQL_HOST, 5432)
    )

    return(server)


def sql_connect(server=None):

    port = 5432
    user = "postgres"
    dbname = "MemeToaster"

    pm2 = os.getenv("PM2_HOME")

    ssm = boto3.client("ssm",region_name="us-west-1")

    POSTGRESQL_HOST = boto_ssm("POSTGRESQL_HOST_EC2", ssm)
    POSTGRESQL_PASSWORD = boto_ssm("POSTGRESQL_PASSWORD_EC2", ssm)

    if pm2: # connect directly

        conn = connect(
            host = POSTGRESQL_HOST,
            port = port,
            user = user,
            password = POSTGRESQL_PASSWORD,
            dbname = dbname
        )

    else: # Incorporate port forwarding

        conn = connect(
            host = "localhost",
            port = server.local_bind_port,
            user = user,
            password = POSTGRESQL_PASSWORD,
            dbname = dbname)



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


def log_error(code, msg, conn) -> None:
    log_error_string = """
    INSERT INTO error_log (code, msg)
    VALUES (%s, %s)"""

    with conn.cursor() as curs:
        curs.execute(log_error_string, (code, msg,))
    
    conn.commit()


def log_request(tags, caption, success, conn) -> None:

    # Query for retrieving last request_id
    request_id_string = """
    SELECT request_id
    FROM request_log
    ORDER BY id DESC
    LIMIT 1"""

    # Query for entering a new log entry
    log_tag_string = """
    INSERT INTO request_log (tag, caption, success, request_id)
    VALUES (%s, %s, %s, %s)"""

    with conn.cursor() as curs:
        curs.execute(request_id_string)
        request_id = str(curs.fetchone()[0] + 1)

        for tag in tags:
            curs.execute(log_tag_string, (tag, caption, success, request_id,))
    conn.commit()


def query_single_tag(tag, agerestrict, conn):
    query_by_tag = """
SELECT filename FROM filename AS f
    LEFT JOIN tag_filename AS tf
    ON f.id = tf.filename_id
        LEFT JOIN tag
        ON tf.tag_id = tag.id
WHERE tag.tag = %s
"""

    if not agerestrict:
        query_by_tag += "AND f.agerestrict = 'false'"

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
        FROM filename TABLESAMPLE BERNOULLI(1)
        WHERE agerestrict = 'false'
        ORDER BY random()
        LIMIT 1"""

        with conn.cursor() as curs:
            curs.execute(query_random_filename)
            imageChoice = curs.fetchone()[0]
            success = "0"

    return(imageChoice, success)


def query_by_tags(tags_requested, agerestrict, conn):

    if len(tags_requested) == 1:
        imageChoice, success = query_single_tag(tags_requested[0], agerestrict, conn)
        return(imageChoice, success)

    elif len(tags_requested) < 1:
        return("ERROR: len(tags) should be > 0")

    else:
        tags_available = set([tg[0] for tg in sql_tags(conn)])

        tags_req_avail = tags_available.intersection(set(tags_requested))
        if len(tags_req_avail) == 0:
            imageChoice, success = query_single_tag("", agerestrict, conn)
            return(imageChoice, success)

        elif len(tags_req_avail) == 1:
            imageChoice, success = query_single_tag(tags_req_avail.pop(), agerestrict, conn)
            return(imageChoice, success)

        else:
            final_tags = [i for i in tags_requested if i in tags_available]

            # Assemble SQL query
            where_clause = "WHERE (" + " OR ".join(["tag.tag = %s"]*len(final_tags)) + ")"

            if not agerestrict:
                where_clause += "AND f.agerestrict = 'false'"
            

            query_pt1 = """
            SELECT filename
            FROM filename AS f
                LEFT JOIN tag_filename AS tf
                ON f.id = tf.filename_id
                    LEFT JOIN tag
                    ON tf.tag_id = tag.id
            """

            query_pt2 = """
            GROUP BY f.filename
            HAVING COUNT(filename) = (
                SELECT MAX(sub.count_filename)
                FROM (
                    SELECT filename, count(filename) as count_filename
                    FROM filename AS f
                        LEFT JOIN tag_filename AS tf
                        ON f.id = tf.filename_id
                            LEFT JOIN tag
                            ON tf.tag_id = tag.id
            """

            query_pt3 = """
            GROUP BY f.filename) sub)"""

            final_query = query_pt1 + where_clause + query_pt2 + where_clause + query_pt3

            with conn.cursor() as curs:
                curs.execute(final_query, tuple(final_tags*2))
                result = curs.fetchall()

            if result:
                imageChoice = choice(
                    [im[0] for im in result]
                )
                success = "1"
            else:
                query_random_filename = """
                SELECT filename
                FROM filename TABLESAMPLE BERNOULLI(1)
                ORDER BY random()
                LIMIT 1;"""

                with conn.cursor() as curs:
                    curs.execute(query_random_filename)
                    imageChoice = curs.fetchone()[0]
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


"""
pm2 = os.getenv("PM2_HOME")

if pm2:
    conn = sql_connect()
else:
    server = ssh_connect()
    server.start()

    conn = sql_connect(server)


create_tag_list(conn)
conn.close()
if not pm2:
    server.stop()
"""