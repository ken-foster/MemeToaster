import itertools
from data import *

server = ssh_connect()
server.start()

conn = sql_connect(server)

### CODE IN HERE ###

tags = ["dad","sleep"]

query = """
SELECT filename
FROM filename AS f
	LEFT JOIN tag_filename AS tf
	ON f.id = tf.filename_id
		LEFT JOIN tag
		ON tf.tag_id = tag.id
WHERE tag.tag = 'letsgo'
OR tag.tag = 'shades'
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
		WHERE tag.tag = 'letsgo'
		OR tag.tag = 'shades'
		GROUP BY f.filename ) sub);"""

query_pt1 = """
SELECT filename
FROM filename AS f
	LEFT JOIN tag_filename AS tf
	ON f.id = tf.filename_id
		LEFT JOIN tag
		ON tf.tag_id = tag.id
"""

or_sections = " OR ".join(["tag.tag = %s"]*len(tags))
where_clause = "WHERE " + or_sections

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

# WHERE clause

query_pt3 = """
GROUP BY f.filename) sub)"""

full_query = query_pt1 + where_clause + query_pt2 + where_clause + query_pt3

with conn.cursor() as curs:
    curs.execute(full_query, tuple(tags*2))
    result = curs.fetchall()

print(result)


### CODE IN HERE ###

conn.close()
server.stop()

