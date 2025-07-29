import os
"""
Shared Configuration and Utilities
=================================

Common configuration, utilities, and functions used across all modules.

Version: 5.0 - Modular Architecture
"""

import streamlit as st
import pandas as pd
import logging
from typing import Dict, List, Optional, Any

# Import database utilities
from db_utils import get_engine_testdb, get_engine_powerapps

class Config:
    """Application configuration and constants"""
    
    # Fixed fields that apply to all equipment entries
    FIXED_FIELDS = [
        'CustomerID', 'CustomerName', 'CustomerLocation', 'ActiveStatus', 
        'Manufacturer', 'ManufacturerProjectID', 'ParentProjectID'
    ]
    
    # Equipment fields that appear between SerialNumber and Specifications
    EQUIPMENT_FIELDS = [
        'OtherOrPreviousPosition', 'CustomerPositionNo', 'YearManufactured', 
        'SalesDateWarrantyStartDate', 'InstallDate', 'Manufacturer', 
        'ManufacturerProjectID', 'ParentProjectID', 'EquipmentType', 
        'FunctionalType', 'FunctionalPosition', 'ManufacturerModelDescription', 'Model'
    ]
    
    # Additional fields from the actual table structure
    ADDITIONAL_FIELDS = ['Notes', 'EquipmentKey', 'RecordHistory']
    
    # Network visualization settings
    MAX_MACHINES_CIRCULAR = 50
    NETWORK_HEIGHT = "800px"
    NETWORK_WIDTH = "100%"
    CUSTOMER_RADIUS = 400
    PROJECT_RADIUS = 250
    MACHINE_RADIUS = 150
    MANUFACTURER_RADIUS = 50

def get_user_identity() -> str:
    """Get current user identity for logging purposes"""
    return (st.session_state.get('EngineerName') or 
            os.getenv('USERNAME') or 
            os.getenv('USER') or 
            'Unknown')

def initialize_session_state():
    """Initialize all session state variables"""
    defaults = {
        'fixed_fields_set': False,
        'selected_equipment_type': '',
        'equipment_data': pd.DataFrame(),
        'paste_data': [],
        'auto_populated_fields': {}
    }
    
    # Add all fixed fields
    for field in Config.FIXED_FIELDS:
        defaults[field] = ''
    
    # Initialize all defaults
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

def find_equipment_table_name() -> Optional[str]:
    """Find the correct equipment table name in the database"""
    try:
        engine = get_engine_testdb()
        
        # First, try the exact table name we know exists
        try:
            test_query = "SELECT TOP 1 * FROM [dbo].[EquipmentDB]"
            pd.read_sql(test_query, engine)
            return "EquipmentDB"  # Found it!
        except:
            pass
        
        # Check for equipment tables with different cases
        tables_query = """
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE' 
            AND LOWER(TABLE_NAME) LIKE '%equipment%'
            ORDER BY TABLE_NAME
        """
        available_tables = pd.read_sql(tables_query, engine)
        
        if not available_tables.empty:
            return available_tables['TABLE_NAME'].iloc[0]
        
        # Try common variations with different cases
        possible_names = ['EquipmentDB', 'equipmentDB', 'equipment', 'Equipment', 'EQUIPMENT', 'EquipmentTable']
        for name in possible_names:
            try:
                test_query = f"SELECT TOP 1 * FROM [dbo].[{name}]"
                pd.read_sql(test_query, engine)
                return name
            except:
                continue
        
        return None
        
    except Exception as e:
        logging.error(f"Failed to find equipment table: {str(e)}")
        return None

def test_database_connections() -> Dict[str, bool]:
    """Test both database connections"""
    results = {}
    
    try:
        engine_test = get_engine_testdb()
        pd.read_sql("SELECT 1 as test", engine_test)
        results['testdb'] = True
    except Exception as e:
        results['testdb'] = False
        logging.error(f"TestDB connection failed: {str(e)}")
    
    try:
        engine_power = get_engine_powerapps()
        pd.read_sql("SELECT 1 as test", engine_power)
        results['powerapps'] = True
    except Exception as e:
        results['powerapps'] = False
        logging.error(f"PowerApps connection failed: {str(e)}")
    
    return results

def auto_populate_field(field_name: str, field_value: str) -> Dict[str, str]:
    """Auto-populate related fields based on a single field"""
    if not field_value.strip():
        return {}
        
    try:
        engine = get_engine_testdb()
        
        # Find correct table name
        table_name = find_equipment_table_name()
        if not table_name:
            st.warning("⚠️ Could not find equipment table for auto-population")
            return {}
        
        auto_filled = {}
        
        if field_name == 'CustomerID':
            query = f"SELECT TOP 1 CustomerName, CustomerLocation, Manufacturer FROM [dbo].[{table_name}] WHERE CustomerID = ?"
        elif field_name == 'CustomerName':
            query = f"SELECT TOP 1 CustomerID, CustomerLocation, Manufacturer FROM [dbo].[{table_name}] WHERE CustomerName = ?"
        elif field_name == 'ParentProjectID':
            query = f"SELECT TOP 1 CustomerID, CustomerName, CustomerLocation, Manufacturer FROM [dbo].[{table_name}] WHERE ParentProjectID = ?"
        else:
            return {}
        
        result = pd.read_sql(query, engine, params=(field_value,))
        
        if not result.empty:
            for col in result.columns:
                if pd.notna(result[col].iloc[0]) and not st.session_state.get(col, ''):
                    st.session_state[col] = str(result[col].iloc[0])
                    auto_filled[col] = str(result[col].iloc[0])
        
        return auto_filled
        
    except Exception as e:
        logging.error(f"Auto-populate failed: {str(e)}")
        return {}

def get_specification_columns() -> Dict[str, str]:
    """Get specification columns for current equipment type"""
    try:
        engine = get_engine_powerapps()
        equipment_type = st.session_state.get('selected_equipment_type', '')
        
        if not equipment_type:
            return {'Specifications1': 'Weight (kg)', 'Specifications2': 'Power (kW)', 'Specifications3': 'Capacity'}
        
        spec_df = pd.read_sql(
            "SELECT * FROM [dbo].[vw_EquipmentType_SpecificationLabels] WHERE EquipmentType = ?",
            engine,
            params=(equipment_type,)
        )
        
        if not spec_df.empty:
            spec_fields = [col for col in spec_df.columns if col.startswith("Specifications")]
            spec_labels = {}
            for field in spec_fields:
                label = spec_df[field].iloc[0]
                if pd.notna(label) and str(label).strip():
                    spec_labels[field] = str(label).strip()
            
            return spec_labels if spec_labels else {
                'Specifications1': 'Weight (kg)', 
                'Specifications2': 'Power (kW)', 
                'Specifications3': 'Capacity'
            }
        else:
            return {
                'Specifications1': 'Weight (kg)', 
                'Specifications2': 'Power (kW)', 
                'Specifications3': 'Capacity'
            }
            
    except Exception as e:
        logging.warning(f"Using default specifications: {str(e)}")
        return {
            'Specifications1': 'Weight (kg)', 
            'Specifications2': 'Power (kW)', 
            'Specifications3': 'Capacity'
        }

def safe_execute(func, *args, **kwargs) -> Any:
    """Execute function with comprehensive error handling"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logging.error(f"Function {func.__name__} failed: {str(e)}")
        st.error(f"Operation failed: {str(e)}")
        return None

def format_date_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Format date columns consistently"""
    if df is None or df.empty:
        return df
        
    try:
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime('%Y-%m-%d')
            elif df[col].dtype == object:
                sample_non_null = df[col].dropna().head(5)
                if not sample_non_null.empty and sample_non_null.astype(str).str.match(r'^\d{4}-\d{2}-\d{2}T').any():
                    df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d')
        return df
    except Exception as e:
        logging.error(f"Date formatting failed: {str(e)}")
        return df

# Export commonly used items
__all__ = [
    'Config',
    'get_user_identity',
    'initialize_session_state', 
    'find_equipment_table_name',
    'test_database_connections',
    'auto_populate_field',
    'get_specification_columns',
    'safe_execute',
    'format_date_columns'
]
