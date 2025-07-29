import urllib
import os
import pandas as pd
from sqlalchemy import create_engine

# --- Engines for both databases ---
def get_engine_testdb():
    db_server = os.getenv("DB_SERVER", "vdrsapps.database.windows.net")
    db_user = os.getenv("DB_USER", "VDRSAdmin")
    db_password = os.getenv("DB_PASSWORD", "Oz01%O0wi")
    db_name = "testDB"
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
    db_server = os.getenv("DB_SERVER", "vdrsapps.database.windows.net")
    db_user = os.getenv("DB_USER", "VDRSAdmin")
    db_password = os.getenv("DB_PASSWORD", "Oz01%O0wi")
    db_name = "PowerAppsDatabase"
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

# --- CRUD on testDB.dbo.EquipmentDB ---
def insert_or_update_equipment(row, table="dbo.EquipmentDB", key_fields=["ProjectNumber", "EquipmentSerial"]):
    engine = get_engine_testdb()
    where_clause = " AND ".join([f"[{k}] = ?" for k in key_fields])
    select_query = f"SELECT * FROM [{table}] WHERE {where_clause}"
    existing = pd.read_sql(select_query, engine, params=tuple(row[k] for k in key_fields))
    if not existing.empty:
        set_clause = ", ".join([f"[{col}] = ?" for col in row.keys() if col not in key_fields])
        update_query = f"UPDATE [{table}] SET {set_clause} WHERE {where_clause}"
        params = tuple([row[col] for col in row.keys() if col not in key_fields] + [row[k] for k in key_fields])
        with engine.begin() as conn:
            conn.execute(update_query, params)
        return 'updated'
    else:
        columns = ", ".join([f"[{col}]" for col in row.keys()])
        placeholders = ", ".join(["?" for _ in row.keys()])
        insert_query = f"INSERT INTO [{table}] ({columns}) VALUES ({placeholders})"
        with engine.begin() as conn:
            conn.execute(insert_query, tuple(row.values()))
        return 'inserted'

def check_duplicate_serial(project_number, serial, table="dbo.EquipmentDB"):
    engine = get_engine_testdb()
    query = f"SELECT COUNT(*) as cnt FROM [{table}] WHERE [ProjectNumber]=? AND [EquipmentSerial]=?"
    df = pd.read_sql(query, engine, params=(project_number, serial))
    return df['cnt'].iloc[0] > 0

def fetch_existing_equipment(project_number, equipment_type=None, table="dbo.EquipmentDB"):
    engine = get_engine_testdb()
    if equipment_type:
        query = f"SELECT * FROM [{table}] WHERE [ProjectNumber]=? AND [EquipmentType]=?"
        df = pd.read_sql(query, engine, params=(project_number, equipment_type))
    else:
        query = f"SELECT * FROM [{table}] WHERE [ProjectNumber]=?"
        df = pd.read_sql(query, engine, params=(project_number,))
    return df

# --- Reference data from PowerAppsDatabase views ---
def fetch_frequent_values(table, field):
    engine = get_engine_powerapps()
    query = f"SELECT DISTINCT [{field}] FROM [{table}] WHERE [{field}] IS NOT NULL ORDER BY [{field}]"
    df = pd.read_sql(query, engine)
    return df[field].dropna().tolist()

def fetch_equipment_specs(equipment_type):
    engine = get_engine_powerapps()
    query = f"SELECT * FROM [dbo].[vw_MappedEquipmentSpecs] WHERE [EquipmentType] = ?"
    df = pd.read_sql(query, engine, params=(equipment_type,))
    return df

def fetch_project_manufacturer(project_number, table="Projects"):
    engine = get_engine_powerapps()
    query = f"SELECT [Manufacturer] FROM [{table}] WHERE [ProjectNumber]=?"
    df = pd.read_sql(query, engine, params=(project_number,))
    if not df.empty:
        return df['Manufacturer'].iloc[0]
    return None 