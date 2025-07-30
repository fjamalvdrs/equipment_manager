import streamlit as st
import urllib
import pandas as pd
from sqlalchemy import create_engine

# --- Engines for both databases ---
def get_engine_testdb():
    db_server = st.secrets["DB_SERVER"]
    db_user = st.secrets["DB_USER"]
    db_password = st.secrets["DB_PASSWORD"]
    db_name = st.secrets["DB_TESTDB"]
    params = urllib.parse.quote_plus(
        f"Driver={{ODBC Driver 17 for SQL Server}};"
        f"Server={db_server};"
        f"Database={db_name};"
        f"Uid={db_user};"
        f"Pwd={db_password};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )
    return create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

def get_engine_powerapps():
    db_server = st.secrets["DB_SERVER"]
    db_user = st.secrets["DB_USER"]
    db_password = st.secrets["DB_PASSWORD"]
    db_name = st.secrets["DB_POWERAPPS"]
    params = urllib.parse.quote_plus(
        f"Driver={{ODBC Driver 17 for SQL Server}};"
        f"Server={db_server};"
        f"Database={db_name};"
        f"Uid={db_user};"
        f"Pwd={db_password};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )
    return create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
