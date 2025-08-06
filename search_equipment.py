"""
Search Equipment Module - Dynamic Specification Mapping
======================================================

Optimized equipment search with:
- High-performance caching and loading
- Dynamic specification labeling (1-55) from vw_EquipmentType_SpecificationLabels
- Enhanced data analysis with visualizations
- User-friendly interface for light and dark modes
- Comprehensive logging
- NO export functionality

Version: 6.3 - Dynamic Database-Driven Specification Mapping
"""

import streamlit as st
import pandas as pd
import logging
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import text

# Import shared utilities
from shared_config import (
    Config, get_user_identity, find_equipment_table_name, 
    format_date_columns
)
from db_utils import get_engine_testdb

# Configure enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/search_equipment.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_equipment_metrics_html(records, customers, manufacturers, models):
    """Create responsive, mode-friendly metrics row using HTML/CSS"""
    return f"""
    <div class="equipment-metrics">
        <div class="equipment-metric-item">
            <span class="equipment-metric-value">{records}</span>
            <span class="equipment-metric-label">Records</span>
        </div>
        <div class="equipment-metric-item">
            <span class="equipment-metric-value">{customers}</span>
            <span class="equipment-metric-label">Customers</span>
        </div>
        <div class="equipment-metric-item">
            <span class="equipment-metric-value">{manufacturers}</span>
            <span class="equipment-metric-label">Manufacturers</span>
        </div>
        <div class="equipment-metric-item">
            <span class="equipment-metric-value">{models}</span>
            <span class="equipment-metric-label">Models</span>
        </div>
    </div>
    """

def create_equipment_header_html(equipment_type):
    """Create responsive equipment type header with mode-friendly colors"""
    return f"""
    <div class="equipment-header">
        <h3>🔧 {equipment_type} Equipment</h3>
    </div>
    """

class SearchEquipment:
    """High-performance equipment search with dynamic database-driven specification mapping"""
    
    def __init__(self):
        """Initialize search equipment with optimized settings"""
        self.config = Config()
        self.table_name = 'EquipmentDB'
        logger.info("SearchEquipment module initialized with dynamic specification mapping")
    
    def render(self):
        """Main render method - optimized and user-friendly"""
        
        # Log user access
        user = st.session_state.get("username", "Unknown")
        logger.info(f"SearchEquipment accessed by user: {user}")
        
        st.title("🔍 Equipment Search & Analysis")
        st.markdown("**Professional equipment search with editable results, dynamic filtering and database-driven specification mapping**")
        
        # ========== EDITABLE INTERFACE INFO ==========
        with st.expander("📝 Editable Interface Guide"):
            st.markdown("""
            **🔧 Editing Features:**
            - ✅ **Edit any cell** by clicking and typing
            - ✅ **Add new rows** using the "+" button
            - ✅ **Delete rows** by selecting and using delete
            - ✅ **Save changes** back to database with the Save button
            - ✅ **Only labeled specifications** are shown (unlabeled ones are automatically removed)
            - ✅ **Dynamic labels** from database (e.g., "Weight (kg)" instead of "Specifications1")
            
            **🎯 Specification Filtering:**
            - 📋 Only specifications with database labels are displayed
            - 🧹 Unlabeled "SpecificationsX" columns are automatically hidden
            - 🔗 Labels come from `vw_EquipmentType_SpecificationLabels` table
            """)
        
        # ========== PERFORMANCE CONTROLS ==========
        col1, col2 = st.columns([4, 1])
        with col1:
            # Cache status indicator (logged, not displayed)
            cache_status = "Active" if hasattr(st, 'cache_data') else "Disabled"
            logger.info(f"Cache status: {cache_status}")
        with col2:
            if st.button("🔄 Clear Cache", help="Clear all cached data", use_container_width=True):
                try:
                    st.cache_data.clear()
                    logger.info("Cache cleared by user")
                    st.success("Cache cleared!")
                    st.rerun()
                except Exception as e:
                    logger.error(f"Cache clear failed: {str(e)}")
        
        # ========== MAIN SEARCH INTERFACE ==========
        search_tab1, search_tab2, search_tab3 = st.tabs([
            "🎯 Advanced Search", 
            "🔎 Quick Search",
            "📊 Data Analysis"
        ])
        
        with search_tab1:
            self._render_advanced_search()
        
        with search_tab2:
            self._render_quick_search()
        
        with search_tab3:
            self._render_data_analysis()
    
    # ========== DYNAMIC SPECIFICATION MAPPING METHODS ==========
    @st.cache_data(ttl=1800, show_spinner="Loading specification labels...")
    def _get_specification_labels_from_db(_self, equipment_type: str) -> dict:
        """Get specification labels dynamically from vw_EquipmentType_SpecificationLabels table"""
        try:
            logger.info(f"Fetching dynamic specification labels for equipment type: {equipment_type}")
            
            from db_utils import get_engine_powerapps
            engine = get_engine_powerapps()
            
            # Query the view with the exact structure from your example
            query = text("""
                SELECT * FROM [dbo].[vw_EquipmentType_SpecificationLabels]
                WHERE [EquipmentType] = :equipment_type
            """)
            
            result = pd.read_sql(query, engine, params={'equipment_type': equipment_type})
            
            if result.empty:
                logger.warning(f"No specification labels found for equipment type: {equipment_type}")
                return {}
            
            # Extract the first (and should be only) row
            spec_row = result.iloc[0]
            logger.info(f"Found specification row for {equipment_type} with columns: {list(result.columns)}")
            
            # Build the mapping dictionary
            spec_mapping = {}
            duplicate_labels = {}  # Track potential duplicates
            
            # Map Specifications1 through Specifications50 (based on your data)
            for spec_num in range(1, 51):  # 1 to 50 based on your data
                spec_col = f'Specifications{spec_num}'
                
                if spec_col in result.columns:
                    spec_label = spec_row[spec_col]
                    
                    # Only include if the label exists and is not null/empty
                    if pd.notna(spec_label) and str(spec_label).strip() and str(spec_label).strip().upper() != 'NULL':
                        clean_label = str(spec_label).strip()
                        
                        # Check for duplicates in the mapping itself
                        if clean_label in duplicate_labels:
                            logger.warning(f"Duplicate label detected in {equipment_type}: '{clean_label}' found in both {duplicate_labels[clean_label]} and {spec_col}")
                            # Make the label unique
                            original_label = clean_label
                            counter = 1
                            while clean_label in spec_mapping.values():
                                clean_label = f"{original_label} ({counter})"
                                counter += 1
                        
                        spec_mapping[spec_col] = clean_label
                        duplicate_labels[clean_label] = spec_col
                        logger.debug(f"Mapped {spec_col} -> {clean_label}")
            
            logger.info(f"Successfully created dynamic mapping for {equipment_type}: {len(spec_mapping)} specifications")
            
            # Log any duplicates found
            if len(duplicate_labels) != len(spec_mapping):
                logger.warning(f"Potential duplicate labels detected for {equipment_type}")
            
            return spec_mapping
            
        except Exception as e:
            logger.error(f"Error fetching dynamic specification labels for {equipment_type}: {str(e)}")
            return {}

    def _apply_dynamic_specification_labels(self, df: pd.DataFrame, equipment_type: str = None) -> pd.DataFrame:
        """Apply dynamic specification labels - simplified for consistency"""
        try:
            if df.empty:
                return df
            
            logger.info(f"Applying dynamic specification labels for: {equipment_type or 'mixed equipment'}")
            
            # If specific equipment type provided, use its mapping
            if equipment_type:
                spec_labels = self._get_specification_labels_from_db(equipment_type)
                logger.info(f"Retrieved {len(spec_labels)} specification labels from database for {equipment_type}")
                
                if spec_labels:
                    labeled_df = df.copy()
                    
                    # Apply mapping directly - let pandas handle any issues
                    try:
                        labeled_df = labeled_df.rename(columns=spec_labels)
                        logger.info(f"Successfully applied {len(spec_labels)} specification labels for {equipment_type}")
                        
                        # Remove any remaining unlabeled specification columns
                        remaining_spec_cols = [col for col in labeled_df.columns if col.startswith('Specifications')]
                        if remaining_spec_cols:
                            labeled_df = labeled_df.drop(columns=remaining_spec_cols)
                            logger.info(f"Removed {len(remaining_spec_cols)} remaining unlabeled specification columns")
                        
                        return labeled_df
                        
                    except Exception as mapping_error:
                        logger.error(f"Error applying mapping for {equipment_type}: {str(mapping_error)}")
                        # If mapping fails, just remove unlabeled specifications
                        return self._remove_all_specification_columns(df)
                else:
                    logger.warning(f"No specification labels retrieved from database for {equipment_type}")
                    return self._remove_all_specification_columns(df)
            
            # If no equipment type, remove all specification columns
            return self._remove_all_specification_columns(df)
            
        except Exception as e:
            logger.error(f"Error applying dynamic specification labels: {str(e)}")
            return df

    def _remove_all_specification_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove all unlabeled specification columns"""
        try:
            columns_to_remove = [col for col in df.columns if col.startswith('Specifications')]
            if columns_to_remove:
                logger.info(f"Removing {len(columns_to_remove)} unlabeled specification columns")
                return df.drop(columns=columns_to_remove)
            return df
        except Exception as e:
            logger.error(f"Error removing specification columns: {str(e)}")
            return df

    # ========== OPTIMIZED CACHED DATA FETCHING METHODS ==========
    @st.cache_data(ttl=900, show_spinner="Loading customers...")
    def _fetch_all_customers(_self) -> list:
        """Fetch all customers with optimized caching"""
        try:
            logger.info("Fetching all customers from EquipmentDB")
            engine = get_engine_testdb()
            query = text("""
                SELECT DISTINCT [CustomerName] 
                FROM [dbo].[EquipmentDB] 
                WHERE [CustomerName] IS NOT NULL AND [CustomerName] != ''
                ORDER BY [CustomerName]
            """)
            result = pd.read_sql(query, engine)
            customers = result['CustomerName'].tolist()
            logger.info(f"Fetched {len(customers)} customers")
            return customers
        except Exception as e:
            logger.error(f"Error fetching customers: {str(e)}")
            return []

    @st.cache_data(ttl=900, show_spinner="Loading equipment types...")
    def _fetch_all_equipment_types(_self) -> list:
        """Fetch all equipment types with optimized caching"""
        try:
            logger.info("Fetching all equipment types")
            engine = get_engine_testdb()
            query = text("""
                SELECT DISTINCT [EquipmentType] 
                FROM [dbo].[EquipmentDB] 
                WHERE [EquipmentType] IS NOT NULL AND [EquipmentType] != ''
                ORDER BY [EquipmentType]
            """)
            result = pd.read_sql(query, engine)
            types = result['EquipmentType'].tolist()
            logger.info(f"Fetched {len(types)} equipment types")
            return types
        except Exception as e:
            logger.error(f"Error fetching equipment types: {str(e)}")
            return []

    @st.cache_data(ttl=900, show_spinner="Loading manufacturers...")
    def _fetch_all_manufacturers(_self) -> list:
        """Fetch all manufacturers with optimized caching"""
        try:
            logger.info("Fetching all manufacturers")
            engine = get_engine_testdb()
            query = text("""
                SELECT DISTINCT [Manufacturer] 
                FROM [dbo].[EquipmentDB] 
                WHERE [Manufacturer] IS NOT NULL AND [Manufacturer] != ''
                ORDER BY [Manufacturer]
            """)
            result = pd.read_sql(query, engine)
            manufacturers = result['Manufacturer'].tolist()
            logger.info(f"Fetched {len(manufacturers)} manufacturers")
            return manufacturers
        except Exception as e:
            logger.error(f"Error fetching manufacturers: {str(e)}")
            return []

    @st.cache_data(ttl=900, show_spinner="Loading projects...")
    def _fetch_all_projects(_self) -> list:
        """Fetch all project IDs with optimized caching"""
        try:
            logger.info("Fetching all projects")
            engine = get_engine_testdb()
            query = text("""
                SELECT DISTINCT [ParentProjectID] 
                FROM [dbo].[EquipmentDB] 
                WHERE [ParentProjectID] IS NOT NULL AND [ParentProjectID] != ''
                ORDER BY [ParentProjectID]
            """)
            result = pd.read_sql(query, engine)
            projects = result['ParentProjectID'].tolist()
            logger.info(f"Fetched {len(projects)} projects")
            return projects
        except Exception as e:
            logger.error(f"Error fetching projects: {str(e)}")
            return []

    @st.cache_data(ttl=900)
    def _fetch_all_mfg_projects(_self) -> list:
        """Fetch all manufacturer project IDs with optimized caching"""
        try:
            logger.info("Fetching all manufacturer projects")
            engine = get_engine_testdb()
            query = text("""
                SELECT DISTINCT [ManufacturerProjectID] 
                FROM [dbo].[EquipmentDB] 
                WHERE [ManufacturerProjectID] IS NOT NULL AND [ManufacturerProjectID] != ''
                ORDER BY [ManufacturerProjectID]
            """)
            result = pd.read_sql(query, engine)
            mfg_projects = result['ManufacturerProjectID'].tolist()
            logger.info(f"Fetched {len(mfg_projects)} manufacturer projects")
            return mfg_projects
        except Exception as e:
            logger.error(f"Error fetching manufacturer projects: {str(e)}")
            return []

    @st.cache_data(ttl=600, show_spinner="Filtering by customer...")
    def _fetch_customer_filtered_equipment_types(_self, customer_name: str) -> list:
        """Fetch equipment types for specific customer with optimized caching"""
        try:
            logger.info(f"Fetching equipment types for customer: {customer_name}")
            engine = get_engine_testdb()
            query = text("""
                SELECT DISTINCT [EquipmentType] 
                FROM [dbo].[EquipmentDB] 
                WHERE [CustomerName] = :customer_name 
                AND [EquipmentType] IS NOT NULL AND [EquipmentType] != ''
                ORDER BY [EquipmentType]
            """)
            result = pd.read_sql(query, engine, params={'customer_name': customer_name})
            types = result['EquipmentType'].tolist()
            logger.info(f"Fetched {len(types)} equipment types for {customer_name}")
            return types
        except Exception as e:
            logger.error(f"Error fetching customer equipment types for {customer_name}: {str(e)}")
            return []

    @st.cache_data(ttl=600)
    def _fetch_customer_filtered_manufacturers(_self, customer_name: str) -> list:
        """Fetch manufacturers for specific customer with optimized caching"""
        try:
            logger.info(f"Fetching manufacturers for customer: {customer_name}")
            engine = get_engine_testdb()
            query = text("""
                SELECT DISTINCT [Manufacturer] 
                FROM [dbo].[EquipmentDB] 
                WHERE [CustomerName] = :customer_name 
                AND [Manufacturer] IS NOT NULL AND [Manufacturer] != ''
                ORDER BY [Manufacturer]
            """)
            result = pd.read_sql(query, engine, params={'customer_name': customer_name})
            manufacturers = result['Manufacturer'].tolist()
            logger.info(f"Fetched {len(manufacturers)} manufacturers for {customer_name}")
            return manufacturers
        except Exception as e:
            logger.error(f"Error fetching customer manufacturers for {customer_name}: {str(e)}")
            return []

    @st.cache_data(ttl=600)  
    def _fetch_customer_filtered_projects(_self, customer_name: str) -> list:
        """Fetch projects for specific customer with optimized caching"""
        try:
            logger.info(f"Fetching projects for customer: {customer_name}")
            engine = get_engine_testdb()
            query = text("""
                SELECT DISTINCT [ParentProjectID] 
                FROM [dbo].[EquipmentDB] 
                WHERE [CustomerName] = :customer_name 
                AND [ParentProjectID] IS NOT NULL AND [ParentProjectID] != ''
                ORDER BY [ParentProjectID]
            """)
            result = pd.read_sql(query, engine, params={'customer_name': customer_name})
            projects = result['ParentProjectID'].tolist()
            logger.info(f"Fetched {len(projects)} projects for {customer_name}")
            return projects
        except Exception as e:
            logger.error(f"Error fetching customer projects for {customer_name}: {str(e)}")
            return []

    @st.cache_data(ttl=600)
    def _fetch_customer_filtered_mfg_projects(_self, customer_name: str) -> list:
        """Fetch manufacturer projects for specific customer with optimized caching"""
        try:
            logger.info(f"Fetching manufacturer projects for customer: {customer_name}")
            engine = get_engine_testdb()
            query = text("""
                SELECT DISTINCT [ManufacturerProjectID] 
                FROM [dbo].[EquipmentDB] 
                WHERE [CustomerName] = :customer_name 
                AND [ManufacturerProjectID] IS NOT NULL AND [ManufacturerProjectID] != ''
                ORDER BY [ManufacturerProjectID]
            """)
            result = pd.read_sql(query, engine, params={'customer_name': customer_name})
            mfg_projects = result['ManufacturerProjectID'].tolist()
            logger.info(f"Fetched {len(mfg_projects)} manufacturer projects for {customer_name}")
            return mfg_projects
        except Exception as e:
            logger.error(f"Error fetching customer manufacturer projects for {customer_name}: {str(e)}")
            return []

    @st.cache_data(ttl=600)
    def _fetch_customer_filtered_active_status(_self, customer_name: str) -> list:
        """Fetch active status values for specific customer with optimized caching"""
        try:
            logger.info(f"Fetching active status for customer: {customer_name}")
            engine = get_engine_testdb()
            query = text("""
                SELECT DISTINCT [ActiveStatus] 
                FROM [dbo].[EquipmentDB] 
                WHERE [CustomerName] = :customer_name 
                AND [ActiveStatus] IS NOT NULL AND [ActiveStatus] != ''
                ORDER BY [ActiveStatus]
            """)
            result = pd.read_sql(query, engine, params={'customer_name': customer_name})
            statuses = result['ActiveStatus'].tolist()
            logger.info(f"Fetched {len(statuses)} active status values for {customer_name}")
            return statuses
        except Exception as e:
            logger.error(f"Error fetching customer active status for {customer_name}: {str(e)}")
            return []

    @st.cache_data(ttl=900)
    def _fetch_all_active_status(_self) -> list:
        """Fetch all active status values with optimized caching"""
        try:
            logger.info("Fetching all active status values")
            engine = get_engine_testdb()
            query = text("""
                SELECT DISTINCT [ActiveStatus] 
                FROM [dbo].[EquipmentDB] 
                WHERE [ActiveStatus] IS NOT NULL AND [ActiveStatus] != ''
                ORDER BY [ActiveStatus]
            """)
            result = pd.read_sql(query, engine)
            statuses = result['ActiveStatus'].tolist()
            logger.info(f"Fetched {len(statuses)} active status values")
            return statuses
        except Exception as e:
            logger.error(f"Error fetching active status: {str(e)}")
            return []

    # ========== SEARCH INTERFACE METHODS ==========
    def _render_advanced_search(self):
        """Optimized advanced search interface with dynamic filtering"""
        
        # Log search access
        logger.info("Advanced search interface accessed")
        
        # ========== SEARCH CRITERIA ==========
        st.markdown("### 🎛️ Search Criteria")
        
        # Customer and Equipment Info in organized columns
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### 👥 Customer & Project Information")
            
            # Customer dropdown with performance optimization
            customers = self._fetch_all_customers()
            if customers:
                customer_options = ['-- Select Customer --'] + customers
                selected_customer = st.selectbox(
                    "Customer Name:", 
                    customer_options, 
                    key='customer_select'
                )
                selected_customer = selected_customer if selected_customer != '-- Select Customer --' else ''
            else:
                selected_customer = st.text_input("Customer Name:", key='customer_text')
            
            # Dynamic project filtering with optimized loading
            if selected_customer:
                logger.info(f"Customer selected: {selected_customer}, applying dynamic filters")
                projects = self._fetch_customer_filtered_projects(selected_customer)
                mfg_projects = self._fetch_customer_filtered_mfg_projects(selected_customer)
            else:
                projects = self._fetch_all_projects()
                mfg_projects = self._fetch_all_mfg_projects()
            
            # Project dropdowns
            if projects:
                project_options = ['-- Select Project --'] + projects
                selected_project = st.selectbox(f"Project ID ({len(projects)} available):", project_options, key='project_select')
                selected_project = selected_project if selected_project != '-- Select Project --' else ''
            else:
                selected_project = st.text_input("Project ID:", key='project_text')
            
            if mfg_projects:
                mfg_project_options = ['-- Select Mfg Project --'] + mfg_projects
                selected_mfg_project = st.selectbox(f"Manufacturer Project ID ({len(mfg_projects)} available):", mfg_project_options, key='mfg_project_select')
                selected_mfg_project = selected_mfg_project if selected_mfg_project != '-- Select Mfg Project --' else ''
            else:
                selected_mfg_project = st.text_input("Manufacturer Project ID:", key='mfg_project_text')
        
        with col2:
            st.markdown("##### 🔧 Equipment & Technical Details")
            
            # Dynamic equipment filtering with performance optimization
            if selected_customer:
                equipment_types = self._fetch_customer_filtered_equipment_types(selected_customer)
                manufacturers = self._fetch_customer_filtered_manufacturers(selected_customer)
                active_statuses = self._fetch_customer_filtered_active_status(selected_customer)
            else:
                equipment_types = self._fetch_all_equipment_types()
                manufacturers = self._fetch_all_manufacturers()
                active_statuses = self._fetch_all_active_status()
            
            # Equipment Type dropdown
            if equipment_types:
                eq_type_options = ['-- Select Equipment Type --'] + equipment_types
                selected_eq_type = st.selectbox(f"Equipment Type ({len(equipment_types)} available):", eq_type_options, key='eq_type_select')
                selected_eq_type = selected_eq_type if selected_eq_type != '-- Select Equipment Type --' else ''
            else:
                selected_eq_type = st.text_input("Equipment Type:", key='eq_type_text')
            
            # Manufacturer dropdown
            if manufacturers:
                mfg_options = ['-- Select Manufacturer --'] + manufacturers
                selected_manufacturer = st.selectbox(f"Manufacturer ({len(manufacturers)} available):", mfg_options, key='manufacturer_select')
                selected_manufacturer = selected_manufacturer if selected_manufacturer != '-- Select Manufacturer --' else ''
            else:
                selected_manufacturer = st.text_input("Manufacturer:", key='manufacturer_text')
            
            # Active Status dropdown
            if active_statuses:
                status_options = ['-- Select Status --'] + active_statuses
                selected_status = st.selectbox(f"Active Status ({len(active_statuses)} available):", status_options, key='status_select')
                selected_status = selected_status if selected_status != '-- Select Status --' else ''
            else:
                selected_status = st.text_input("Active Status:", key='status_text')
        
        # ========== DYNAMIC SPECIFICATION PREVIEW ==========
        if selected_eq_type:
            st.markdown("---")
            st.markdown("##### 📋 Dynamic Specification Preview")
            
            with st.expander(f"🔍 View {selected_eq_type} Specifications from Database"):
                spec_labels = self._get_specification_labels_from_db(selected_eq_type)
                if spec_labels:
                    st.success(f"✅ Found {len(spec_labels)} specification labels for {selected_eq_type} from database")
                    
                    # Display specifications in organized columns
                    spec_items = list(spec_labels.items())
                    
                    # Show specifications in 2 columns for better readability
                    if len(spec_items) > 0:
                        cols = st.columns(2)
                        for i, (spec_key, spec_label) in enumerate(spec_items):
                            col_idx = i % 2
                            spec_num = spec_key.replace('Specifications', '')
                            cols[col_idx].write(f"**Spec {spec_num}:** {spec_label}")
                        
                        # Add debug information
                        with st.expander("🔧 Database Query Details"):
                            st.write("**Database mapping details:**")
                            for spec_key, spec_label in spec_items:
                                st.write(f"`{spec_key}` → `{spec_label}`")
                else:
                    st.warning(f"⚠️ No specification mappings found in database for: {selected_eq_type}")
                    st.info("💡 The system will display generic 'Specifications1', 'Specifications2', etc.")
        
        # ========== SEARCH EXECUTION ==========
        st.markdown("---")
        if st.button("🎯 Execute Advanced Search", type="primary", key="execute_search", use_container_width=True):
            self._execute_advanced_search(
                selected_customer, selected_project, selected_mfg_project,
                selected_eq_type, selected_manufacturer, selected_status
            )
        
        # Clear button as secondary action
        if st.button("🧹 Clear All Selections", key="clear_search", use_container_width=True):
            logger.info("User cleared all search selections")
            st.rerun()
    
    def _render_quick_search(self):
        """Optimized quick search interface with dynamic specification mapping"""
        st.markdown("### 🔎 Quick Equipment Search")
        
        # ========== SEARCH INPUT ==========
        col1, col2 = st.columns([4, 1])
        
        with col1:
            search_term = st.text_input(
                "Search across all equipment fields:",
                placeholder="Enter customer name, serial number, equipment type, manufacturer, etc.",
                key='quick_search_input'
            )
            st.caption("🔍 Searches across ALL fields including specifications with dynamic database labels (unlabeled specs removed)")
        
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔍 Search", type="primary", key="quick_search_btn", use_container_width=True):
                if search_term and len(search_term.strip()) > 2:
                    logger.info(f"Quick search executed: {search_term}")
                    results = self._perform_enhanced_quick_search(search_term.strip())
                    # Apply dynamic specification labels and remove unlabeled specs
                    labeled_results = self._apply_dynamic_specification_labels_to_mixed_data(results)
                    self._display_single_table_results(labeled_results, f"Quick search: '{search_term}'", already_labeled=True)
                else:
                    st.warning("⚠️ Enter at least 3 characters to search")
        
        # ========== RECENT EQUIPMENT ==========
        st.markdown("---")
        st.markdown("### 📅 Recent Equipment")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            limit = st.selectbox("Show recent:", [10, 25, 50, 100], index=1, key="recent_limit")
        
        with col2:
            if st.button("📋 Load Recent Equipment", key="load_recent", use_container_width=True):
                logger.info(f"Loading {limit} recent equipment records")
                try:
                    engine = get_engine_testdb()
                    query = text(f"""
                        SELECT TOP {limit} * FROM [dbo].[{self.table_name}]
                        ORDER BY 
                            CASE WHEN RowCounter IS NOT NULL THEN RowCounter ELSE 0 END DESC,
                            SerialNumber DESC
                    """)
                    recent_df = pd.read_sql(query, engine)
                    
                    if not recent_df.empty:
                        logger.info(f"Loaded {len(recent_df)} recent equipment records")
                        # Apply dynamic specification labels and remove unlabeled specs
                        labeled_recent_df = self._apply_dynamic_specification_labels_to_mixed_data(recent_df)
                        
                        st.success(f"✅ **Loaded {len(recent_df)} recent equipment records**")
                        
                        # Show editable recent equipment
                        ordered_cols = self._get_ordered_columns_for_editing(labeled_recent_df)
                        
                        edited_recent = st.data_editor(
                            labeled_recent_df[ordered_cols],
                            use_container_width=True,
                            height=min(400, max(200, len(labeled_recent_df) * 40 + 100)),
                            hide_index=True,
                            num_rows="dynamic",
                            key="edit_recent_equipment"
                        )
                        
                        # Save button for recent equipment
                        if st.button("💾 Save Recent Equipment Changes", key="save_recent", use_container_width=True):
                            self._save_equipment_changes(edited_recent, labeled_recent_df, "Recent Equipment")
                    else:
                        logger.warning("No recent equipment found")
                        st.info("No recent equipment found")
                        
                except Exception as e:
                    logger.error(f"Failed to load recent equipment: {str(e)}")
                    st.error(f"Failed to load recent equipment: {str(e)}")
    
    def _render_data_analysis(self):
        """Enhanced data analysis interface with dynamic specification mapping testing"""
        st.markdown("### 📊 Equipment Database Analysis")
        
        col1, col2 = st.columns([2, 2])
        with col1:
            st.markdown("Generate comprehensive analysis with dynamic database-driven specification mapping")
            if st.button("📈 Generate Analysis", type="primary", key="generate_analysis", use_container_width=True):
                logger.info("Dynamic data analysis report generation started")
                self._generate_dynamic_analysis_report()
        
        with col2:
            st.markdown("Test dynamic specification mapping and filtering from database")
            if st.button("🔧 Test Database Mapping", key="test_db_mapping", use_container_width=True):
                self._test_database_specification_mapping()

    def _test_database_specification_mapping(self):
        """Test dynamic specification mapping from database"""
        st.markdown("#### 🔧 Database Specification Mapping Test")
        
        # Test with a few equipment types from your data
        test_types = ['BALER', 'AIR BOOSTER', 'CONVEYOR', 'DUST FILTER', 'STAR SCREEN']
        
        for eq_type in test_types:
            st.markdown(f"**Testing {eq_type} (from database):**")
            
            # Get the mapping from database
            mapping = self._get_specification_labels_from_db(eq_type)
            
            if mapping:
                st.success(f"✅ Found {len(mapping)} specification labels for {eq_type} from database")
                
                # Show first 10 mappings
                col1, col2 = st.columns(2)
                items = list(mapping.items())[:10]
                
                for i, (spec_key, spec_label) in enumerate(items):
                    col_idx = i % 2
                    spec_num = spec_key.replace('Specifications', '')
                    cols = [col1, col2]
                    cols[col_idx].write(f"**Spec {spec_num}:** {spec_label}")
                
                if len(mapping) > 10:
                    st.info(f"+ {len(mapping) - 10} more specifications mapped from database")
                    
            else:
                st.error(f"❌ No database mapping found for {eq_type}")
            
            st.markdown("---")
        
        # Test actual data application
        st.markdown("**Test with Real Equipment Data:**")
        
        if st.button("🧪 Test BALER Data Labeling from Database", key="test_baler_db_labeling"):
            try:
                engine = get_engine_testdb()
                query = text("""
                    SELECT TOP 3 * FROM [dbo].[EquipmentDB] 
                    WHERE EquipmentType = 'BALER'
                """)
                test_data = pd.read_sql(query, engine)
                
                if not test_data.empty:
                    st.markdown("**Original Data (first 3 BALER records):**")
                    # Show only first few columns to avoid clutter
                    display_cols = ['SerialNumber', 'EquipmentType', 'Specifications1', 'Specifications2', 'Specifications3', 'Specifications4', 'Specifications5']
                    available_cols = [col for col in display_cols if col in test_data.columns]
                    st.dataframe(test_data[available_cols], use_container_width=True)
                    
                    # Debug: Show what mapping will be applied
                    mapping = self._get_specification_labels_from_db('BALER')
                    if mapping:
                        st.markdown("**Database mapping for BALER:**")
                        mapping_display = []
                        for spec_key, spec_label in list(mapping.items())[:10]:
                            spec_num = spec_key.replace('Specifications', '')
                            mapping_display.append(f"Spec {spec_num}: {spec_label}")
                        st.write(" | ".join(mapping_display))
                        
                        st.info(f"📋 **Total mappings found:** {len(mapping)} out of 50 possible specifications")
                    
                    # Apply dynamic labels from database
                    labeled_data = self._apply_dynamic_specification_labels(test_data, 'BALER')
                    
                    st.markdown("**After Applying Database Labels:**")
                    
                    # Show exactly what columns we have now
                    all_columns = list(labeled_data.columns)
                    basic_cols = ['CustomerID', 'CustomerName', 'SerialNumber', 'EquipmentType', 'Manufacturer']
                    available_basic_cols = [col for col in basic_cols if col in labeled_data.columns]
                    
                    # Get specification columns (both labeled and unlabeled)
                    spec_cols = []
                    for col in labeled_data.columns:
                        if col.startswith('Specifications'):
                            spec_cols.append(f"{col} (unlabeled)")
                        elif col not in basic_cols + ['CustomerLocation', 'ActiveStatus', 'Model']:
                            spec_cols.append(f"{col} (labeled)")
                    
                    # Show first 10 columns
                    display_columns = available_basic_cols + [col.split(' (')[0] for col in spec_cols[:10]]
                    available_display_cols = [col for col in display_columns if col in labeled_data.columns]
                    
                    if available_display_cols:
                        st.dataframe(labeled_data[available_display_cols], use_container_width=True)
                    
                    # Show detailed column analysis
                    st.markdown("**Column Structure Analysis:**")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        basic_count = len([col for col in labeled_data.columns if col in basic_cols])
                        st.metric("Basic Columns", basic_count)
                    
                    with col2:
                        labeled_spec_count = len([col for col in labeled_data.columns 
                                                if not col.startswith('Specifications') 
                                                and col not in basic_cols + ['CustomerLocation', 'ActiveStatus', 'Model']])
                        st.metric("Labeled Specifications", labeled_spec_count)
                    
                    with col3:
                        unlabeled_spec_count = len([col for col in labeled_data.columns if col.startswith('Specifications')])
                        st.metric("Unlabeled Specifications", unlabeled_spec_count)
                    
                    # Show what the interface will look like
                    ordered_columns = self._get_ordered_columns_for_editing(labeled_data)
                    st.markdown("**Final Interface Column Order:**")
                    st.write(", ".join(ordered_columns[:15]) + ("..." if len(ordered_columns) > 15 else ""))
                    
                    if labeled_spec_count > 0:
                        st.success(f"✅ **Interface Consistency:** Database mapping applied successfully")
                    else:
                        st.warning("⚠️ **Interface Mismatch:** No specification labels were applied")
                        
                        # Debug why mapping wasn't applied
                        if mapping:
                            st.write("**Debug: Mapping exists but not applied**")
                            st.write(f"- Database mapping size: {len(mapping)}")
                            st.write(f"- Sample mapping: {dict(list(mapping.items())[:3])}")
                            
                            # Check if column names match
                            available_spec_cols = [col for col in test_data.columns if col.startswith('Specifications')]
                            matching_cols = [col for col in available_spec_cols if col in mapping]
                            st.write(f"- Available spec columns in data: {len(available_spec_cols)}")
                            st.write(f"- Matching columns for mapping: {len(matching_cols)}")
                        else:
                            st.error("❌ No mapping retrieved from database for BALER")
                else:
                    st.warning("No BALER equipment found in database")
                    
            except Exception as e:
                st.error(f"Database test failed: {str(e)}")
                logger.error(f"BALER database test failed: {str(e)}")
                
                # Additional debugging for the duplicate error
                if "Duplicate column names" in str(e):
                    st.error("🔍 **Duplicate Column Names Error Detected**")
                    st.info("💡 This happens when multiple Specifications columns map to the same label")
                    st.info("🔧 **Solution:** The system now prevents this by keeping original names for mixed data")

    # ========== SEARCH EXECUTION METHODS ==========
    def _execute_advanced_search(self, customer, project, mfg_project, eq_type, manufacturer, status):
        """Execute optimized advanced search with dynamic specification mapping"""
        # Build criteria and log search parameters
        criteria = {}
        if customer: criteria['CustomerName'] = customer
        if project: criteria['ParentProjectID'] = project
        if mfg_project: criteria['ManufacturerProjectID'] = mfg_project
        if eq_type: criteria['EquipmentType'] = eq_type
        if manufacturer: criteria['Manufacturer'] = manufacturer
        if status: criteria['ActiveStatus'] = status
        
        if criteria:
            logger.info(f"Advanced search executed with criteria: {criteria}")
            
            with st.spinner("🔍 Searching equipment database with dynamic specification mapping..."):
                results = self._perform_advanced_search(criteria)
            
            # Log search results
            logger.info(f"Advanced search returned {len(results)} records")
            
            if customer:
                search_desc = f"Advanced search for {customer} with {len(criteria)} criteria"
            else:
                search_desc = f"Advanced search with {len(criteria)} criteria"
            
            # Apply dynamic specification labels based on equipment type and remove unlabeled specs
            if eq_type:
                # Specific equipment type selected - apply its mapping and remove unlabeled specs
                labeled_results = self._apply_dynamic_specification_labels(results, eq_type)
            else:
                # Mixed equipment types - handle safely and remove unlabeled specs
                labeled_results = self._apply_dynamic_specification_labels_to_mixed_data(results)
            
            self._display_equipment_wise_results(labeled_results, search_desc, eq_type)
        else:
            logger.warning("Advanced search attempted with no criteria")
            st.warning("⚠️ Please select at least one search criterion from the dropdowns above")
    
    def _perform_enhanced_quick_search(self, search_term: str) -> pd.DataFrame:
        """Perform optimized quick search across multiple fields including specifications"""
        try:
            logger.info(f"Performing enhanced quick search for term: {search_term}")
            engine = get_engine_testdb()
            
            # Build dynamic query to search specifications 1-50
            spec_conditions = []
            for spec_num in range(1, 51):  # Based on your data going to Specifications50
                spec_conditions.append(f"[Specifications{spec_num}] LIKE :search_term")
            
            spec_where_clause = " OR ".join(spec_conditions)
            
            query = text(f"""
                SELECT TOP 200 * FROM [dbo].[{self.table_name}] 
                WHERE 
                    [CustomerID] LIKE :search_term OR
                    [CustomerName] LIKE :search_term OR
                    [CustomerLocation] LIKE :search_term OR
                    [SerialNumber] LIKE :search_term OR
                    [EquipmentType] LIKE :search_term OR
                    [Manufacturer] LIKE :search_term OR
                    [ParentProjectID] LIKE :search_term OR
                    [ManufacturerProjectID] LIKE :search_term OR
                    [Model] LIKE :search_term OR
                    [FunctionalType] LIKE :search_term OR
                    [ManufacturerModelDescription] LIKE :search_term OR
                    [ActiveStatus] LIKE :search_term OR
                    {spec_where_clause}
                ORDER BY CustomerName, EquipmentType, SerialNumber
            """)
            result = pd.read_sql(query, engine, params={'search_term': f'%{search_term}%'})
            logger.info(f"Enhanced quick search returned {len(result)} records")
            return result
        except Exception as e:
            logger.error(f"Enhanced quick search failed for term '{search_term}': {str(e)}")
            st.error(f"Enhanced quick search failed: {str(e)}")
            return pd.DataFrame()
    
    def _perform_advanced_search(self, criteria: Dict[str, str]) -> pd.DataFrame:
        """Perform optimized advanced search with multiple criteria"""
        try:
            logger.info(f"Performing advanced search with criteria: {criteria}")
            engine = get_engine_testdb()
            where_clauses = []
            params = {}
            
            for field, value in criteria.items():
                if value and str(value).strip():
                    param_name = f'{field.lower()}_param'
                    where_clauses.append(f"[{field}] LIKE :{param_name}")
                    params[param_name] = f'%{str(value).strip()}%'
            
            if not where_clauses:
                logger.warning("Advanced search called with empty criteria")
                return pd.DataFrame()
            
            query = text(f"""
                SELECT * FROM [dbo].[{self.table_name}] 
                WHERE {' AND '.join(where_clauses)}
                ORDER BY CustomerName, EquipmentType, SerialNumber
            """)
            
            result = pd.read_sql(query, engine, params=params)
            logger.info(f"Advanced search returned {len(result)} records")
            return result
        except Exception as e:
            logger.error(f"Advanced search failed with criteria {criteria}: {str(e)}")
            st.error(f"Advanced search failed: {str(e)}")
            return pd.DataFrame()

    def _apply_dynamic_specification_labels_to_mixed_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply dynamic specification labels to mixed equipment data - always try to apply best mapping"""
        try:
            if df.empty or 'EquipmentType' not in df.columns:
                return self._remove_all_specification_columns(df)
            
            logger.info("Applying dynamic specification labeling to equipment data")
            
            # Check if data contains only one equipment type
            unique_types = df['EquipmentType'].dropna().unique()
            
            if len(unique_types) == 1:
                # Single equipment type - apply specific mapping
                equipment_type = unique_types[0]
                logger.info(f"Single equipment type detected: {equipment_type}, applying specific mapping")
                return self._apply_dynamic_specification_labels(df, equipment_type)
            
            elif len(unique_types) > 1:
                # Multiple equipment types - apply mapping from most common type
                type_counts = df['EquipmentType'].value_counts()
                primary_type = type_counts.index[0]
                
                logger.info(f"Mixed equipment types detected: {list(unique_types)}, using {primary_type} as primary for mapping")
                st.info(f"📊 **Mixed Equipment Types:** Using {primary_type} specification mapping for {', '.join(unique_types[:3])}{'...' if len(unique_types) > 3 else ''}")
                
                # Apply the primary type's mapping to all data
                return self._apply_dynamic_specification_labels(df, primary_type)
            
            # No equipment type data - remove all specification columns
            return self._remove_all_specification_columns(df)
            
        except Exception as e:
            logger.error(f"Error applying dynamic labels to mixed data: {str(e)}")
            return df
    
    # ========== EDITABLE TABLE HELPER METHODS ==========
    def _get_ordered_columns_for_editing(self, df: pd.DataFrame) -> list:
        """Get columns in logical order for editing interface - matching SQL table structure"""
        try:
            # Define the preferred column order matching your SQL table structure
            priority_columns = [
                'CustomerID', 'CustomerName', 'CustomerLocation', 'ActiveStatus', 
                'SortSystemPosition', 'SerialNumber', 'OtherOrPreviousPosition', 
                'CustomerPositionNo', 'YearManufactured', 'SalesDateWarrantyStartDate', 
                'InstallDate', 'Manufacturer', 'ManufacturerProjectID', 'ParentProjectID', 
                'EquipmentType', 'FunctionalType', 'FunctionalPosition', 
                'ManufacturerModelDescription', 'Model'
            ]
            
            # Get specification columns (labeled ones) and system columns
            spec_columns = []
            system_columns = []
            
            for col in df.columns:
                if col in priority_columns:
                    continue  # Will be added in order
                elif col.startswith('Specifications'):
                    # This should have been removed if unlabeled, but include if still present
                    spec_columns.append(col)
                elif col in [
                    'Notes', 'EquipmentKey', 'RecordHistory', 'RowCounter', 
                    'MachineInfoID', 'UploadsPendingID', 'HashedSerialNumber'
                ]:
                    # System columns go at the end
                    system_columns.append(col)
                else:
                    # This is likely a labeled specification column
                    spec_columns.append(col)
            
            # Build final column order matching SQL table structure
            ordered_columns = []
            
            # Add priority columns first (matching SQL table order)
            for col in priority_columns:
                if col in df.columns:
                    ordered_columns.append(col)
            
            # Add specification columns (both labeled and unlabeled) in order
            # Sort specification columns by number if they're still SpecificationsX format
            spec_columns_sorted = []
            other_spec_columns = []
            
            for col in spec_columns:
                if col.startswith('Specifications') and col[13:].isdigit():
                    spec_columns_sorted.append((int(col[13:]), col))
                else:
                    other_spec_columns.append(col)
            
            # Add numbered specifications in order
            spec_columns_sorted.sort()
            for _, col in spec_columns_sorted:
                ordered_columns.append(col)
            
            # Add other specification columns (labeled ones)
            ordered_columns.extend(sorted(other_spec_columns))
            
            # Add system columns at the end
            ordered_columns.extend(sorted(system_columns))
            
            logger.info(f"Ordered {len(ordered_columns)} columns for editing interface matching SQL structure")
            return ordered_columns
            
        except Exception as e:
            logger.error(f"Error ordering columns for editing: {str(e)}")
            return list(df.columns)

    def _save_equipment_changes(self, edited_data: pd.DataFrame, original_data: pd.DataFrame, equipment_type: str):
        """Save changes made in the editable interface back to database"""
        try:
            logger.info(f"Attempting to save changes for {equipment_type}")
            
            # Compare edited data with original data
            if edited_data.equals(original_data):
                st.info("ℹ️ No changes detected - nothing to save")
                return
            
            # Detect changes
            changes_detected = []
            
            # Check for modified rows
            if len(edited_data) == len(original_data):
                for idx in range(len(edited_data)):
                    for col in edited_data.columns:
                        if col in original_data.columns:
                            old_val = original_data.iloc[idx][col] if idx < len(original_data) else None
                            new_val = edited_data.iloc[idx][col]
                            
                            if str(old_val) != str(new_val):
                                changes_detected.append({
                                    'row': idx,
                                    'column': col,
                                    'old_value': old_val,
                                    'new_value': new_val
                                })
            
            # Check for added/removed rows
            row_changes = len(edited_data) - len(original_data)
            
            if changes_detected or row_changes != 0:
                st.success(f"✅ **Changes Detected:** {len(changes_detected)} field changes, {row_changes} row changes")
                
                # Show changes summary
                if changes_detected:
                    with st.expander("🔍 View Changes Summary"):
                        changes_df = pd.DataFrame(changes_detected)
                        st.dataframe(changes_df, use_container_width=True)
                
                # Save confirmation
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"✅ Confirm Save to Database", key=f"confirm_save_{equipment_type}", type="primary"):
                        # Here you would implement the actual database save logic
                        # For now, just show what would be saved
                        st.success("💾 **Save functionality ready!**")
                        st.info("🔧 **Next Step:** Implement database UPDATE queries to save changes")
                        logger.info(f"Changes confirmed for saving: {len(changes_detected)} changes, {row_changes} row changes")
                
                with col2:
                    if st.button(f"❌ Cancel Changes", key=f"cancel_save_{equipment_type}"):
                        st.warning("❌ Changes cancelled")
                        st.rerun()
            
            else:
                st.info("ℹ️ No changes detected")
                
        except Exception as e:
            logger.error(f"Error saving equipment changes: {str(e)}")
            st.error(f"Error saving changes: {str(e)}")

    # ========== RESULTS DISPLAY METHODS (EDITABLE, NO EXPORT) ==========
    def _display_equipment_wise_results(self, results: pd.DataFrame, search_description: str, specific_equipment_type: str = None):
        """Display results grouped by equipment type with safe dynamic specification labels"""
        if results.empty:
            logger.warning(f"No equipment found for search: {search_description}")
            st.info(f"🔍 No equipment found for: {search_description}")
            return
        
        logger.info(f"Displaying equipment-wise results with dynamic specifications: {len(results)} records")
        st.success(f"✅ **Found {len(results)} equipment records**")
        
        # Overall statistics with mode-friendly HTML metrics
        overall_customers = results['CustomerName'].nunique() if 'CustomerName' in results.columns else 0
        overall_types = results['EquipmentType'].nunique() if 'EquipmentType' in results.columns else 0
        overall_manufacturers = results['Manufacturer'].nunique() if 'Manufacturer' in results.columns else 0
        overall_projects = results['ParentProjectID'].nunique() if 'ParentProjectID' in results.columns else 0
        
        metrics_html = create_equipment_metrics_html(overall_customers, overall_types, overall_manufacturers, overall_projects)
        st.markdown(metrics_html, unsafe_allow_html=True)
        
        # Show specification coverage statistics
        self._display_specification_coverage(results)
        
        # Group by Equipment Type and display with safe dynamic labels
        if 'EquipmentType' in results.columns:
            grouped = results.groupby('EquipmentType')
            equipment_types = sorted(grouped.groups.keys())
            logger.info(f"Grouped results into {len(equipment_types)} equipment types")
            
            st.markdown("---")
            st.markdown(f"#### 📊 Equipment Distribution: {len(equipment_types)} Types Found")
            
            # Show specification mapping info
            if len(equipment_types) > 1:
                st.info("📋 **Specification Labels:** Each equipment type will show with its specific database-driven labels")
            
            for i, eq_type in enumerate(equipment_types):
                equipment_data = grouped.get_group(eq_type)
                
                # Apply dynamic specification labels for this specific equipment type (safe since it's grouped)
                labeled_equipment_data = self._apply_dynamic_specification_labels(equipment_data, eq_type)
                
                # Equipment type header
                header_html = create_equipment_header_html(eq_type)
                st.markdown(header_html, unsafe_allow_html=True)
                
                # Type-specific metrics
                type_customers = equipment_data['CustomerName'].nunique() if 'CustomerName' in equipment_data.columns else 0
                type_manufacturers = equipment_data['Manufacturer'].nunique() if 'Manufacturer' in equipment_data.columns else 0
                type_models = equipment_data['Model'].nunique() if 'Model' in equipment_data.columns else 0
                
                type_metrics_html = create_equipment_metrics_html(len(equipment_data), type_customers, type_manufacturers, type_models)
                st.markdown(type_metrics_html, unsafe_allow_html=True)
                
                # Show if specification mapping was applied
                spec_mapping = self._get_specification_labels_from_db(eq_type)
                if spec_mapping:
                    mapped_count = len([col for col in labeled_equipment_data.columns if not col.startswith('Specifications')])
                    original_count = len([col for col in equipment_data.columns if not col.startswith('Specifications')])
                    applied_mappings = mapped_count - original_count
                    
                    if applied_mappings > 0:
                        st.success(f"✅ Applied {applied_mappings} database-driven specification labels for {eq_type}")
                    else:
                        st.info(f"📋 Using generic specification names for {eq_type} (no database mapping applied)")
                else:
                    st.info(f"📋 No database mapping found for {eq_type}")
                
                # Display editable table with dynamic specification labels
                st.markdown("**📝 Editable Equipment Data:**")
                
                # Configure column order for better editing experience
                ordered_columns = self._get_ordered_columns_for_editing(labeled_equipment_data)
                
                # Make table editable
                edited_data = st.data_editor(
                    labeled_equipment_data[ordered_columns],
                    use_container_width=True,
                    height=min(500, max(200, len(labeled_equipment_data) * 40 + 100)),
                    hide_index=True,
                    num_rows="dynamic",  # Allow adding/deleting rows
                    key=f"edit_{eq_type}_{i}"
                )
                
                # Save changes functionality
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button(f"💾 Save {eq_type} Changes", key=f"save_{eq_type}_{i}", use_container_width=True):
                        logger.info(f"Saving changes for equipment type: {eq_type}")
                        self._save_equipment_changes(edited_data, labeled_equipment_data, eq_type)
                
                with col2:
                    if st.button(f"📊 Analyze {eq_type}", key=f"analyze_{eq_type}_{i}", use_container_width=True):
                        logger.info(f"Dynamic analysis initiated for equipment type: {eq_type}")
                        self._analyze_equipment_type_dynamic(edited_data, eq_type)
                
                with col3:
                    # Show specification coverage for this type
                    spec_coverage = self._calculate_specification_coverage(equipment_data)
                    st.metric("Spec Coverage", f"{spec_coverage:.1f}%")
                
                # Separator between types
                if i < len(equipment_types) - 1:
                    st.markdown("---")
        
        else:
            # Fallback for single equipment type or no type grouping
            labeled_results = self._apply_dynamic_specification_labels_to_mixed_data(results)
            self._display_single_table_results(labeled_results, search_description, already_labeled=True)
    
    def _display_single_table_results(self, results: pd.DataFrame, search_description: str, already_labeled: bool = False):
        """Display results in single table with dynamic specification labels"""
        if results.empty:
            logger.warning(f"No equipment found for: {search_description}")
            st.info(f"🔍 No equipment found for: {search_description}")
            return
        
        logger.info(f"Displaying single table results with dynamic specifications: {len(results)} records")
        st.success(f"✅ **Found {len(results)} equipment records with dynamic specification mapping**")
        
        # Statistics with mode-friendly HTML metrics
        unique_customers = results['CustomerName'].nunique() if 'CustomerName' in results.columns else 0
        unique_types = results['EquipmentType'].nunique() if 'EquipmentType' in results.columns else 0
        unique_manufacturers = results['Manufacturer'].nunique() if 'Manufacturer' in results.columns else 0
        unique_projects = results['ParentProjectID'].nunique() if 'ParentProjectID' in results.columns else 0
        
        metrics_html = create_equipment_metrics_html(unique_customers, unique_types, unique_manufacturers, unique_projects)
        st.markdown(metrics_html, unsafe_allow_html=True)
        
        # Show specification coverage
        self._display_specification_coverage(results)
        
        # Apply dynamic specification labels if not already done
        if not already_labeled:
            labeled_results = self._apply_dynamic_specification_labels_to_mixed_data(results)
            logger.info("Applied dynamic specification labels to single table results")
        else:
            labeled_results = results
        
        # Display editable table with dynamic specification labels
        st.markdown("**📝 Editable Equipment Data:**")
        
        # Configure column order for better editing experience
        ordered_columns = self._get_ordered_columns_for_editing(labeled_results)
        
        # Make table editable
        edited_results = st.data_editor(
            labeled_results[ordered_columns], 
            use_container_width=True, 
            height=min(600, max(300, len(labeled_results) * 40 + 100)),
            hide_index=True,
            num_rows="dynamic",  # Allow adding/deleting rows
            key=f"edit_single_{hash(search_description)}"
        )
        
        # Action buttons
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 Save Changes", key=f"save_{hash(search_description)}", use_container_width=True):
                logger.info(f"Saving changes for search results: {search_description}")
                self._save_equipment_changes(edited_results, labeled_results, "Mixed Equipment")
        
        with col2:
            if st.button("📊 Analyze Results", key=f"analyze_{hash(search_description)}", use_container_width=True):
                logger.info(f"Dynamic analysis initiated for search results: {search_description}")
                self._analyze_equipment_data_dynamic(edited_results)
        
        with col3:
            spec_coverage = self._calculate_specification_coverage(results)
            st.metric("Specification Coverage", f"{spec_coverage:.1f}%")

    def _display_specification_coverage(self, df: pd.DataFrame):
        """Display specification coverage statistics showing what mapping was applied"""
        try:
            if df.empty:
                return
            
            # Count labeled specification columns (those that were successfully mapped)
            labeled_spec_cols = []
            unlabeled_spec_cols = []
            
            for col in df.columns:
                if col.startswith('Specifications'):
                    unlabeled_spec_cols.append(col)
                elif col not in [
                    'CustomerID', 'CustomerName', 'CustomerLocation', 'ActiveStatus', 
                    'SortSystemPosition', 'SerialNumber', 'OtherOrPreviousPosition', 
                    'CustomerPositionNo', 'YearManufactured', 'SalesDateWarrantyStartDate', 
                    'InstallDate', 'Manufacturer', 'ManufacturerProjectID', 'ParentProjectID', 
                    'EquipmentType', 'FunctionalType', 'FunctionalPosition', 
                    'ManufacturerModelDescription', 'Model', 'Notes', 'EquipmentKey', 
                    'RecordHistory', 'RowCounter', 'MachineInfoID', 'UploadsPendingID', 
                    'HashedSerialNumber'
                ]:
                    # This is likely a labeled specification column
                    labeled_spec_cols.append(col)
            
            # Show what mapping was applied
            if labeled_spec_cols:
                specs_with_data = sum(1 for col in labeled_spec_cols if df[col].notna().sum() > 0)
                st.success(f"✅ **Database Mapping Applied:** {len(labeled_spec_cols)} specifications labeled, {specs_with_data} contain data")
                
                # Show sample of mapped specifications
                if len(labeled_spec_cols) > 0:
                    sample_specs = labeled_spec_cols[:5]
                    st.caption(f"📋 **Sample Labels:** {', '.join(sample_specs)}")
            
            elif unlabeled_spec_cols:
                st.info(f"📊 **Generic Labels:** {len(unlabeled_spec_cols)} specifications showing as 'Specifications1, 2, 3...' (no database mapping found)")
            
        except Exception as e:
            logger.error(f"Error displaying specification coverage: {str(e)}")

    def _show_type_specification_usage(self, labeled_data: pd.DataFrame, equipment_type: str):
        """Show specification usage for specific equipment type"""
        try:
            # Count labeled specification columns (those that have been renamed from SpecificationsX)
            labeled_spec_cols = []
            unlabeled_spec_cols = []
            
            for col in labeled_data.columns:
                if col.startswith('Specifications'):
                    unlabeled_spec_cols.append(col)
                elif col not in ['CustomerName', 'CustomerID', 'SerialNumber', 'EquipmentType', 
                               'Manufacturer', 'Model', 'ActiveStatus', 'ParentProjectID', 
                               'ManufacturerProjectID', 'CustomerLocation', 'YearManufactured']:
                    # This is likely a labeled specification column
                    if labeled_data[col].notna().any():
                        labeled_spec_cols.append(col)
            
            # Show labeled specifications usage
            if labeled_spec_cols:
                specs_with_data = []
                for col in labeled_spec_cols:
                    non_null_count = labeled_data[col].notna().sum()
                    if non_null_count > 0:
                        coverage = (non_null_count / len(labeled_data)) * 100
                        specs_with_data.append({
                            'specification': col,
                            'records': non_null_count,
                            'coverage': coverage
                        })
                
                if specs_with_data:
                    specs_with_data.sort(key=lambda x: x['coverage'], reverse=True)
                    top_specs = specs_with_data[:5]  # Show top 5
                    
                    st.caption(f"📊 **Dynamic Labels Applied for {equipment_type}:** " + 
                              ", ".join([f"{s['specification']} ({s['coverage']:.0f}%)" for s in top_specs]))
            
        except Exception as e:
            logger.error(f"Error showing type specification usage: {str(e)}")

    def _calculate_specification_coverage(self, df: pd.DataFrame) -> float:
        """Calculate specification coverage percentage for labeled specifications only"""
        try:
            if df.empty:
                return 0.0
            
            # Count labeled specification columns (non-Specifications columns that are specifications)
            labeled_spec_cols = []
            for col in df.columns:
                if not col.startswith('Specifications') and col not in [
                    'CustomerName', 'CustomerID', 'SerialNumber', 'EquipmentType', 
                    'Manufacturer', 'Model', 'ActiveStatus', 'ParentProjectID', 
                    'ManufacturerProjectID', 'CustomerLocation', 'YearManufactured',
                    'InstallDate', 'SalesDateWarrantyStartDate', 'FunctionalType',
                    'FunctionalPosition', 'ManufacturerModelDescription', 'Notes',
                    'EquipmentKey', 'RecordHistory', 'RowCounter', 'MachineInfoID',
                    'UploadsPendingID', 'HashedSerialNumber', 'SortSystemPosition',
                    'OtherOrPreviousPosition', 'CustomerPositionNo'
                ]:
                    # This is likely a labeled specification column
                    labeled_spec_cols.append(col)
            
            if labeled_spec_cols:
                total_spec_cells = len(labeled_spec_cols) * len(df)
                filled_spec_cells = sum(df[col].notna().sum() for col in labeled_spec_cols)
                coverage = (filled_spec_cells / total_spec_cells) * 100 if total_spec_cells > 0 else 0
                return coverage
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating specification coverage: {str(e)}")
            return 0.0
    
    # ========== ANALYSIS METHODS (NO EXPORT FUNCTIONALITY) ==========
    def _analyze_equipment_type_dynamic(self, data: pd.DataFrame, equipment_type: str):
        """Dynamic analysis for specific equipment type with database-driven specifications"""
        logger.info(f"Generating dynamic analysis for equipment type: {equipment_type}")
        
        st.markdown(f"#### 📊 Dynamic Analysis: {equipment_type} Equipment")
        
        # Basic metrics
        total_records = len(data)
        unique_customers = data['CustomerName'].nunique() if 'CustomerName' in data.columns else 0
        unique_manufacturers = data['Manufacturer'].nunique() if 'Manufacturer' in data.columns else 0
        spec_coverage = self._calculate_specification_coverage(data)
        
        # Display enhanced metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Records", total_records)
        with col2:
            st.metric("Unique Customers", unique_customers)
        with col3:
            st.metric("Manufacturers", unique_manufacturers)
        with col4:
            st.metric("Spec Coverage", f"{spec_coverage:.1f}%")
        
        # Dynamic specification analysis
        self._analyze_dynamic_specifications(data, equipment_type)
        
        # Customer distribution for this equipment type
        if 'CustomerName' in data.columns:
            st.markdown("**Customer Distribution:**")
            customer_counts = data['CustomerName'].value_counts().head(10)
            st.bar_chart(customer_counts)
        
        # Manufacturer analysis
        if 'Manufacturer' in data.columns:
            st.markdown("**Manufacturer Distribution:**")
            mfg_counts = data['Manufacturer'].value_counts()
            st.bar_chart(mfg_counts)
    
    def _analyze_equipment_data_dynamic(self, data: pd.DataFrame):
        """Dynamic analysis for mixed equipment data"""
        logger.info(f"Generating dynamic analysis for {len(data)} mixed equipment records")
        
        st.markdown("#### 📊 Comprehensive Equipment Analysis with Dynamic Specifications")
        
        # Equipment type distribution
        if 'EquipmentType' in data.columns:
            st.markdown("**Equipment Type Distribution:**")
            type_counts = data['EquipmentType'].value_counts()
            st.bar_chart(type_counts)
        
        # Customer analysis
        if 'CustomerName' in data.columns:
            st.markdown("**Top Customers:**")
            customer_counts = data['CustomerName'].value_counts().head(15)
            st.bar_chart(customer_counts)
        
        # Manufacturer analysis
        if 'Manufacturer' in data.columns:
            st.markdown("**Manufacturer Distribution:**")
            mfg_counts = data['Manufacturer'].value_counts().head(15)
            st.bar_chart(mfg_counts)
        
        # Dynamic specifications analysis across all equipment types (only labeled specs)
        self._analyze_dynamic_specifications(data, "All Equipment Types")
        
        # Active status analysis
        if 'ActiveStatus' in data.columns:
            st.markdown("**Active Status Distribution:**")
            status_counts = data['ActiveStatus'].value_counts()
            st.bar_chart(status_counts)
    
    def _analyze_dynamic_specifications(self, data: pd.DataFrame, equipment_type: str):
        """Dynamic specification analysis using database-driven labels (only labeled specs)"""
        logger.info(f"Analyzing dynamic specifications for: {equipment_type}")
        
        st.markdown(f"**Dynamic Specification Analysis for {equipment_type}:**")
        
        # Find labeled specification columns (those that have been mapped from database)
        labeled_spec_columns = []
        unlabeled_spec_columns = []
        
        # Categorize specification columns
        for col in data.columns:
            if col.startswith('Specifications'):
                unlabeled_spec_columns.append(col)
            elif col not in [
                'CustomerName', 'CustomerID', 'SerialNumber', 'EquipmentType', 
                'Manufacturer', 'Model', 'ActiveStatus', 'ParentProjectID', 
                'ManufacturerProjectID', 'CustomerLocation', 'YearManufactured',
                'InstallDate', 'SalesDateWarrantyStartDate', 'FunctionalType',
                'FunctionalPosition', 'ManufacturerModelDescription', 'Notes',
                'EquipmentKey', 'RecordHistory', 'RowCounter', 'MachineInfoID',
                'UploadsPendingID', 'HashedSerialNumber', 'SortSystemPosition',
                'OtherOrPreviousPosition', 'CustomerPositionNo'
            ]:
                # This is likely a dynamically labeled specification column
                if data[col].notna().any():
                    labeled_spec_columns.append(col)
        
        if labeled_spec_columns:
            logger.info(f"Found {len(labeled_spec_columns)} labeled specification columns (unlabeled filtered out)")
            
            # Specification coverage overview
            st.markdown("**Database-Mapped Specification Analysis:**")
            
            coverage_data = []
            for col in labeled_spec_columns:
                non_null_count = data[col].notna().sum()
                if non_null_count > 0:
                    unique_values = data[col].nunique()
                    coverage_pct = (non_null_count / len(data)) * 100
                    
                    coverage_data.append({
                        'Specification': col,
                        'Records with Data': non_null_count,
                        'Unique Values': unique_values,
                        'Coverage %': f"{coverage_pct:.1f}%"
                    })
            
            if coverage_data:
                # Sort by coverage percentage
                coverage_data.sort(key=lambda x: float(x['Coverage %'].replace('%', '')), reverse=True)
                coverage_df = pd.DataFrame(coverage_data)
                
                # Show all labeled specifications
                st.dataframe(coverage_df, use_container_width=True)
                
                st.success(f"✅ **Clean Interface:** Showing {len(coverage_data)} database-mapped specifications only")
                
                # Interactive specification charts
                st.markdown("**Specification Value Analysis:**")
                
                # Let user select which specification to analyze
                chartable_specs = [item['Specification'] for item in coverage_data 
                                 if int(item['Unique Values']) < 50 and int(item['Unique Values']) > 1]
                
                if chartable_specs:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        selected_spec = st.selectbox(
                            "Select specification for detailed analysis:", 
                            [''] + chartable_specs[:10], 
                            key=f"dynamic_spec_chart_{equipment_type}"
                        )
                    
                    with col2:
                        if selected_spec and st.button("📈 Analyze Specification", key=f"analyze_spec_{equipment_type}_{selected_spec}"):
                            self._analyze_single_specification(data, selected_spec, equipment_type)
        else:
            if unlabeled_spec_columns:
                st.info(f"📊 **Clean Interface:** {len(unlabeled_spec_columns)} unlabeled specification columns filtered out - no database mappings available")
            else:
                st.info("📊 No specification data available for detailed analysis")

    def _analyze_single_specification(self, data: pd.DataFrame, spec_name: str, equipment_type: str):
        """Analyze a single specification in detail"""
        try:
            logger.info(f"Analyzing specification '{spec_name}' for {equipment_type}")
            
            # Find the actual column name
            spec_col = spec_name
            if spec_col not in data.columns:
                # Try to find it among columns
                for col in data.columns:
                    if col == spec_name:
                        spec_col = col
                        break
            
            if spec_col in data.columns:
                spec_data = data[spec_col].dropna()
                
                if not spec_data.empty:
                    st.markdown(f"**Detailed Analysis: {spec_name}**")
                    
                    # Basic statistics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Records with Data", len(spec_data))
                    with col2:
                        st.metric("Unique Values", spec_data.nunique())
                    with col3:
                        coverage = (len(spec_data) / len(data)) * 100
                        st.metric("Coverage", f"{coverage:.1f}%")
                    with col4:
                        try:
                            numeric_data = pd.to_numeric(spec_data, errors='coerce').dropna()
                            if not numeric_data.empty:
                                st.metric("Avg Value", f"{numeric_data.mean():.2f}")
                        except:
                            st.metric("Data Type", "Text")
                    
                    # Value distribution
                    if spec_data.dtype in ['object', 'category'] or spec_data.nunique() < 20:
                        # Categorical analysis
                        st.markdown("**Value Distribution:**")
                        value_counts = spec_data.value_counts().head(15)
                        st.bar_chart(value_counts)
                        
                        # Show value details
                        st.markdown("**Value Details:**")
                        value_details = []
                        for value, count in value_counts.items():
                            pct = (count / len(spec_data)) * 100
                            value_details.append({
                                'Value': str(value),
                                'Count': count,
                                'Percentage': f"{pct:.1f}%"
                            })
                        
                        details_df = pd.DataFrame(value_details)
                        st.dataframe(details_df, use_container_width=True)
                    
                    else:
                        # Numerical analysis
                        try:
                            numeric_data = pd.to_numeric(spec_data, errors='coerce').dropna()
                            if not numeric_data.empty:
                                st.markdown("**Statistical Distribution:**")
                                
                                # Statistical summary
                                stats_col1, stats_col2 = st.columns(2)
                                with stats_col1:
                                    st.metric("Minimum", f"{numeric_data.min():.2f}")
                                    st.metric("Mean", f"{numeric_data.mean():.2f}")
                                    st.metric("Maximum", f"{numeric_data.max():.2f}")
                                with stats_col2:
                                    st.metric("Median", f"{numeric_data.median():.2f}")
                                    st.metric("Std Dev", f"{numeric_data.std():.2f}")
                                    st.metric("Range", f"{numeric_data.max() - numeric_data.min():.2f}")
                                
                                # Distribution chart
                                st.line_chart(numeric_data.value_counts().sort_index())
                        except:
                            # Fallback to value counts
                            value_counts = spec_data.value_counts().head(15)
                            st.bar_chart(value_counts)
                            
        except Exception as e:
            logger.error(f"Error analyzing specification '{spec_name}': {str(e)}")
            st.error(f"Could not analyze specification: {spec_name}")
    
    def _generate_dynamic_analysis_report(self):
        """Generate comprehensive database analysis with dynamic specification mapping"""
        try:
            logger.info("Generating dynamic analysis report with database-driven specifications")
            engine = get_engine_testdb()
            
            st.markdown("#### 📈 Dynamic Equipment Database Overview")
            
            # ========== DATABASE STATISTICS ==========
            # Basic statistics with optimized queries
            total_query = text(f"SELECT COUNT(*) as total FROM [dbo].[{self.table_name}]")
            total_result = pd.read_sql(total_query, engine)
            total_equipment = total_result['total'].iloc[0]
            
            # Detailed metrics in single query for performance
            metrics_query = text(f"""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(DISTINCT CustomerName) as unique_customers,
                    COUNT(DISTINCT EquipmentType) as unique_types,
                    COUNT(DISTINCT Manufacturer) as unique_manufacturers,
                    COUNT(DISTINCT ParentProjectID) as unique_projects
                FROM [dbo].[{self.table_name}]
                WHERE CustomerName IS NOT NULL
            """)
            metrics_result = pd.read_sql(metrics_query, engine)
            
            if not metrics_result.empty:
                row = metrics_result.iloc[0]
                overview_html = create_equipment_metrics_html(
                    row['total_records'], row['unique_customers'], 
                    row['unique_types'], row['unique_manufacturers']
                )
                st.markdown(overview_html, unsafe_allow_html=True)
            
            # ========== DYNAMIC SPECIFICATION ANALYSIS ==========
            st.markdown("**Dynamic Specification Analysis (Database-Driven):**")
            
            # Analyze specification usage across all equipment types
            dynamic_spec_query = text(f"""
                SELECT 
                    EquipmentType,
                    COUNT(*) as total_records,
                    {', '.join([f"COUNT(CASE WHEN Specifications{i} IS NOT NULL THEN 1 END) as spec{i}_count" for i in range(1, 51)])}
                FROM [dbo].[{self.table_name}]
                WHERE EquipmentType IS NOT NULL
                GROUP BY EquipmentType
                ORDER BY total_records DESC
            """)
            
            dynamic_spec_df = pd.read_sql(dynamic_spec_query, engine)
            
            if not dynamic_spec_df.empty:
                st.markdown("**Specification Usage by Equipment Type (Database-Driven Labels):**")
                
                # Calculate total specification coverage by type
                coverage_by_type = []
                for _, row in dynamic_spec_df.iterrows():
                    eq_type = row['EquipmentType']
                    total_records = row['total_records']
                    
                    # Calculate average coverage across all specs
                    spec_counts = [row[f'spec{i}_count'] for i in range(1, 51)]
                    total_spec_cells = total_records * 50
                    filled_spec_cells = sum(spec_counts)
                    coverage_pct = (filled_spec_cells / total_spec_cells) * 100 if total_spec_cells > 0 else 0
                    
                    # Count how many specifications have any data
                    specs_with_data = sum(1 for count in spec_counts if count > 0)
                    
                    coverage_by_type.append({
                        'Equipment Type': eq_type,
                        'Total Records': total_records,
                        'Specs with Data': f"{specs_with_data}/50",
                        'Avg Coverage %': f"{coverage_pct:.1f}%",
                        'Most Used Specs': specs_with_data
                    })
                
                coverage_df = pd.DataFrame(coverage_by_type)
                coverage_df = coverage_df.sort_values('Most Used Specs', ascending=False)
                st.dataframe(coverage_df, use_container_width=True)
                
                # Chart specification usage by type
                if len(coverage_by_type) > 0:
                    chart_data = {}
                    for item in coverage_by_type[:10]:  # Top 10 equipment types
                        chart_data[item['Equipment Type']] = item['Most Used Specs']
                    
                    if chart_data:
                        st.bar_chart(chart_data)
                        st.caption("Number of specifications with data by equipment type (top 10)")
            
            # ========== EQUIPMENT TYPE ANALYSIS ==========
            st.markdown("**Equipment Type Distribution with Dynamic Specification Trends:**")
            type_query = text(f"""
                SELECT 
                    EquipmentType, 
                    COUNT(*) as count,
                    COUNT(DISTINCT CustomerName) as customers,
                    COUNT(DISTINCT Manufacturer) as manufacturers,
                    AVG(CASE WHEN Specifications1 IS NOT NULL THEN 1.0 ELSE 0.0 END) * 100 as spec_coverage_sample
                FROM [dbo].[{self.table_name}] 
                WHERE EquipmentType IS NOT NULL 
                GROUP BY EquipmentType 
                ORDER BY count DESC
            """)
            type_df = pd.read_sql(type_query, engine)
            
            if not type_df.empty:
                # Equipment type distribution chart
                st.bar_chart(type_df.set_index('EquipmentType')['count'])
                
                # Show detailed breakdown with specification coverage
                st.markdown("**Equipment Type Details with Dynamic Specification Coverage:**")
                type_df['Spec Coverage %'] = type_df['spec_coverage_sample'].round(1).astype(str) + '%'
                display_df = type_df[['EquipmentType', 'count', 'customers', 'manufacturers', 'Spec Coverage %']]
                display_df.columns = ['Equipment Type', 'Count', 'Customers', 'Manufacturers', 'Sample Spec Coverage']
                st.dataframe(display_df, use_container_width=True)
            
            # ========== CUSTOMER & MANUFACTURER ANALYSIS ==========
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Top Customers Analysis:**")
                customer_query = text(f"""
                    SELECT TOP 15 
                        CustomerName, 
                        COUNT(*) as equipment_count,
                        COUNT(DISTINCT EquipmentType) as equipment_types,
                        COUNT(DISTINCT Manufacturer) as manufacturers
                    FROM [dbo].[{self.table_name}] 
                    WHERE CustomerName IS NOT NULL 
                    GROUP BY CustomerName 
                    ORDER BY equipment_count DESC
                """)
                customer_df = pd.read_sql(customer_query, engine)
                
                if not customer_df.empty:
                    st.bar_chart(customer_df.set_index('CustomerName')['equipment_count'])
                    st.dataframe(customer_df, use_container_width=True)
            
            with col2:
                st.markdown("**Manufacturer Analysis:**")
                mfg_query = text(f"""
                    SELECT TOP 15 
                        Manufacturer, 
                        COUNT(*) as equipment_count,
                        COUNT(DISTINCT CustomerName) as customers,
                        COUNT(DISTINCT EquipmentType) as equipment_types
                    FROM [dbo].[{self.table_name}] 
                    WHERE Manufacturer IS NOT NULL 
                    GROUP BY Manufacturer 
                    ORDER BY equipment_count DESC
                """)
                mfg_df = pd.read_sql(mfg_query, engine)
                
                if not mfg_df.empty:
                    st.bar_chart(mfg_df.set_index('Manufacturer')['equipment_count'])
                    st.dataframe(mfg_df, use_container_width=True)
            
            logger.info("Dynamic analysis report generated successfully")
            
        except Exception as e:
            logger.error(f"Dynamic analysis report failed: {str(e)}")
            st.error(f"Dynamic analysis report failed: {str(e)}")

    # ========== BACKWARD COMPATIBILITY METHODS ==========
    def _get_specification_labels(self, equipment_type: str) -> dict:
        """Backward compatibility wrapper"""
        return self._get_specification_labels_from_db(equipment_type)
    
    def _apply_specification_labels_to_all_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Backward compatibility wrapper"""
        return self._apply_dynamic_specification_labels_to_mixed_data(df)
    
    def _apply_specification_labels(self, df: pd.DataFrame, equipment_type: str) -> pd.DataFrame:
        """Backward compatibility wrapper"""
        return self._apply_dynamic_specification_labels(df, equipment_type)
    
    def _analyze_specifications_data(self, data: pd.DataFrame, equipment_type: str):
        """Backward compatibility wrapper"""
        return self._analyze_dynamic_specifications(data, equipment_type)
    
    def _analyze_equipment_type(self, data: pd.DataFrame, equipment_type: str):
        """Backward compatibility wrapper"""
        return self._analyze_equipment_type_dynamic(data, equipment_type)
    
    def _analyze_equipment_data(self, data: pd.DataFrame):
        """Backward compatibility wrapper"""
        return self._analyze_equipment_data_dynamic(data)
    
    def _generate_enhanced_analysis_report(self):
        """Backward compatibility wrapper"""
        return self._generate_dynamic_analysis_report()
    
    # ========== HELPER METHODS ==========
    def _analyze_results(self, results: pd.DataFrame, equipment_type: str = None):
        """Enhanced results analysis with dynamic specification data"""
        if equipment_type:
            self._analyze_equipment_type_dynamic(results, equipment_type)
        else:
            self._analyze_equipment_data_dynamic(results)
