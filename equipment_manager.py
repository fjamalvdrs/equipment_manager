"""
Equipment Manager Module
=======================

Handles all equipment add/edit functionality including:
- Smart auto-fill from database
- Excel-like data interface with direct paste support
- Complete equipment field management
- Database save operations with audit trail in RecordHistory
- Automatic RowCounter management
- Flexible data loading with OR-based search
- Automatic table name correction

Version: 5.5 - Fixed table name resolution
"""

import streamlit as st
import pandas as pd
import logging
from io import StringIO
from typing import Dict, List, Optional, Any
from sqlalchemy import text  # Added for SQLAlchemy 2.x compatibility
from datetime import datetime

# Import shared utilities
from shared_config import (
    Config, get_user_identity, auto_populate_field, 
    get_specification_columns, find_equipment_table_name
)
from db_utils import get_engine_testdb, fetch_frequent_values



class EquipmentManager:
    """Main equipment management class"""
    
    def __init__(self):
        self.config = Config()
        # Allow manual override of table name via session state
        if 'equipment_table_name_override' not in st.session_state:
            st.session_state.equipment_table_name_override = None
    
    def render(self):
        """Main render method for equipment management"""
        st.title("📝 Equipment Data Manager")
        st.markdown("**Smart equipment data management with auto-fill and Excel-like editing**")
        
        # Progress tracking
        steps_completed = 0
        if st.session_state.get('fixed_fields_set'):
            steps_completed += 1
        if st.session_state.get('selected_equipment_type'):
            steps_completed += 1
        
        st.progress(steps_completed / 2)
        st.caption(f"Setup Progress: {steps_completed}/2 steps completed")
        
        # Step 1: Fixed Fields
        if not st.session_state.get('fixed_fields_set'):
            self._render_fixed_fields_section()
        else:
            # Show completed step 1
            st.success("✅ Step 1 Complete: Common information saved")
            with st.expander("📋 Review Common Information", expanded=False):
                for field in self.config.FIXED_FIELDS:
                    value = st.session_state.get(field, '')
                    if value:
                        st.write(f"**{field}:** {value}")
            
            # Step 2: Equipment Type
            if not st.session_state.get('selected_equipment_type'):
                self._render_equipment_type_selection()
            else:
                # Show completed step 2
                st.success(f"✅ Step 2 Complete: Equipment type - {st.session_state['selected_equipment_type']}")
                
                # Step 3: Equipment Data Management
                st.markdown("---")
                self._render_equipment_data_section()
    
    def _render_fixed_fields_section(self):
        """Render the fixed fields input section"""
        st.markdown("### 📋 Step 1: Enter Common Information")
        st.info("🔮 **Smart Auto-Fill:** Enter any field below to automatically fill related information!")
        
        # Customer Information
        st.markdown("**Customer Information:**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            customer_id = st.text_input(
                "Customer ID", 
                value=st.session_state.get('CustomerID', ''), 
                key='eq_customer_id'
            )
            st.caption("Enter customer ID to auto-fill customer details")
            
            if customer_id != st.session_state.get('CustomerID', '') and customer_id.strip():
                auto_filled = auto_populate_field('CustomerID', customer_id)
                if auto_filled:
                    st.success(f"✅ Auto-filled: {', '.join(f'{k}: {v}' for k, v in auto_filled.items())}")
            
            st.session_state['CustomerID'] = customer_id
        
        with col2:
            customer_name = st.text_input(
                "Customer Name", 
                value=st.session_state.get('CustomerName', ''), 
                key='eq_customer_name'
            )
            st.caption("Enter customer name to auto-fill customer details")
            
            if customer_name != st.session_state.get('CustomerName', '') and customer_name.strip():
                auto_filled = auto_populate_field('CustomerName', customer_name)
                if auto_filled:
                    st.success(f"✅ Auto-filled: {', '.join(f'{k}: {v}' for k, v in auto_filled.items())}")
            
            st.session_state['CustomerName'] = customer_name
        
        with col3:
            st.session_state['CustomerLocation'] = st.text_input(
                "Customer Location", 
                value=st.session_state.get('CustomerLocation', ''), 
                key='eq_customer_location'
            )
            st.caption("Auto-filled from database or enter manually")
        
        # Project Information
        st.markdown("**Project Information:**")
        col1, col2 = st.columns(2)
        
        with col1:
            project_id = st.text_input(
                "Project ID", 
                value=st.session_state.get('ParentProjectID', ''), 
                key='eq_project_id'
            )
            st.caption("Enter project ID to auto-fill project details")
            
            if project_id != st.session_state.get('ParentProjectID', '') and project_id.strip():
                auto_filled = auto_populate_field('ParentProjectID', project_id)
                if auto_filled:
                    st.success(f"✅ Auto-filled: {', '.join(f'{k}: {v}' for k, v in auto_filled.items())}")
            
            st.session_state['ParentProjectID'] = project_id
        
        with col2:
            st.session_state['Manufacturer'] = st.text_input(
                "Manufacturer", 
                value=st.session_state.get('Manufacturer', ''), 
                key='eq_manufacturer'
            )
            st.caption("Auto-filled from database or enter manually")
        
        # Additional fields
        col1, col2 = st.columns(2)
        with col1:
            st.session_state['ManufacturerProjectID'] = st.text_input(
                "Manufacturer Project ID", 
                value=st.session_state.get('ManufacturerProjectID', ''), 
                key='eq_mfg_project'
            )
        with col2:
            st.session_state['ActiveStatus'] = st.text_input(
                "Active Status", 
                value=st.session_state.get('ActiveStatus', ''), 
                key='eq_active_status'
            )
        
        # Save button
        st.markdown("---")
        if st.button("✅ Save Common Information", type="primary", key="save_fixed_fields"):
            filled_fields = sum(1 for field in self.config.FIXED_FIELDS 
                              if st.session_state.get(field, '').strip())
            if filled_fields > 0:
                st.session_state['fixed_fields_set'] = True
                st.success("✅ Common information saved! Proceed to Step 2.")
                st.balloons()
                st.rerun()
            else:
                st.warning("⚠️ Please fill in at least one field before proceeding")
    
    def _render_equipment_type_selection(self):
        """Render equipment type selection"""
        st.markdown("### 🏷️ Step 2: Select Equipment Type")
        st.info("This determines what specification fields are available for your equipment")
        
        with st.spinner("Loading available equipment types..."):
            equipment_types = fetch_frequent_values('vw_EquipmentTypes', 'EquipmentType') or []
        
        if equipment_types:
            selected_type = st.selectbox(
                "Equipment Type",
                equipment_types,
                key='eq_type_select'
            )
            st.caption(f"Selected: {selected_type} - This will determine available specification fields")
            
            if st.button("✅ Confirm Equipment Type", type="primary", key="confirm_eq_type"):
                st.session_state['selected_equipment_type'] = selected_type
                st.success(f"✅ Equipment type confirmed: {selected_type}")
                st.rerun()
        else:
            st.warning("Could not load equipment types from database")
            manual_type = st.text_input("Enter Equipment Type manually:", key='manual_eq_type')
            
            if st.button("✅ Set Equipment Type", type="primary", key="set_manual_eq_type"):
                if manual_type.strip():
                    st.session_state['selected_equipment_type'] = manual_type.upper()
                    st.success(f"✅ Equipment type set: {manual_type.upper()}")
                    st.rerun()
                else:
                    st.error("❌ Please enter an equipment type")
    
    def _render_equipment_data_section(self):
        """Render the main equipment data management section"""
        st.markdown("### 📊 Equipment Data Management")
        st.info("🔮 **Auto-filled fields:** EquipmentType + all information from Step 1")
        
        # Load specification configuration
        spec_labels = get_specification_columns()
        st.success(f"📋 **Specification fields loaded:** {list(spec_labels.values())}")
        
        # Add manual search option
        with st.expander("🔍 Manual Search Options", expanded=False):
            st.markdown("If automatic loading doesn't find your records, try manual search:")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                manual_serial = st.text_input("Search by Serial Number", key="manual_serial_search")
            with col2:
                manual_project = st.text_input("Search by Project ID", key="manual_project_search")
            with col3:
                if st.button("🔍 Search", key="manual_search_btn"):
                    st.session_state['manual_search_triggered'] = True
                    st.rerun()
        
        # Add table name override option
        with st.expander("⚙️ Advanced Settings", expanded=False):
            st.markdown("**Database Table Configuration:**")
            
            current_table = self._get_equipment_table_name()
            st.info(f"Current table: **{current_table}**")
            
            # Quick fix buttons for common table names
            st.markdown("**Quick Fix - Select your table:**")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("EquipmentDB", key="fix_equipmentdb"):
                    st.session_state.equipment_table_name_override = "EquipmentDB"
                    st.rerun()
            with col2:
                if st.button("Equipment", key="fix_equipment"):
                    st.session_state.equipment_table_name_override = "Equipment"
                    st.rerun()
            with col3:
                if st.button("Auto-detect", key="fix_auto"):
                    st.session_state.equipment_table_name_override = None
                    st.rerun()
            
            st.markdown("**Or manually specify:**")
            col1, col2 = st.columns([3, 1])
            with col1:
                override_table = st.text_input(
                    "Override table name (leave empty for auto-detect):",
                    value=st.session_state.get('equipment_table_name_override', ''),
                    key="table_name_override_input",
                    placeholder="e.g., EquipmentDB"
                )
            with col2:
                if st.button("Apply", key="apply_table_override"):
                    st.session_state.equipment_table_name_override = override_table.strip() if override_table.strip() else None
                    st.success("Table name updated!")
                    st.rerun()
        
        # Load existing data
        col1, col2 = st.columns([10, 1])
        with col2:
            if st.button("🔄", key="refresh_data", help="Refresh data from database"):
                st.rerun()
        
        if st.session_state.get('manual_search_triggered'):
            existing_df = self._manual_search_equipment()
            st.session_state['manual_search_triggered'] = False
        else:
            existing_df = self._load_existing_equipment_data()
        
        # Create and display the data grid
        self._render_data_grid(existing_df, spec_labels)
    
    def _manual_search_equipment(self) -> pd.DataFrame:
        """Perform manual search for equipment"""
        try:
            engine = get_engine_testdb()
            table_name = self._get_equipment_table_name()
            
            if not table_name:
                st.error("❌ Could not find equipment table")
                return pd.DataFrame()
            
            conditions = []
            params = {}
            
            if serial := st.session_state.get('manual_serial_search', '').strip():
                conditions.append("[SerialNumber] LIKE :serial")
                params['serial'] = f'%{serial}%'
            
            if project := st.session_state.get('manual_project_search', '').strip():
                conditions.append("([ParentProjectID] LIKE :project OR [ManufacturerProjectID] LIKE :project)")
                params['project'] = f'%{project}%'
            
            if not conditions:
                st.warning("⚠️ Please enter search criteria")
                return pd.DataFrame()
            
            where_clause = " OR ".join(conditions)
            query = text(f"SELECT * FROM [dbo].[{table_name}] WHERE {where_clause} ORDER BY SerialNumber")
            
            with st.spinner("Searching..."):
                result_df = pd.read_sql(query, engine, params=params)
            
            if not result_df.empty:
                st.success(f"✅ Manual search found {len(result_df)} records")
            else:
                st.warning("No records found with manual search criteria")
            
            return result_df
            
        except Exception as e:
            st.error(f"Manual search failed: {str(e)}")
            return pd.DataFrame()
    
    def _get_equipment_table_name(self) -> str:
        """Get the correct equipment table name with fallback"""
        try:
            # Try the dynamic lookup first
            table_name = self._get_equipment_table_name()
            
            # If it returns 'Equipment', correct it to 'EquipmentDB'
            if table_name == 'Equipment':
                table_name = 'EquipmentDB'
                
            return table_name
        except Exception:
            # Fallback to known table name
            return 'EquipmentDB'
    
    def _load_existing_equipment_data(self) -> pd.DataFrame:
        """Load existing equipment data for editing"""
        try:
            engine = get_engine_testdb()
            table_name = find_equipment_table_name()
            
            if not table_name:
                st.error("❌ Could not find equipment table")
                return pd.DataFrame()
            
            st.info(f"📋 **Using table:** dbo.{table_name}")
            
            # Verify table exists and show column info
            try:
                # Get column information
                col_query = text("""
                    SELECT COLUMN_NAME 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = 'dbo' 
                    AND TABLE_NAME = :table_name
                    ORDER BY ORDINAL_POSITION
                """)
                columns_df = pd.read_sql(col_query, engine, params={'table_name': table_name})
                
                with st.expander(f"📊 Table '{table_name}' Structure", expanded=False):
                    st.write(f"**Total Columns:** {len(columns_df)}")
                    st.write("**Column Names:**")
                    # Display columns in a more readable format
                    cols_per_row = 4
                    for i in range(0, len(columns_df), cols_per_row):
                        cols = st.columns(cols_per_row)
                        for j, col in enumerate(cols):
                            if i + j < len(columns_df):
                                col.write(f"• {columns_df.iloc[i + j]['COLUMN_NAME']}")
            except Exception as e:
                st.warning(f"Could not retrieve table structure: {str(e)}")
            
            # Build search criteria - use OR logic for more flexible matching
            conditions = []
            params = {}
            param_counter = 0

            # Check each fixed field individually
            for field in self.config.FIXED_FIELDS:
                value = st.session_state.get(field, '').strip()
                if value and field in ['CustomerID', 'ParentProjectID', 'ManufacturerProjectID']:
                    param_name = f'param_{param_counter}'
                    conditions.append(f"[{field}] = :{param_name}")
                    params[param_name] = value
                    param_counter += 1

            # Also check equipment type
            equipment_type = st.session_state.get('selected_equipment_type', '').strip()
            if equipment_type:
                param_name = f'param_{param_counter}'
                if conditions:
                    equipment_condition = f"[EquipmentType] = :{param_name}"
                else:
                    conditions.append(f"[EquipmentType] = :{param_name}")
                    equipment_condition = None
                params[param_name] = equipment_type
                param_counter += 1
            else:
                equipment_condition = None

            if not conditions:
                st.info("💡 No search criteria - showing empty grid for new entries")
                return pd.DataFrame()

            # Define where_clause from conditions
            where_clause = " OR ".join(conditions)

            # Show debug info for troubleshooting
            with st.expander("🔧 Debug: Search Criteria Used", expanded=False):
                st.write("**Search Parameters:**")
                for field in self.config.FIXED_FIELDS:
                    value = st.session_state.get(field, '')
                    if value:
                        st.write(f"- {field}: '{value}'")

                equipment_type = st.session_state.get('selected_equipment_type', '')
                if equipment_type:
                    st.write(f"- EquipmentType: '{equipment_type}'")

                st.write("\n**SQL Where Clause:**")
                st.code(where_clause)
                st.write("\n**Parameters:**")
                st.json(params)

            query = text(f"SELECT * FROM [dbo].[{table_name}] WHERE {where_clause} ORDER BY SerialNumber")
            
            with st.spinner("Loading existing equipment data..."):
                existing_df = pd.read_sql(query, engine, params=params)
            
            if not existing_df.empty:
                st.success(f"✅ Loaded {len(existing_df)} existing records for editing")
                
                # Show a preview of what was loaded
                with st.expander(f"📊 Found {len(existing_df)} existing records", expanded=False):
                    preview_cols = ['SerialNumber', 'EquipmentType', 'Model', 'CustomerPositionNo']
                    available_cols = [col for col in preview_cols if col in existing_df.columns]
                    if available_cols:
                        st.dataframe(existing_df[available_cols], use_container_width=True)
            else:
                st.info("🔍 No existing records found - ready for new data entry")
            
            return existing_df
            
        except Exception as e:
            st.error(f"Failed to load existing data: {str(e)}")
            logging.error(f"Load existing data failed: {str(e)}")
            
            # Try a more basic query as fallback
            try:
                st.warning("⚠️ Trying alternative search method...")
                
                # Just try to load by ParentProjectID or CustomerID
                fallback_conditions = []
                fallback_params = {}
                
                if project_id := st.session_state.get('ParentProjectID', '').strip():
                    fallback_conditions.append("[ParentProjectID] = :project_id")
                    fallback_params['project_id'] = project_id
                
                if customer_id := st.session_state.get('CustomerID', '').strip():
                    fallback_conditions.append("[CustomerID] = :customer_id")
                    fallback_params['customer_id'] = customer_id
                
                if fallback_conditions:
                    fallback_where = " OR ".join(fallback_conditions)
                    fallback_query = text(f"SELECT * FROM [dbo].[{table_name}] WHERE {fallback_where} ORDER BY SerialNumber")
                    existing_df = pd.read_sql(fallback_query, engine, params=fallback_params)
                    
                    if not existing_df.empty:
                        st.success(f"✅ Found {len(existing_df)} records using alternative search")
                        return existing_df
                        
            except Exception as fallback_error:
                st.error(f"Alternative search also failed: {str(fallback_error)}")
            
            return pd.DataFrame()
    
    def _render_data_grid(self, existing_df: pd.DataFrame, spec_labels: Dict[str, str]):
        """Render the main data grid"""
        st.markdown("### 📊 Equipment Data Grid")
        
        # Show data loading info
        if not existing_df.empty:
            st.info(f"""
            📌 **Data Loading:** Found {len(existing_df)} existing records based on your search criteria.
            - These records are loaded in the grid below for editing
            - Any changes you make will update the existing records
            - Empty rows at the bottom are for adding new equipment
            """)
        
        # Help section for Excel paste
        with st.expander("📋 How to paste data from Excel", expanded=False):
            st.markdown("""
            **To paste data from Excel:**
            1. Copy your data from Excel (including headers if needed)
            2. Click on the first cell where you want to paste
            3. Press **Ctrl+V** (or Cmd+V on Mac) to paste
            
            **💡 Tips:**
            - The grid will automatically expand if you paste more rows than available
            - Auto-filled fields (EquipmentType, Customer info) will be preserved
            - You can paste partial data - empty columns will remain empty
            - Use Tab/Enter to navigate between cells like in Excel
            """)
        
        # Build complete grid
        grid_df = self._build_complete_grid(existing_df, spec_labels)
        
        if grid_df.empty:
            st.warning("⚠️ No data to display")
            return
        
        # Use st.data_editor for Excel-like experience
        st.markdown("**Excel-like Interface:**")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("- 🔄 **Blue cells** = Auto-filled from Step 1")
            st.markdown("- 📋 **Paste data** = Ctrl+V directly into grid")
        with col2:
            st.markdown("- ➕ **Add/Delete rows** = Use table controls")
            st.markdown("- 📝 **Edit cells** = Click any cell to edit")
        
        # Configure column types (all as text to avoid type conflicts)
        column_config = self._build_column_config(spec_labels)
        
        # Render the data editor
        edited_df = st.data_editor(
            grid_df,
            column_config=column_config,
            num_rows="dynamic",
            use_container_width=True,
            height=600,
            key="equipment_data_editor"
        )
        
        # Save to database
        if st.button("💾 Save All Data to Database", type="primary", key="save_equipment_data"):
            self._save_to_database(edited_df, spec_labels)
    
    def _build_complete_grid(self, existing_df: pd.DataFrame, spec_labels: Dict[str, str]) -> pd.DataFrame:
        """Build the complete data grid"""
        all_rows = []
        
        # Complete column structure
        columns = (['Status', 'SortSystemPosition', 'SerialNumber'] + 
                  self.config.EQUIPMENT_FIELDS + 
                  self.config.ADDITIONAL_FIELDS + 
                  list(spec_labels.values()))
        
        # Add existing records
        if not existing_df.empty:
            for idx, row in existing_df.iterrows():
                grid_row = {'Status': f'🔄#{idx+1}'}
                
                for col in columns[1:]:  # Skip Status
                    if col == 'EquipmentType':
                        # Use the equipment type from the database if available
                        db_value = row.get('EquipmentType', '')
                        if pd.notna(db_value) and str(db_value).strip():
                            grid_row[col] = str(db_value)
                        else:
                            grid_row[col] = st.session_state.get('selected_equipment_type', '')
                    elif col in self.config.FIXED_FIELDS:
                        # For fixed fields, prefer database value over session state
                        db_value = row.get(col, '')
                        session_value = st.session_state.get(col, '')
                        if pd.notna(db_value) and str(db_value).strip():
                            grid_row[col] = str(db_value)
                        elif session_value:
                            grid_row[col] = session_value
                        else:
                            grid_row[col] = ''
                    else:
                        # Map specification columns correctly
                        if col in spec_labels.values():
                            # Find the database column name for this spec label
                            db_col_name = None
                            for db_col, label in spec_labels.items():
                                if label == col:
                                    db_col_name = db_col
                                    break
                            
                            if db_col_name and db_col_name in row:
                                value = row.get(db_col_name, '')
                            else:
                                value = row.get(col, '')
                        else:
                            # Regular columns
                            value = row.get(col, '')
                        
                        # Handle NaN values
                        grid_row[col] = '' if pd.isna(value) else str(value)
                
                all_rows.append(grid_row)
            
            st.info(f"📝 Loaded {len(all_rows)} existing records. You can edit them directly in the grid below.")
        
        # Add empty rows for new data entry
        empty_rows_count = 10 if existing_df.empty else 5  # More rows if starting fresh
        for i in range(empty_rows_count):
            grid_row = {'Status': f'➕{i+1}'}
            
            for col in columns[1:]:
                if col == 'EquipmentType':
                    grid_row[col] = st.session_state.get('selected_equipment_type', '')
                elif col in self.config.FIXED_FIELDS:
                    grid_row[col] = st.session_state.get(col, '')
                else:
                    grid_row[col] = ''
            
            all_rows.append(grid_row)
        
        return pd.DataFrame(all_rows, columns=columns)
    
    def _build_column_config(self, spec_labels: Dict[str, str]) -> Dict:
        """Build column configuration for data editor"""
        column_config = {}
        
        # Status column (read-only)
        column_config['Status'] = st.column_config.TextColumn(
            'Status', disabled=True, width=80
        )
        
        # Basic columns
        column_config['SortSystemPosition'] = st.column_config.TextColumn(
            'Sort Position', max_chars=10
        )
        column_config['SerialNumber'] = st.column_config.TextColumn(
            'Serial Number', max_chars=20
        )
        
        # Fixed fields from Step 1 (make them disabled/read-only)
        for field in self.config.FIXED_FIELDS:
            if field in ['CustomerID', 'CustomerName', 'CustomerLocation', 'ActiveStatus', 
                        'Manufacturer', 'ManufacturerProjectID', 'ParentProjectID']:
                # These come from Step 1, so make them read-only
                column_config[field] = st.column_config.TextColumn(
                    field, disabled=True, help='Set in Step 1'
                )
        
        # Equipment fields (EquipmentType disabled as it's auto-filled)
        equipment_configs = {
            'EquipmentType': st.column_config.TextColumn('Equipment Type', disabled=True, help='Set in Step 2'),
            'OtherOrPreviousPosition': st.column_config.TextColumn('Other/Previous Position', max_chars=30),
            'CustomerPositionNo': st.column_config.TextColumn('Customer Position No', max_chars=20),
            'YearManufactured': st.column_config.TextColumn('Year Manufactured', max_chars=4),
            'Model': st.column_config.TextColumn('Model', max_chars=50),
            'SalesDateWarrantyStartDate': st.column_config.TextColumn('Sales/Warranty Date', max_chars=20),
            'InstallDate': st.column_config.TextColumn('Install Date', max_chars=20),
            'FunctionalType': st.column_config.TextColumn('Functional Type', max_chars=50),
            'FunctionalPosition': st.column_config.TextColumn('Functional Position', max_chars=50),
            'ManufacturerModelDescription': st.column_config.TextColumn('Manufacturer Model Desc', max_chars=100),
        }
        
        column_config.update(equipment_configs)
        
        # Additional fields
        additional_configs = {
            'Notes': st.column_config.TextColumn('Notes', max_chars=200),
            'EquipmentKey': st.column_config.TextColumn('Equipment Key', max_chars=50),
            'RecordHistory': st.column_config.TextColumn('Record History', max_chars=500, help='Audit trail - auto-updated on save')
        }
        
        column_config.update(additional_configs)
        
        # Specification columns
        for spec_label in spec_labels.values():
            column_config[spec_label] = st.column_config.TextColumn(
                spec_label, max_chars=50
            )
        
        return column_config
    
    def _check_column_exists(self, engine, table_name: str, column_name: str) -> bool:
        """Check if a column exists in the table"""
        try:
            query = text("""
                SELECT COUNT(*) as cnt
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = 'dbo' 
                AND TABLE_NAME = :table_name 
                AND COLUMN_NAME = :column_name
            """)
            result = pd.read_sql(query, engine, params={
                'table_name': table_name,
                'column_name': column_name
            })
            return result['cnt'].iloc[0] > 0
        except Exception:
            return False
    
    def _get_next_row_counter(self, engine, table_name: str) -> int:
        """Get the next available RowCounter value"""
        try:
            query = text(f"SELECT ISNULL(MAX([RowCounter]), 0) + 1 as next_counter FROM [dbo].[{table_name}]")
            result = pd.read_sql(query, engine)
            return int(result['next_counter'].iloc[0])
        except Exception:
            return 1  # Start from 1 if table is empty or error occurs
    
    def _save_to_database(self, edited_df: pd.DataFrame, spec_labels: Dict[str, str]):
        """Save edited data to database"""
        try:
            table_name = self._get_equipment_table_name()
            if not table_name:
                st.error("❌ Could not find equipment table")
                return
            
            engine = get_engine_testdb()
            success_count = 0
            errors = []
            
            # Check if RowCounter exists
            has_row_counter = self._check_column_exists(engine, table_name, 'RowCounter')
            
            st.info("💾 **Saving to database...**")
            st.caption("Audit trail: User identity and timestamp will be added to RecordHistory")
            if has_row_counter:
                st.caption("RowCounter: Automatically assigned for new records")
            
            for idx, row in edited_df.iterrows():
                try:
                    # Skip empty rows
                    if not any(str(row.get(col, '')).strip() for col in edited_df.columns if col != 'Status'):
                        continue
                    
                    # Build database record
                    record = {}
                    
                    # Add all fields
                    for field in self.config.FIXED_FIELDS:
                        record[field] = st.session_state.get(field, '')
                    
                    record['SortSystemPosition'] = str(row.get('SortSystemPosition', ''))
                    record['SerialNumber'] = str(row.get('SerialNumber', ''))
                    
                    for eq_field in self.config.EQUIPMENT_FIELDS:
                        record[eq_field] = str(row.get(eq_field, ''))
                    
                    for add_field in self.config.ADDITIONAL_FIELDS:
                        if add_field == 'RecordHistory':
                            # Append edit info to RecordHistory
                            existing_history = str(row.get(add_field, '')).strip()
                            user_identity = get_user_identity()
                            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            edit_info = f"[{timestamp}] Edited by: {user_identity}"
                            
                            if existing_history:
                                record[add_field] = existing_history + '\n' + edit_info
                            else:
                                record[add_field] = edit_info
                        else:
                            record[add_field] = str(row.get(add_field, ''))
                    
                    for spec_field, spec_label in spec_labels.items():
                        if str(row.get(spec_label, '')).strip():
                            record[spec_field] = str(row[spec_label])
                    
                    # Direct database operation
                    self._direct_database_save(engine, table_name, record)
                    success_count += 1
                    
                except Exception as e:
                    errors.append(f"Row {idx+1}: {str(e)}")
                    logging.error(f"Save row {idx} failed: {str(e)}")
            
            # Show results
            if success_count > 0:
                st.success(f"🎉 Successfully saved {success_count} records!")
                logging.info(f"Equipment Manager: User saved {success_count} records")
            
            if errors:
                st.error(f"❌ {len(errors)} errors occurred:")
                for error in errors[:3]:
                    st.write(f"• {error}")
                if len(errors) > 3:
                    st.write(f"... and {len(errors)-3} more errors")
            
        except Exception as e:
            st.error(f"❌ Save operation failed: {str(e)}")
            logging.error(f"Equipment save failed: {str(e)}")
    
    def _direct_database_save(self, engine, table_name: str, record: Dict[str, Any]):
        """Direct database save operation - Fixed for SQLAlchemy 2.x"""
        # Check if RowCounter column exists
        has_row_counter = self._check_column_exists(engine, table_name, 'RowCounter')
        
        # Check if record exists
        check_query = text(f"SELECT COUNT(*) as cnt FROM [dbo].[{table_name}] WHERE [SerialNumber] = :serial_number")
        exists_result = pd.read_sql(check_query, engine, params={'serial_number': record['SerialNumber']})
        record_exists = exists_result['cnt'].iloc[0] > 0
        
        if record_exists:
            # For UPDATE: Fetch existing RecordHistory and append to it
            history_query = text(f"SELECT [RecordHistory] FROM [dbo].[{table_name}] WHERE [SerialNumber] = :serial_number")
            history_result = pd.read_sql(history_query, engine, params={'serial_number': record['SerialNumber']})
            
            if not history_result.empty and 'RecordHistory' in record:
                existing_history = history_result['RecordHistory'].iloc[0] or ''
                existing_history = str(existing_history).strip()
                
                # Extract just the new edit info (last line with timestamp)
                new_history = record['RecordHistory']
                if '[' in new_history and '] Edited by:' in new_history:
                    # Find the last edit entry
                    lines = new_history.split('\n')
                    new_edit_line = lines[-1]  # Get the last line which should be the new edit
                    
                    # Combine existing history with new edit
                    if existing_history:
                        record['RecordHistory'] = existing_history + '\n' + new_edit_line
                    else:
                        record['RecordHistory'] = new_edit_line
            
            # UPDATE - Don't update RowCounter
            set_clauses = []
            update_params = {}
            
            for key, value in record.items():
                if key not in ['SerialNumber', 'RowCounter']:  # Exclude RowCounter from updates
                    set_clauses.append(f"[{key}] = :{key}")
                    update_params[key] = value
            
            update_params['serial_number'] = record['SerialNumber']
            
            update_query = text(f"UPDATE [dbo].[{table_name}] SET {', '.join(set_clauses)} WHERE [SerialNumber] = :serial_number")
            
            with engine.begin() as conn:
                conn.execute(update_query, update_params)
        else:
            # INSERT - Add RowCounter if column exists
            if has_row_counter:
                next_row_counter = self._get_next_row_counter(engine, table_name)
                record['RowCounter'] = next_row_counter
            
            columns = ", ".join([f"[{col}]" for col in record.keys()])
            placeholders = ", ".join([f":{col}" for col in record.keys()])
            insert_query = text(f"INSERT INTO [dbo].[{table_name}] ({columns}) VALUES ({placeholders})")
            
            with engine.begin() as conn:
                conn.execute(insert_query, record)