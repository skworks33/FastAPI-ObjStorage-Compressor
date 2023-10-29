# providers/database.py

import mysql.connector
from fastapi import HTTPException

from common.config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME

def get_mysql_connection():
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return connection
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database connection error: {err}")
