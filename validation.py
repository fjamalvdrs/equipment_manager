import pandas as pd
import datetime

def validate_row(row, required_fields, field_types, autocomplete_fields=None, autocomplete_values=None):
    """
    Validate a single row of data.
    - required_fields: list of required field names
    - field_types: dict of field_name: type (e.g., 'int', 'float', 'date', 'str')
    - autocomplete_fields: list of fields with autocomplete
    - autocomplete_values: dict of field_name: set of valid values
    Returns: (is_valid, error_message)
    """
    for field in required_fields:
        if pd.isnull(row.get(field)) or row.get(field) == '':
            return False, f"Field '{field}' is required."
    for field, dtype in field_types.items():
        value = row.get(field)
        if pd.isnull(value) or value == '':
            continue  # Allow nulls for non-required fields
        if dtype == 'int':
            try:
                int(value)
            except Exception:
                return False, f"Field '{field}' must be an integer."
        elif dtype == 'float':
            try:
                float(value)
            except Exception:
                return False, f"Field '{field}' must be a float."
        elif dtype == 'date':
            try:
                if not isinstance(value, (datetime.date, pd.Timestamp)):
                    pd.to_datetime(value)
            except Exception:
                return False, f"Field '{field}' must be a date."
    if autocomplete_fields and autocomplete_values:
        for field in autocomplete_fields:
            if field in row and row[field] not in autocomplete_values.get(field, set()):
                return False, f"Field '{field}' value '{row[field]}' is not a valid option."
    return True, ""

def enforce_data_types(df, field_types):
    """
    Enforce data types on a DataFrame according to field_types dict.
    """
    for field, dtype in field_types.items():
        if field not in df.columns:
            continue
        if dtype == 'int':
            df[field] = pd.to_numeric(df[field], errors='coerce').astype('Int64')
        elif dtype == 'float':
            df[field] = pd.to_numeric(df[field], errors='coerce')
        elif dtype == 'date':
            df[field] = pd.to_datetime(df[field], errors='coerce')
        # else: leave as string
    return df 