# Equipment Manager Module (V7, Fixed Duplicate Save Issue + Fixed Data Fetching)
import streamlit as st
import pandas as pd
import logging
import hashlib
from sqlalchemy import text
from datetime import datetime
from shared_config import (
    Config, get_user_identity, auto_populate_field, 
    get_specification_columns, find_equipment_table_name
)
from db_utils import get_engine_testdb, fetch_frequent_values

SQL_COLUMN_ORDER = [
    'CustomerID', 'CustomerName', 'CustomerLocation', 'ActiveStatus', 'SortSystemPosition',
    'SerialNumber', 'OtherOrPreviousPosition', 'CustomerPositionNo', 'YearManufactured', 'SalesDateWarrantyStartDate',
    'InstallDate', 'Manufacturer', 'ManufacturerProjectID', 'ParentProjectID', 'EquipmentType',
    'FunctionalType', 'FunctionalPosition', 'ManufacturerModelDescription', 'Model',
] + [f'Specifications{i}' for i in range(1, 51)] + [
    'Notes', 'EquipmentKey', 'RecordHistory',
    'RowCounter', 'MachineInfoID', 'UploadsPendingID', 'HashedSerialNumber'
]
FULL_COLUMN_ORDER = ['Status', 'RowID'] + SQL_COLUMN_ORDER

class EquipmentManager:
    def __init__(self):
        self.config = Config()
        if 'equipment_table_name_override' not in st.session_state:
            st.session_state.equipment_table_name_override = None
        if 'original_data_hash' not in st.session_state:
            st.session_state.original_data_hash = {}

    def render(self):
        st.title("📝 Equipment Manager")
        
        steps_completed = 0
        if st.session_state.get('fixed_fields_set'): steps_completed += 1
        if st.session_state.get('selected_equipment_type'): steps_completed += 1
        st.progress(steps_completed / 2)
        
        if not st.session_state.get('fixed_fields_set'):
            self._render_fixed_fields_section()
        else:
            if not st.session_state.get('selected_equipment_type'):
                self._render_equipment_type_selection()
            else:
                st.markdown("---")
                self._render_equipment_data_section()

    def _fetch_specification_labels(self, equipment_type: str) -> dict:
        """Fetch specification labels for given equipment type with column mapping"""
        try:
            from db_utils import get_engine_powerapps
            engine = get_engine_powerapps()
            
            query = text("SELECT * FROM [dbo].[vw_EquipmentType_SpecificationLabels] WHERE [EquipmentType] = :equipment_type")
            result = pd.read_sql(query, engine, params={'equipment_type': equipment_type})
            
            if not result.empty:
                # Try common column names
                for label_col in ['SpecificationLabel', 'Label', 'Specification', 'Name']:
                    if label_col in result.columns:
                        spec_mapping = {}
                        for i, label in enumerate(result[label_col].tolist(), 1):
                            spec_mapping[label] = f'Specifications{i}'
                        return spec_mapping
            
            return {}
        except Exception:
            return {}

    def _get_dynamic_columns(self, equipment_type: str = None) -> tuple:
        """Get column order with equipment-specific specification labels and mapping"""
        base_columns = [
            'CustomerID', 'CustomerName', 'CustomerLocation', 'ActiveStatus', 'SortSystemPosition',
            'SerialNumber', 'OtherOrPreviousPosition', 'CustomerPositionNo', 'YearManufactured', 'SalesDateWarrantyStartDate',
            'InstallDate', 'Manufacturer', 'ManufacturerProjectID', 'ParentProjectID', 'EquipmentType',
            'FunctionalType', 'FunctionalPosition', 'ManufacturerModelDescription', 'Model'
        ]
        
        end_columns = [
            'Notes', 'EquipmentKey', 'RecordHistory',
            'RowCounter', 'MachineInfoID', 'UploadsPendingID', 'HashedSerialNumber'
        ]
        
        spec_mapping = {}
        if equipment_type:
            spec_mapping = self._fetch_specification_labels(equipment_type)
            if spec_mapping:
                display_columns = base_columns + list(spec_mapping.keys()) + end_columns
                return display_columns, spec_mapping
        
        # Fallback to generic specifications
        fallback_columns = base_columns + [f'Specifications{i}' for i in range(1, 21)] + end_columns
        return fallback_columns, {}

    def _fetch_customer_projects(self, customer_id: str = None, customer_name: str = None) -> list:
        """Fetch projects for specific customer, with fallback to all projects"""
        try:
            engine = get_engine_testdb()
            table_name = 'EquipmentDB'  # Fixed table name
            
            # First try customer-filtered results
            if customer_id or customer_name:
                conditions = []
                params = {}
                
                if customer_id:
                    conditions.append("[CustomerID] = :customer_id")
                    params['customer_id'] = customer_id
                if customer_name:
                    conditions.append("[CustomerName] = :customer_name") 
                    params['customer_name'] = customer_name
                    
                where_clause = " AND ".join(conditions)
                query = text(f"""
                    SELECT DISTINCT [ParentProjectID] 
                    FROM [dbo].[{table_name}] 
                    WHERE {where_clause} AND [ParentProjectID] IS NOT NULL AND [ParentProjectID] != ''
                    ORDER BY [ParentProjectID]
                """)
                
                result = pd.read_sql(query, engine, params=params)
                if not result.empty:
                    return result['ParentProjectID'].tolist()
            
            # Fallback: Get ALL available ParentProjectIDs
            query = text(f"""
                SELECT DISTINCT [ParentProjectID] 
                FROM [dbo].[{table_name}] 
                WHERE [ParentProjectID] IS NOT NULL AND [ParentProjectID] != ''
                ORDER BY [ParentProjectID]
            """)
            result = pd.read_sql(query, engine)
            return result['ParentProjectID'].tolist()
            
        except Exception as e:
            st.error(f"Error fetching projects: {str(e)}")
            logging.error(f"Error in _fetch_customer_projects: {str(e)}")
            return []

    def _fetch_all_manufacturers(self) -> list:
        """Fetch all manufacturers from vw_Manufacturers table"""
        try:
            engine = get_engine_testdb()
            query = text("SELECT DISTINCT [Manufacturer] FROM [dbo].[vw_Manufacturers] WHERE [Manufacturer] IS NOT NULL AND [Manufacturer] != '' ORDER BY [Manufacturer]")
            result = pd.read_sql(query, engine)
            return result['Manufacturer'].tolist()
        except Exception as e:
            # Fallback to equipment table if vw_Manufacturers doesn't exist
            try:
                table_name = 'EquipmentDB'  # Fixed table name
                query = text(f"SELECT DISTINCT [Manufacturer] FROM [dbo].[{table_name}] WHERE [Manufacturer] IS NOT NULL AND [Manufacturer] != '' ORDER BY [Manufacturer]")
                result = pd.read_sql(query, engine)
                return result['Manufacturer'].tolist()
            except Exception as e2:
                st.error(f"Error fetching manufacturers: {str(e2)}")
                logging.error(f"Error in _fetch_all_manufacturers: {str(e2)}")
                return []

    def _insert_new_manufacturer(self, manufacturer_name: str) -> bool:
        """Insert new manufacturer into vw_Manufacturers table"""
        try:
            engine = get_engine_testdb()
            query = text("INSERT INTO [dbo].[vw_Manufacturers] ([Manufacturer]) VALUES (:manufacturer)")
            with engine.begin() as conn:
                conn.execute(query, {'manufacturer': manufacturer_name})
            return True
        except Exception as e:
            st.error(f"Failed to add manufacturer: {str(e)}")
            return False

    def _insert_new_customer(self, customer_name: str, customer_id: str = None, location: str = None) -> bool:
        """Insert new customer into ContractsCustomersAddresses table"""
        try:
            engine = get_engine_testdb()
            query = text("""
                INSERT INTO [dbo].[ContractsCustomersAddresses] 
                ([CustomerName], [CustomerIDAcu], [City]) 
                VALUES (:customer_name, :customer_id, :location)
            """)
            with engine.begin() as conn:
                conn.execute(query, {
                    'customer_name': customer_name,
                    'customer_id': customer_id or customer_name,
                    'location': location or ''
                })
            return True
        except Exception as e:
            st.error(f"Failed to add customer: {str(e)}")
            return False

    def _fetch_customer_manufacturers(self, customer_id: str = None, customer_name: str = None) -> list:
        """Fetch manufacturers for specific customer, with fallback to all manufacturers"""
        try:
            engine = get_engine_testdb()
            table_name = 'EquipmentDB'  # Fixed table name
            
            # First try customer-filtered results
            if customer_id or customer_name:
                conditions = []
                params = {}
                
                if customer_id:
                    conditions.append("[CustomerID] = :customer_id")
                    params['customer_id'] = customer_id
                if customer_name:
                    conditions.append("[CustomerName] = :customer_name")
                    params['customer_name'] = customer_name
                    
                where_clause = " AND ".join(conditions)
                query = text(f"""
                    SELECT DISTINCT [Manufacturer] 
                    FROM [dbo].[{table_name}] 
                    WHERE {where_clause} AND [Manufacturer] IS NOT NULL AND [Manufacturer] != ''
                    ORDER BY [Manufacturer]
                """)
                
                result = pd.read_sql(query, engine, params=params)
                if not result.empty:
                    return result['Manufacturer'].tolist()
            
            # Fallback: Get ALL available manufacturers
            return self._fetch_all_manufacturers()
            
        except Exception as e:
            st.error(f"Error fetching customer manufacturers: {str(e)}")
            logging.error(f"Error in _fetch_customer_manufacturers: {str(e)}")
            return []

    def _fetch_customer_mfg_projects(self, customer_id: str = None, customer_name: str = None) -> list:
        """Fetch manufacturer project IDs for specific customer, with fallback to all"""
        try:
            engine = get_engine_testdb()
            table_name = 'EquipmentDB'  # Fixed table name
            
            # First try customer-filtered results
            if customer_id or customer_name:
                conditions = []
                params = {}
                
                if customer_id:
                    conditions.append("[CustomerID] = :customer_id")
                    params['customer_id'] = customer_id
                if customer_name:
                    conditions.append("[CustomerName] = :customer_name")
                    params['customer_name'] = customer_name
                    
                where_clause = " AND ".join(conditions)
                query = text(f"""
                    SELECT DISTINCT [ManufacturerProjectID] 
                    FROM [dbo].[{table_name}] 
                    WHERE {where_clause} AND [ManufacturerProjectID] IS NOT NULL AND [ManufacturerProjectID] != ''
                    ORDER BY [ManufacturerProjectID]
                """)
                
                result = pd.read_sql(query, engine, params=params)
                if not result.empty:
                    return result['ManufacturerProjectID'].tolist()
            
            # Fallback: Get ALL available ManufacturerProjectIDs
            query = text(f"""
                SELECT DISTINCT [ManufacturerProjectID] 
                FROM [dbo].[{table_name}] 
                WHERE [ManufacturerProjectID] IS NOT NULL AND [ManufacturerProjectID] != ''
                ORDER BY [ManufacturerProjectID]
            """)
            result = pd.read_sql(query, engine)
            return result['ManufacturerProjectID'].tolist()
            
        except Exception as e:
            st.error(f"Error fetching manufacturer projects: {str(e)}")
            logging.error(f"Error in _fetch_customer_mfg_projects: {str(e)}")
            return []

    def _fetch_customer_active_status(self, customer_id: str = None, customer_name: str = None) -> list:
        """Fetch active status values for specific customer, with fallback to all"""
        try:
            engine = get_engine_testdb()
            table_name = 'EquipmentDB'  # Fixed table name
            
            # First try customer-filtered results
            if customer_id or customer_name:
                conditions = []
                params = {}
                
                if customer_id:
                    conditions.append("[CustomerID] = :customer_id")
                    params['customer_id'] = customer_id
                if customer_name:
                    conditions.append("[CustomerName] = :customer_name")
                    params['customer_name'] = customer_name
                    
                where_clause = " AND ".join(conditions)
                query = text(f"""
                    SELECT DISTINCT [ActiveStatus] 
                    FROM [dbo].[{table_name}] 
                    WHERE {where_clause} AND [ActiveStatus] IS NOT NULL AND [ActiveStatus] != ''
                    ORDER BY [ActiveStatus]
                """)
                
                result = pd.read_sql(query, engine, params=params)
                if not result.empty:
                    return result['ActiveStatus'].tolist()
            
            # Fallback: Get ALL available ActiveStatus values
            query = text(f"""
                SELECT DISTINCT [ActiveStatus] 
                FROM [dbo].[{table_name}] 
                WHERE [ActiveStatus] IS NOT NULL AND [ActiveStatus] != ''
                ORDER BY [ActiveStatus]
            """)
            result = pd.read_sql(query, engine)
            return result['ActiveStatus'].tolist()
            
        except Exception as e:
            st.error(f"Error fetching active status: {str(e)}")
            logging.error(f"Error in _fetch_customer_active_status: {str(e)}")
            return []

    def _fetch_customers(self) -> pd.DataFrame:
        """Fetch customer data from ContractsCustomersAddresses table"""
        try:
            engine = get_engine_testdb()
            query = text("""
                SELECT DISTINCT [CustomerIDAcu], [CustomerName], [City], [State]
                FROM [dbo].[ContractsCustomersAddresses]
                WHERE [CustomerName] IS NOT NULL AND [CustomerName] != ''
                ORDER BY [CustomerName]
            """)
            return pd.read_sql(query, engine)
        except Exception as e:
            st.error(f"Failed to load customers: {str(e)}")
            return pd.DataFrame()

    def _render_fixed_fields_section(self):
        st.markdown("### 📋 Step 1: Common Information")
        
        # Customer Selection Section
        st.markdown("**Customer:**")
        customers_df = self._fetch_customers()
        selected_customer = None  # Initialize variable
        
        col1, col2 = st.columns([2, 1])
        with col1:
            if not customers_df.empty:
                customer_options = [''] + customers_df['CustomerName'].tolist() + ['-- Add New Customer --']
                selected_customer = st.selectbox(
                    "Select Customer", 
                    customer_options, 
                    key='customer_dropdown'
                )
                
                if selected_customer and selected_customer not in ['', '-- Add New Customer --']:
                    # Auto-fill from selected customer
                    customer_row = customers_df[customers_df['CustomerName'] == selected_customer].iloc[0]
                    st.session_state['CustomerID'] = customer_row['CustomerIDAcu']
                    st.session_state['CustomerName'] = customer_row['CustomerName']
                    location_parts = [str(customer_row.get('City', '')), str(customer_row.get('State', ''))]
                    st.session_state['CustomerLocation'] = ', '.join([p for p in location_parts if p and p != 'nan'])
                
                elif selected_customer == '-- Add New Customer --':
                    with st.expander("➕ Add New Customer", expanded=True):
                        new_cust_name = st.text_input("New Customer Name:", key='new_customer_name')
                        new_cust_id = st.text_input("New Customer ID (optional):", key='new_customer_id')
                        new_cust_location = st.text_input("Customer Location (optional):", key='new_customer_location')
                        
                        if st.button("💾 Add Customer", key='add_new_customer'):
                            if new_cust_name.strip():
                                if self._insert_new_customer(new_cust_name, new_cust_id, new_cust_location):
                                    st.session_state['CustomerName'] = new_cust_name
                                    st.session_state['CustomerID'] = new_cust_id or new_cust_name
                                    st.session_state['CustomerLocation'] = new_cust_location
                            else:
                                st.error("Customer name is required")
            else:
                st.warning("Could not load customer list - enter manually below")
        
        with col2:
            if st.button("🔄 Refresh Customers", key="refresh_customers"):
                st.rerun()
        
        # Manual Entry Section
        col1, col2, col3 = st.columns(3)
        with col1:
            customer_id = st.text_input(
                "Customer ID", 
                value=st.session_state.get('CustomerID', ''), 
                key='eq_customer_id',
                help="Optional for new customers"
            )
            if selected_customer == '-- Add New Customer --':
                st.caption("⚠️ New customer - ID optional, will be assigned later")
            else:
                st.caption("Auto-filled from selection or enter manually")
            st.session_state['CustomerID'] = customer_id
            
        with col2:
            customer_name = st.text_input(
                "Customer Name", 
                value=st.session_state.get('CustomerName', ''), 
                key='eq_customer_name'
            )
            if customer_name != st.session_state.get('CustomerName', '') and customer_name.strip():
                # Check if manually entered name exists in database
                if not customers_df.empty:
                    matching_customers = customers_df[customers_df['CustomerName'].str.contains(customer_name, case=False, na=False)]
                    if not matching_customers.empty and len(matching_customers) == 1:
                        match = matching_customers.iloc[0]
                        st.session_state['CustomerID'] = match['CustomerIDAcu']
                        location_parts = [str(match.get('City', '')), str(match.get('State', ''))]
                        st.session_state['CustomerLocation'] = ', '.join([p for p in location_parts if p and p != 'nan'])
                        st.success(f"✅ Found match: ID={match['CustomerIDAcu']}")
                    elif len(matching_customers) > 1:
                        st.info(f"🔍 Found {len(matching_customers)} similar customers - use dropdown to select")
                    else:
                        st.info("🆕 New customer detected - please add Customer ID if known")
            st.session_state['CustomerName'] = customer_name
            
        with col3:
            st.session_state['CustomerLocation'] = st.text_input(
                "Customer Location", 
                value=st.session_state.get('CustomerLocation', ''), 
                key='eq_customer_location'
            )
            st.caption("Auto-filled from selection or enter manually")
            
        st.markdown("**Project Information:**")
        
        # Get current customer info for filtering
        current_customer_id = st.session_state.get('CustomerID', '')
        current_customer_name = st.session_state.get('CustomerName', '')
        
        # Show project information with improved data fetching
        col1, col2 = st.columns(2)
        with col1:
            # Project ID dropdown - now with fallback to all projects
            project_options = self._fetch_customer_projects(current_customer_id, current_customer_name)
            if project_options:
                project_options = [''] + project_options + ['-- Enter New --']
                selected_project = st.selectbox("Project ID", project_options, key='project_dropdown')
                
                if selected_project and selected_project != '-- Enter New --':
                    st.session_state['ParentProjectID'] = selected_project
                elif selected_project == '-- Enter New --':
                    manual_project = st.text_input("Enter new Project ID:", key='manual_project_input')
                    st.session_state['ParentProjectID'] = manual_project
            else:
                st.session_state['ParentProjectID'] = st.text_input("Project ID", key='new_project_input')
            
        with col2:
            # Manufacturer dropdown - improved fallback
            all_manufacturers = self._fetch_all_manufacturers()
            if all_manufacturers:
                mfg_options = [''] + all_manufacturers + ['-- Add New Manufacturer --']
                selected_mfg = st.selectbox("Manufacturer", mfg_options, key='mfg_dropdown')
                
                if selected_mfg and selected_mfg != '-- Add New Manufacturer --':
                    st.session_state['Manufacturer'] = selected_mfg
                elif selected_mfg == '-- Add New Manufacturer --':
                    with st.expander("➕ Add New Manufacturer", expanded=True):
                        new_mfg_name = st.text_input("New Manufacturer Name:", key='new_mfg_name')
                        if st.button("💾 Add Manufacturer", key='add_new_mfg'):
                            if new_mfg_name.strip():
                                if self._insert_new_manufacturer(new_mfg_name):
                                    st.session_state['Manufacturer'] = new_mfg_name
                            else:
                                st.error("Manufacturer name is required")
            else:
                st.session_state['Manufacturer'] = st.text_input("Manufacturer", key='new_mfg_input')
        
        col1, col2 = st.columns(2)
        with col1:
            # Manufacturer Project ID dropdown - now with fallback
            mfg_proj_options = self._fetch_customer_mfg_projects(current_customer_id, current_customer_name)
            if mfg_proj_options:
                mfg_proj_options = [''] + mfg_proj_options + ['-- Enter New --']
                selected_mfg_proj = st.selectbox("Manufacturer Project ID", mfg_proj_options, key='mfg_proj_dropdown')
                
                if selected_mfg_proj and selected_mfg_proj != '-- Enter New --':
                    st.session_state['ManufacturerProjectID'] = selected_mfg_proj
                elif selected_mfg_proj == '-- Enter New --':
                    manual_mfg_proj = st.text_input("Enter new Mfg Project ID:", key='manual_mfg_proj_input')
                    st.session_state['ManufacturerProjectID'] = manual_mfg_proj
            else:
                st.session_state['ManufacturerProjectID'] = st.text_input("Manufacturer Project ID", key='new_mfg_proj_input')
                
        with col2:
            # Active Status dropdown - now with fallback
            status_options = self._fetch_customer_active_status(current_customer_id, current_customer_name)
            if status_options:
                status_options = [''] + status_options + ['-- Enter New --']
                selected_status = st.selectbox("Active Status", status_options, key='status_dropdown')
                
                if selected_status and selected_status != '-- Enter New --':
                    st.session_state['ActiveStatus'] = selected_status
                elif selected_status == '-- Enter New --':
                    manual_status = st.text_input("Enter new Active Status:", key='manual_status_input')
                    st.session_state['ActiveStatus'] = manual_status
            else:
                st.session_state['ActiveStatus'] = st.text_input("Active Status", key='new_status_input')
                
        # Show filtering info if customer is selected
        if current_customer_id or current_customer_name:
            st.caption(f"🔍 **Data shown:** Customer-specific first, then all available options")
        else:
            st.caption("💡 **Data shown:** All available options from database")
            
        st.markdown("---")
        if st.button("✅ Save Common Information", type="primary", key="save_fixed_fields"):
            filled_fields = sum(1 for field in self.config.FIXED_FIELDS if st.session_state.get(field, '').strip())
            if filled_fields > 0:
                st.session_state['fixed_fields_set'] = True
                st.success("✅ Common information saved! Proceed to Step 2.")
                st.balloons()
                st.rerun()
            else:
                st.warning("⚠️ Please fill in at least one field before proceeding")

    def _render_equipment_type_selection(self):
        st.markdown("### 🏷️ Step 2: Select Equipment Type")
        st.info("This determines what specification fields are available for your equipment")
        with st.spinner("Loading available equipment types..."):
            equipment_types = fetch_frequent_values('vw_EquipmentTypes', 'EquipmentType') or []
        if equipment_types:
            selected_type = st.selectbox("Equipment Type", equipment_types, key='eq_type_select')
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
        st.markdown("### 📊 Equipment Data Management")
        st.info("🔮 **Auto-filled fields:** EquipmentType + all information from Step 1")
        
        col1, col2 = st.columns([8, 1])
        with col1:
            st.info("💡 **Save Behavior:** Only modified and new rows will be saved to prevent duplicates")
        with col2:
            if st.button("🔄", key="refresh_data", help="Refresh data from database"):
                st.session_state.original_data_hash = {}  # Reset hash tracking
                st.rerun()
                
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
        
        with st.expander("⚙️ Advanced Settings", expanded=False):
            st.markdown("**Database Table Configuration:**")
            current_table = self._get_equipment_table_name()
            st.info(f"Current table: **{current_table}**")
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
        
        if st.session_state.get('manual_search_triggered'):
            existing_df = self._manual_search_equipment()
            st.session_state['manual_search_triggered'] = False
        else:
            existing_df = self._load_existing_equipment_data()
        self._render_data_grid(existing_df)

    def _generate_row_id(self, row_data: dict) -> str:
        """Generate unique row ID for tracking, handles records without SerialNumber"""
        # Primary key options in order of preference
        if row_data.get('SerialNumber'):
            return f"SN_{row_data['SerialNumber']}"
        elif row_data.get('RowCounter'):
            return f"RC_{row_data['RowCounter']}"
        elif row_data.get('MachineInfoID'):
            return f"MI_{row_data['MachineInfoID']}"
        else:
            # Composite key for records without unique identifiers
            composite_parts = []
            for field in ['CustomerID', 'CustomerPositionNo', 'EquipmentType', 'Model']:
                val = str(row_data.get(field, '')).strip()
                if val:
                    composite_parts.append(val)
            
            if composite_parts:
                composite_key = "_".join(composite_parts)
                # Add hash to handle long composite keys
                return f"CK_{hashlib.md5(composite_key.encode()).hexdigest()[:8]}"
            else:
                # Last resort - use row hash
                row_str = "_".join(str(v) for v in row_data.values() if str(v).strip())
                return f"RH_{hashlib.md5(row_str.encode()).hexdigest()[:8]}"

    def _get_row_hash(self, row_data: dict) -> str:
        """Generate hash of row data for change detection"""
        # Only hash the actual data columns, not status/ID columns
        data_to_hash = {}
        for col in SQL_COLUMN_ORDER:
            val = str(row_data.get(col, '')).strip()
            data_to_hash[col] = val
        
        row_str = str(sorted(data_to_hash.items()))
        return hashlib.md5(row_str.encode()).hexdigest()

    def _manual_search_equipment(self) -> pd.DataFrame:
        try:
            engine = get_engine_testdb()
            table_name = 'EquipmentDB'  # Fixed table name
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
            sql_cols = ', '.join(f'[{col}]' for col in SQL_COLUMN_ORDER)
            query = text(f"SELECT {sql_cols} FROM [dbo].[{table_name}] WHERE {where_clause} ORDER BY SerialNumber")
            with st.spinner("Searching..."):
                result_df = pd.read_sql(query, engine, params=params)
            if not result_df.empty:
                st.success(f"✅ Manual search found {len(result_df)} records")
            else:
                st.warning("No records found with manual search criteria")
            return result_df
        except Exception as e:
            st.error(f"Manual search failed: {str(e)}")
            logging.error(f"Manual search error: {str(e)}")
            return pd.DataFrame()

    def _get_equipment_table_name(self) -> str:
        if st.session_state.get('equipment_table_name_override'):
            return st.session_state['equipment_table_name_override']
        return 'EquipmentDB'  # Fixed default table name

    def _load_existing_equipment_data(self) -> pd.DataFrame:
        try:
            engine = get_engine_testdb()
            table_name = 'EquipmentDB'  # Fixed table name
            selected_type = st.session_state.get('selected_equipment_type')
            
            # Get available Specifications columns from database
            base_columns = [
                'CustomerID', 'CustomerName', 'CustomerLocation', 'ActiveStatus', 'SortSystemPosition',
                'SerialNumber', 'OtherOrPreviousPosition', 'CustomerPositionNo', 'YearManufactured', 'SalesDateWarrantyStartDate',
                'InstallDate', 'Manufacturer', 'ManufacturerProjectID', 'ParentProjectID', 'EquipmentType',
                'FunctionalType', 'FunctionalPosition', 'ManufacturerModelDescription', 'Model'
            ]
            
            # Add existing Specifications columns
            available_cols = base_columns.copy()
            for i in range(1, 21):
                spec_col = f'Specifications{i}'
                if self._check_column_exists(engine, table_name, spec_col):
                    available_cols.append(spec_col)
            
            # Add end columns
            end_columns = ['Notes', 'EquipmentKey', 'RecordHistory', 'RowCounter', 'MachineInfoID', 'UploadsPendingID', 'HashedSerialNumber']
            for col in end_columns:
                if self._check_column_exists(engine, table_name, col):
                    available_cols.append(col)
            
            sql_cols = ', '.join(f'[{col}]' for col in available_cols)
            
            # Query database with actual column names
            if selected_type:
                query = text(f"SELECT {sql_cols} FROM [dbo].[{table_name}] WHERE [EquipmentType] = :equipment_type ORDER BY SerialNumber")
                existing_df = pd.read_sql(query, engine, params={'equipment_type': selected_type})
            else:
                query = text(f"SELECT {sql_cols} FROM [dbo].[{table_name}] ORDER BY SerialNumber")
                existing_df = pd.read_sql(query, engine)
            
            if not existing_df.empty:
                st.success(f"✅ Loaded {len(existing_df)} {selected_type or 'equipment'} records")
                
                # Store original data hashes for change detection
                for idx, row in existing_df.iterrows():
                    row_id = self._generate_row_id(row.to_dict())
                    row_hash = self._get_row_hash(row.to_dict())
                    st.session_state.original_data_hash[row_id] = row_hash
            else:
                st.info(f"🔍 No {selected_type or 'equipment'} records found")
            
            return existing_df
        except Exception as e:
            st.error(f"Failed to load existing data: {str(e)}")
            logging.error(f"Load existing data error: {str(e)}")
            return pd.DataFrame()

    def _render_data_grid(self, existing_df: pd.DataFrame):
        st.markdown("### 📊 Equipment Data Grid")
        with st.expander("📋 How to paste data from Excel", expanded=False):
            st.markdown("""
            **To paste data from Excel:**
            1. Copy your data from Excel (including headers if needed)
            2. Click on the first cell where you want to paste
            3. Press **Ctrl+V** (or Cmd+V on Mac) to paste
            """)
        grid_df = self._build_complete_grid(existing_df)
        if grid_df.empty:
            st.warning("⚠️ No data to display")
            return
        column_config = self._build_column_config()
        edited_df = st.data_editor(
            grid_df,
            column_config=column_config,
            num_rows="dynamic",
            use_container_width=True,
            height=600,
            key="equipment_data_editor"
        )
        
        col1, col2 = st.columns([3, 1])
        with col1:
            changed_rows = self._detect_changes(edited_df)
            if changed_rows:
                st.info(f"🔍 **Changes detected:** {changed_rows['modified']} modified, {changed_rows['new']} new rows")
            else:
                st.info("📝 **No changes detected** - only modified/new rows will be saved")
        with col2:
            if st.button("💾 Save Changes", type="primary", key="save_equipment_data"):
                self._save_changes_only(edited_df)

    def _build_complete_grid(self, existing_df: pd.DataFrame) -> pd.DataFrame:
        selected_type = st.session_state.get('selected_equipment_type')
        display_columns, spec_mapping = self._get_dynamic_columns(selected_type)
        
        all_rows = []
        
        # Add existing records with mapped data
        for idx, row in existing_df.iterrows():
            row_id = self._generate_row_id(row.to_dict())
            grid_row = {
                'Status': f'📝 {selected_type} #{idx+1}' if selected_type else f'📝 #{idx+1}',
                'RowID': row_id
            }
            
            # Map database columns to display columns
            for display_col in display_columns:
                if display_col in spec_mapping:
                    # This is a specification label, map to database column
                    db_col = spec_mapping[display_col]
                    grid_row[display_col] = row.get(db_col, '') if db_col in row else ''
                else:
                    # Standard column
                    grid_row[display_col] = row.get(display_col, '') if display_col in row else ''
            
            all_rows.append(grid_row)
        
        # Add empty rows for new entries
        new_row_count = 10 if existing_df.empty else 5
        for i in range(new_row_count):
            grid_row = {
                'Status': f'➕ New {selected_type} #{i+1}' if selected_type else f'➕ New #{i+1}',
                'RowID': f'NEW_{i+1}'
            }
            for col in display_columns:
                if col in self.config.FIXED_FIELDS:
                    grid_row[col] = st.session_state.get(col, '')
                elif col == 'EquipmentType':
                    grid_row[col] = selected_type or ''
                else:
                    grid_row[col] = ''
            all_rows.append(grid_row)
        
        df = pd.DataFrame(all_rows)
        full_column_order = ['Status', 'RowID'] + display_columns
        ordered_cols = [col for col in full_column_order if col in df.columns]
        return df[ordered_cols]

    def _build_column_config(self) -> dict:
        selected_type = st.session_state.get('selected_equipment_type')
        display_columns, spec_mapping = self._get_dynamic_columns(selected_type)
        
        column_config = {}
        column_config['Status'] = st.column_config.TextColumn('Status', disabled=True, width=120)
        column_config['RowID'] = st.column_config.TextColumn('Row ID', disabled=True, width=100)
        
        for col in display_columns:
            if col in spec_mapping:
                # This is a specification label
                column_config[col] = st.column_config.TextColumn(col, help=f"{selected_type} specification")
            else:
                column_config[col] = st.column_config.TextColumn(col)
        
        return column_config

    def _detect_changes(self, edited_df: pd.DataFrame) -> dict:
        """Detect which rows have been modified or are new"""
        changes = {'modified': 0, 'new': 0, 'modified_rows': [], 'new_rows': []}
        
        for idx, row in edited_df.iterrows():
            row_dict = row.to_dict()
            row_id = row_dict.get('RowID', '')
            
            # Skip completely empty rows
            if not any(str(row_dict.get(col, '')).strip() for col in SQL_COLUMN_ORDER):
                continue
            
            if row_id.startswith('NEW_'):
                changes['new'] += 1
                changes['new_rows'].append(idx)
            else:
                # Check if existing row was modified
                current_hash = self._get_row_hash(row_dict)
                original_hash = st.session_state.original_data_hash.get(row_id, '')
                
                if current_hash != original_hash:
                    changes['modified'] += 1
                    changes['modified_rows'].append(idx)
        
        return changes

    def _get_database_key_fields(self, record: dict) -> tuple:
        """Get the key fields used to identify record in database"""
        if record.get('SerialNumber'):
            return ('SerialNumber', record['SerialNumber'])
        elif record.get('RowCounter'):
            return ('RowCounter', record['RowCounter'])
        elif record.get('MachineInfoID'):
            return ('MachineInfoID', record['MachineInfoID'])
        else:
            # Use composite key
            key_parts = []
            key_values = {}
            for field in ['CustomerID', 'CustomerPositionNo', 'EquipmentType']:
                if record.get(field):
                    key_parts.append(f"[{field}] = :{field}")
                    key_values[field] = record[field]
            
            if key_parts:
                where_clause = " AND ".join(key_parts)
                return ('COMPOSITE', (where_clause, key_values))
            else:
                return ('NONE', None)

    def _check_column_exists(self, engine, table_name: str, column_name: str) -> bool:
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
        try:
            query = text(f"SELECT ISNULL(MAX([RowCounter]), 0) + 1 as next_counter FROM [dbo].[{table_name}]")
            result = pd.read_sql(query, engine)
            return int(result['next_counter'].iloc[0])
        except Exception:
            return 1

    def _save_changes_only(self, edited_df: pd.DataFrame):
        """Save only modified and new rows to prevent duplicates"""
        try:
            table_name = 'EquipmentDB'  # Fixed table name
            engine = get_engine_testdb()
            selected_type = st.session_state.get('selected_equipment_type')
            display_columns, spec_mapping = self._get_dynamic_columns(selected_type)
            
            success_count = 0
            errors = []
            
            # Detect changes
            changes = self._detect_changes(edited_df)
            
            if not changes['modified_rows'] and not changes['new_rows']:
                st.info("🔍 No changes detected - nothing to save")
                return

            has_row_counter = self._check_column_exists(engine, table_name, 'RowCounter')

            st.info(f"💾 **Saving {selected_type} changes:** {changes['modified']} modified + {changes['new']} new rows")
            
            # Get specification labels for mapping
            spec_labels = []
            if selected_type:
                spec_mapping_dict = self._fetch_specification_labels(selected_type)
                spec_labels = list(spec_mapping_dict.keys())
            
            # Process only changed rows
            rows_to_process = changes['modified_rows'] + changes['new_rows']
            
            for idx in rows_to_process:
                try:
                    row = edited_df.iloc[idx]
                    row_dict = row.to_dict()
                    
                    # Skip empty rows
                    if not any(str(row_dict.get(col, '')).strip() for col in display_columns):
                        continue

                    record = {}
                    
                    # Process standard columns
                    for col in display_columns:
                        if col in self.config.FIXED_FIELDS:
                            record[col] = st.session_state.get(col, '')
                        elif col in SQL_COLUMN_ORDER:
                            # Standard SQL column
                            val = row_dict.get(col, '')
                            record[col] = str(val) if pd.notna(val) and str(val).strip() != '' else None
                        elif col in spec_labels:
                            # This is a specification label - map to Specifications1-50
                            spec_index = spec_labels.index(col) + 1
                            spec_col = f'Specifications{spec_index}'
                            val = row_dict.get(col, '')
                            record[spec_col] = str(val) if pd.notna(val) and str(val).strip() != '' else None

                    # Add/update RecordHistory
                    existing_history = row_dict.get('RecordHistory', '') or ''
                    user_identity = get_user_identity()
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    if idx in changes['new_rows']:
                        edit_info = f"[{timestamp}] Created by: {user_identity}"
                    else:
                        edit_info = f"[{timestamp}] Modified by: {user_identity}"
                    
                    if existing_history:
                        record['RecordHistory'] = f"{existing_history}\n{edit_info}"
                    else:
                        record['RecordHistory'] = edit_info

                    # Determine if UPDATE or INSERT
                    key_type, key_info = self._get_database_key_fields(record)
                    
                    if key_type == 'NONE' or idx in changes['new_rows']:
                        # INSERT new record
                        if has_row_counter:
                            record['RowCounter'] = self._get_next_row_counter(engine, table_name)
                        
                        # Only include columns that exist in database
                        db_record = {}
                        for col, val in record.items():
                            if self._check_column_exists(engine, table_name, col):
                                db_record[col] = val
                        
                        columns = ", ".join([f"[{col}]" for col in db_record.keys()])
                        placeholders = ", ".join([f":{col}" for col in db_record.keys()])
                        insert_query = text(f"INSERT INTO [dbo].[{table_name}] ({columns}) VALUES ({placeholders})")
                        
                        with engine.begin() as conn:
                            conn.execute(insert_query, db_record)
                    else:
                        # UPDATE existing record
                        set_clauses = []
                        update_params = {}
                        
                        for key, value in record.items():
                            if key not in ['SerialNumber', 'RowCounter', 'MachineInfoID'] and self._check_column_exists(engine, table_name, key):
                                set_clauses.append(f"[{key}] = :{key}")
                                update_params[key] = value
                        
                        if key_type == 'COMPOSITE':
                            where_clause, key_values = key_info
                            update_params.update(key_values)
                        else:
                            where_clause = f"[{key_type}] = :{key_type}"
                            update_params[key_type] = key_info
                        
                        update_query = text(f"UPDATE [dbo].[{table_name}] SET {', '.join(set_clauses)} WHERE {where_clause}")
                        
                        with engine.begin() as conn:
                            result = conn.execute(update_query, update_params)
                            if result.rowcount == 0:
                                # Record not found, insert instead
                                if has_row_counter:
                                    record['RowCounter'] = self._get_next_row_counter(engine, table_name)
                                
                                db_record = {}
                                for col, val in record.items():
                                    if self._check_column_exists(engine, table_name, col):
                                        db_record[col] = val
                                
                                columns = ", ".join([f"[{col}]" for col in db_record.keys()])
                                placeholders = ", ".join([f":{col}" for col in db_record.keys()])
                                insert_query = text(f"INSERT INTO [dbo].[{table_name}] ({columns}) VALUES ({placeholders})")
                                conn.execute(insert_query, db_record)
                    
                    success_count += 1
                    
                    # Update hash tracking for existing records
                    if idx in changes['modified_rows']:
                        row_id = row_dict.get('RowID', '')
                        new_hash = self._get_row_hash(record)
                        st.session_state.original_data_hash[row_id] = new_hash

                except Exception as e:
                    errors.append(f"Row {idx+1}: {str(e)}")
                    logging.error(f"Save row {idx} failed: {str(e)}")

            # Show results
            if success_count > 0:
                st.success(f"🎉 Successfully saved {success_count} {selected_type} records!")
                logging.info(f"Equipment Manager: User saved {success_count} {selected_type} records")
            if errors:
                st.error(f"❌ {len(errors)} errors:")
                for error in errors[:3]:
                    st.write(f"• {error}")
                if len(errors) > 3:
                    st.write(f"... and {len(errors)-3} more errors")

        except Exception as e:
            st.error(f"❌ Save operation failed: {str(e)}")
            logging.error(f"Equipment save failed: {str(e)}")

# Execute the application
manager = EquipmentManager()
manager.render()
