import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

#!/usr/bin/env python3
"""
Simple SQL Server connection helper for the EnchantedBeesDB.
Reads connection info from environment variables:
    DB_SERVER   (default: localhost)
    DB_DATABASE (default: EnchantedBeesDB)
    DB_USER
    DB_PASSWORD
If DB_USER/DB_PASSWORD are not set, uses Trusted_Connection=yes (integrated auth).
"""


def _select_driver():
        available = set(pyodbc.drivers())
        for candidate in (
                "ODBC Driver 18 for SQL Server",
                "ODBC Driver 17 for SQL Server",
                "ODBC Driver 13 for SQL Server",
                "SQL Server"
        ):
                if candidate in available:
                        return candidate
        # fallback to first available driver string (may raise later)
        return next(iter(available), "")

def get_connection():
        """
        Return a pyodbc.Connection to the EnchantedBeesDB.
        Caller is responsible for closing the connection.
        """
        server = os.environ.get("DB_SERVER", "localhost")
        database = os.environ.get("DB_DATABASE", "EnchantedBeesDB")
        user = os.environ.get("DB_USER")
        password = os.environ.get("DB_PASSWORD")

        driver = _select_driver()
        if not driver:
                raise RuntimeError("No ODBC driver found for SQL Server. Install an ODBC driver and try again.")

        if user and password:
                conn_str = (
                        f"DRIVER={{{driver}}};"
                        f"SERVER={server};DATABASE={database};UID={user};PWD={password};"
                        "Encrypt=no;"
                )
        else:
                conn_str = (
                        f"DRIVER={{{driver}}};"
                        f"SERVER={server};DATABASE={database};Trusted_Connection=yes;"
                )

        return pyodbc.connect(conn_str)

def get_table_count(conn, table_name):
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row = cursor.fetchone()
        print(f"{table_name} count:", row[0] if row else 0)
    finally:
        cursor.close()

if __name__ == "__main__":
        conn = get_connection()
        try:
                print("Connected to EnchantedBeesDB on", conn.getinfo(pyodbc.SQL_SERVER_NAME))
                
                get_table_count(conn, "Species")
                get_table_count(conn, "Variant")
                get_table_count(conn, "MatingPair")
                get_table_count(conn, "MatingBaby")
        finally:
                conn.close()