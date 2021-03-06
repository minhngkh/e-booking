import sqlite3


def create_connection(path):
    connection = None
    connection = sqlite3.connect(path)

    return connection


def execute_query(connection, query, return_result=False):
    cursor = connection.cursor()
    cursor.execute(query)
    connection.commit()

    if return_result:
        return cursor.fetchall()
