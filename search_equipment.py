"""
Search Equipment Module
======================

Advanced equipment search and data retrieval functionality including:
- Advanced search with multiple criteria
- Export capabilities
- Equipment history viewing
- Data filtering and analysis

Version: 5.0 - Modular Architecture
"""

import streamlit as st
import pandas as pd
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Import shared utilities
from shared_config import (
    Config, get_user_identity, find_equipment_table_name, 
    format_date_columns
)
from db_utils import get_engine_testdb

class SearchEquipment:
    """Equipment search and retrieval class"""
    
    def __init__(self):
        self.config = Config()
    
    def render(self):
        """Main render method for search functionality"""
        st.title("🔍 Equipment Search & Analysis")
        st.markdown("**Advanced search, filtering, and analysis of equipment data**")
        
        # Search interface tabs
        search_tab1, search_tab2, search_tab3 = st.tabs([
            "🔎 Quick Search", 
            "🎯 Advanced Search", 
            "📊 Data Analysis"
        ])
        
        with search_tab1:
            self._render_quick_search()
        
        with search_tab2:
            self._render_advanced_search()
        
        with search_tab3:
            self._render_data_analysis()
    
    def _render_quick_search(self):
        """Render quick search interface"""
        st.markdown("### 🔎 Quick Equipment Search")
        st.info("💡 Search across all equipment fields with a single search term")
        
        # Search input
        col1, col2 = st.columns([3, 1])
        
        with col1:
            search_term = st.text_input(
                "Search for equipment:",
                placeholder="Enter customer name, serial number, equipment type, etc.",
                key='quick_search_term'
            )
            st.caption("Searches across CustomerID, CustomerName, SerialNumber, EquipmentType, and more")
        
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)  # Spacing
            search_clicked = st.button("🔍 Search", type="primary", key="quick_search_btn")
        
        # Perform search
        if search_clicked or (search_term and len(search_term) > 2):
            if search_term.strip():
                results = self._perform_quick_search(search_term)
                self._display_search_results(results, f"Quick search for '{search_term}'")
            else:
                st.info("💡 Enter at least 3 characters to search")
        
        # Show recent searches
        self._show_recent_equipment()
    
    def _render_advanced_search(self):
        """Render advanced search with multiple criteria"""
        st.markdown("### 🎯 Advanced Equipment Search")
        st.info("💡 Search with multiple specific criteria for precise results")
        
        # Search criteria form
        with st.expander("🎛️ Search Criteria", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Customer Information:**")
                customer_id = st.text_input("Customer ID:", key='adv_customer_id')
                customer_name = st.text_input("Customer Name:", key='adv_customer_name')
                customer_location = st.text_input("Customer Location:", key='adv_customer_location')
                
                st.markdown("**Equipment Details:**")
                equipment_type = st.text_input("Equipment Type:", key='adv_equipment_type')
                manufacturer = st.text_input("Manufacturer:", key='adv_manufacturer')
            
            with col2:
                st.markdown("**Project Information:**")
                project_id = st.text_input("Project ID:", key='adv_project_id')
                mfg_project_id = st.text_input("Manufacturer Project ID:", key='adv_mfg_project')
                
                st.markdown("**Technical Details:**")
                serial_number = st.text_input("Serial Number:", key='adv_serial')
                model = st.text_input("Model:", key='adv_model')
                year_manufactured = st.text_input("Year Manufactured:", key='adv_year')
        
        # Search controls
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("🎯 Advanced Search", type="primary", key="advanced_search_btn"):
                criteria = {
                    'CustomerID': customer_id,
                    'CustomerName': customer_name,
                    'CustomerLocation': customer_location,
                    'EquipmentType': equipment_type,
                    'Manufacturer': manufacturer,
                    'ParentProjectID': project_id,
                    'ManufacturerProjectID': mfg_project_id,
                    'SerialNumber': serial_number,
                    'Model': model,
                    'YearManufactured': year_manufactured
                }
                
                # Remove empty criteria
                active_criteria = {k: v for k, v in criteria.items() if v.strip()}
                
                if active_criteria:
                    results = self._perform_advanced_search(active_criteria)
                    self._display_search_results(results, f"Advanced search with {len(active_criteria)} criteria")
                else:
                    st.warning("⚠️ Please enter at least one search criterion")
        
        with col2:
            if st.button("🧹 Clear All", key="clear_advanced_search"):
                st.rerun()
        
        with col3:
            st.caption("Use any combination of criteria above for precise equipment finding")
    
    def _render_data_analysis(self):
        """Render data analysis and statistics"""
        st.markdown("### 📊 Equipment Data Analysis")
        st.info("💡 Overview and statistics of your equipment database")
        
        if st.button("📈 Generate Analysis Report", type="primary", key="generate_analysis"):
            self._generate_analysis_report()
    
    def _perform_quick_search(self, search_term: str) -> pd.DataFrame:
        """Perform quick search across multiple fields"""
        try:
            table_name = find_equipment_table_name()
            if not table_name:
                st.error("❌ Could not find equipment table")
                return pd.DataFrame()
            
            engine = get_engine_testdb()
            
            # Search across common fields
            search_fields = [
                'CustomerID', 'CustomerName', 'CustomerLocation',
                'SerialNumber', 'EquipmentType', 'Manufacturer',
                'ParentProjectID', 'ManufacturerProjectID', 'Model',
                'FunctionalType', 'ManufacturerModelDescription'
            ]
            
            where_clauses = []
            params = []
            
            for field in search_fields:
                where_clauses.append(f"CAST([{field}] AS NVARCHAR(MAX)) LIKE ?")
                params.append(f"%{search_term}%")
            
            query = f"""
                SELECT TOP 100 * FROM [dbo].[{table_name}] 
                WHERE {' OR '.join(where_clauses)}
                ORDER BY CustomerName, SerialNumber
            """
            
            results = pd.read_sql(query, engine, params=tuple(params))
            return format_date_columns(results)
            
        except Exception as e:
            st.error(f"Quick search failed: {str(e)}")
            logging.error(f"Quick search failed: {str(e)}")
            return pd.DataFrame()
    
    def _perform_advanced_search(self, criteria: Dict[str, str]) -> pd.DataFrame:
        """Perform advanced search with multiple criteria"""
        try:
            table_name = find_equipment_table_name()
            if not table_name:
                st.error("❌ Could not find equipment table")
                return pd.DataFrame()
            
            engine = get_engine_testdb()
            
            # Build WHERE clause
            where_clauses = []
            params = []
            
            for field, value in criteria.items():
                if value.strip():
                    where_clauses.append(f"[{field}] LIKE ?")
                    params.append(f"%{value}%")
            
            query = f"""
                SELECT * FROM [dbo].[{table_name}] 
                WHERE {' AND '.join(where_clauses)}
                ORDER BY CustomerName, EquipmentType, SerialNumber
            """
            
            results = pd.read_sql(query, engine, params=tuple(params))
            return format_date_columns(results)
            
        except Exception as e:
            st.error(f"Advanced search failed: {str(e)}")
            logging.error(f"Advanced search failed: {str(e)}")
            return pd.DataFrame()
    
    def _show_recent_equipment(self):
        """Show recently added equipment"""
        st.markdown("### 📅 Recent Equipment")
        
        if st.button("📋 Show Recent Equipment", key="show_recent"):
            try:
                table_name = find_equipment_table_name()
                if not table_name:
                    st.error("❌ Could not find equipment table")
                engine = get_engine_testdb()
                query = f"""
                    SELECT * FROM [dbo].[{table_name}]
                    ORDER BY SerialNumber DESC
                """
                
                recent_df = pd.read_sql(query, engine)
                
 
                if not recent_df.empty:
                    st.success(f"📋 **Recent {len(recent_df)} equipment entries:**")
                    st.dataframe(recent_df, use_container_width=True)
                else:
                    st.info("No recent equipment found")
                    
            except Exception as e:
                st.error(f"Failed to load recent equipment: {str(e)}")
    
    def _display_search_results(self, results: pd.DataFrame, search_description: str):
        """Display search results with analysis"""
        if results.empty:
            st.info(f"🔍 No equipment found for: {search_description}")
            return
        
        st.success(f"✅ **Found {len(results)} equipment records**")
        st.caption(search_description)
        
        # Quick stats
        if len(results) > 0:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                unique_customers = results['CustomerName'].nunique() if 'CustomerName' in results.columns else 0
                st.metric("Customers", unique_customers)
            
            with col2:
                unique_types = results['EquipmentType'].nunique() if 'EquipmentType' in results.columns else 0
                st.metric("Equipment Types", unique_types)
            
            with col3:
                unique_manufacturers = results['Manufacturer'].nunique() if 'Manufacturer' in results.columns else 0
                st.metric("Manufacturers", unique_manufacturers)
            
            with col4:
                unique_projects = results['ParentProjectID'].nunique() if 'ParentProjectID' in results.columns else 0
                st.metric("Projects", unique_projects)
        
        # Display results
        st.dataframe(results, use_container_width=True, height=400)
        
        # Export options
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📥 Export to Excel", key=f"export_excel_{hash(search_description)}"):
                self._export_to_excel(results, search_description)
        
        with col2:
            if st.button("📊 Analyze Results", key=f"analyze_{hash(search_description)}"):
                self._analyze_results(results)
    
    def _export_to_excel(self, results: pd.DataFrame, description: str):
        """Export search results to Excel"""
        try:
            # Create Excel file in memory
            from io import BytesIO
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                results.to_excel(writer, sheet_name='Equipment_Search_Results', index=False)
            
            excel_data = output.getvalue()
            
            # Download button
            filename = f"equipment_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            st.download_button(
                label="💾 Download Excel File",
                data=excel_data,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            st.success(f"✅ Excel file ready for download: {filename}")
            
        except Exception as e:
            st.error(f"Excel export failed: {str(e)}")
    
    def _analyze_results(self, results: pd.DataFrame):
        """Analyze search results"""
        st.markdown("#### 📊 Search Results Analysis")
        
        if 'EquipmentType' in results.columns:
            st.markdown("**Equipment Type Distribution:**")
            type_counts = results['EquipmentType'].value_counts()
            st.bar_chart(type_counts)
        
        if 'Manufacturer' in results.columns:
            st.markdown("**Manufacturer Distribution:**")
            mfg_counts = results['Manufacturer'].value_counts().head(10)
            st.bar_chart(mfg_counts)
        
        if 'YearManufactured' in results.columns:
            st.markdown("**Manufacturing Year Distribution:**")
            year_counts = results['YearManufactured'].value_counts().sort_index()
            st.line_chart(year_counts)
    
    def _generate_analysis_report(self):
        """Generate comprehensive equipment analysis report"""
        try:
            table_name = find_equipment_table_name()
            if not table_name:
                st.error("❌ Could not find equipment table")
                return
            
            engine = get_engine_testdb()
            
            st.markdown("#### 📈 Equipment Database Overview")
            
            # Basic statistics
            total_query = f"SELECT COUNT(*) as total FROM [dbo].[{table_name}]"
            total_result = pd.read_sql(total_query, engine)
            total_equipment = total_result['total'].iloc[0]
            
            st.metric("**Total Equipment Records**", total_equipment)
            
            # Equipment type breakdown
            type_query = f"""
                SELECT EquipmentType, COUNT(*) as count 
                FROM [dbo].[{table_name}] 
                WHERE EquipmentType IS NOT NULL 
                GROUP BY EquipmentType 
                ORDER BY count DESC
            """
            type_df = pd.read_sql(type_query, engine)
            
            if not type_df.empty:
                st.markdown("**Equipment Types:**")
                st.bar_chart(type_df.set_index('EquipmentType')['count'])
            
            # Customer breakdown
            customer_query = f"""
                SELECT CustomerName, COUNT(*) as equipment_count 
                FROM [dbo].[{table_name}] 
                WHERE CustomerName IS NOT NULL 
                GROUP BY CustomerName 
                ORDER BY equipment_count DESC
            """
            customer_df = pd.read_sql(customer_query, engine)
            
            if not customer_df.empty:
                st.markdown("**Top Customers by Equipment Count:**")
                st.dataframe(customer_df.head(10), use_container_width=True)
            
            # Manufacturer breakdown
            mfg_query = f"""
                SELECT Manufacturer, COUNT(*) as equipment_count 
                FROM [dbo].[{table_name}] 
                WHERE Manufacturer IS NOT NULL 
                GROUP BY Manufacturer 
                ORDER BY equipment_count DESC
            """
            mfg_df = pd.read_sql(mfg_query, engine)
            
            if not mfg_df.empty:
                st.markdown("**Equipment by Manufacturer:**")
                st.bar_chart(mfg_df.head(10).set_index('Manufacturer')['equipment_count'])
            
        except Exception as e:
            st.error(f"Analysis report generation failed: {str(e)}")
            logging.error(f"Analysis report failed: {str(e)}")
