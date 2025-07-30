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
from datetime import datetime
from sqlalchemy import text

from shared_config import (
    Config, get_user_identity, auto_populate_field,
    get_specification_columns, find_equipment_table_name
)
from db_utils import get_engine_testdb, fetch_frequent_values

# --- SQL column order from your schema
SQL_COLUMN_ORDER = [
    'CustomerID', 'CustomerName', 'CustomerLocation', 'ActiveStatus', 'SortSystemPosition',
    'SerialNumber', 'OtherOrPreviousPosition', 'CustomerPositionNo', 'YearManufactured', 'SalesDateWarrantyStartDate',
    'InstallDate', 'Manufacturer', 'ManufacturerProjectID', 'ParentProjectID', 'EquipmentType',
    'FunctionalType', 'FunctionalPosition', 'ManufacturerModelDescription', 'Model',
    *[f'Specifications{i}' for i in range(1, 51)],
    'Notes', 'EquipmentKey', 'RecordHistory',
    'RowCounter', 'MachineInfoID', 'UploadsPendingID', 'HashedSerialNumber'
]
FULL_COLUMN_ORDER = ['Status'] + SQL_COLUMN_ORDER

class EquipmentManager:
    def __init__(self):
        self.config = Config()
        if 'equipment_table_name_override' not in st.session_state:
            st.session_state.equipment_table_name_override = None

    def render(self):
        st.title("📝 Equipment Data Manager")
        st.markdown("**Smart equipment data management with auto-fill and Excel-like editing**")
        steps_completed = 0
        if st.session_state.get('fixed_fields_set'):
            steps_completed += 1
        if st.session_state.get('selected_equipment_type'):
            steps_completed += 1
        st.progress(steps_completed / 2)
        st.caption(f"Setup Progress: {steps_completed}/2 steps completed")

        if not st.session_state.get('fixed_fields_set'):
            self._render_fixed_fields_section()
        else:
            st.success("✅ Step 1 Complete: Common information saved")
            with st.expander("📋 Review Common Information", expanded=False):
                for field in self.config.FIXED_FIELDS:
                    value = st.session_state.get(field, '')
                    if value:
                        st.write(f"**{field}:** {value}")
            if not st.session_state.get('selected_equipment_type'):
                self._render_equipment_type_selection()
            else:
                st.success(f"✅ Step 2 Complete: Equipment type - {st.session_state['selected_equipment_type']}")
                st.markdown("---")
                self._render_equipment_data_section()

    def _render_fixed_fields_section(self):
        st.markdown("### 📋 Step 1: Enter Common Information")
        st.info("🔮 **Smart Auto-Fill:** Enter any field below to automatically fill related information!")
        col1, col2, col3 = st.columns(3)
        with col1:
            customer_id = st.text_input("Customer ID", value=st.session_state.get('CustomerID', ''), key='eq_customer_id')
            st.caption("Enter customer ID to auto-fill customer details")
            if customer_id != st.session_state.get('CustomerID', '') and customer_id.strip():
                auto_filled = auto_populate_field('CustomerID', customer_id)
                if auto_filled:
                    st.success(f"✅ Auto-filled: {', '.join(f'{k}: {v}' for k, v in auto_filled.items())}")
            st.session_state['CustomerID'] = customer_id
        with col2:
            customer_name = st.text_input("Customer Name", value=st.session_state.get('CustomerName', ''), key='eq_customer_name')
            st.caption("Enter customer name to auto-fill customer details")
            if customer_name != st.session_state.get('CustomerName', '') and customer_name.strip():
                auto_filled = auto_populate_field('CustomerName', customer_name)
                if auto_filled:
                    st.success(f"✅ Auto-filled: {', '.join(f'{k}: {v}' for k, v in auto_filled.items())}")
            st.session_state['CustomerName'] = customer_name
        with col3:
            st.session_state['CustomerLocation'] = st.text_input(
                "Customer Location", value=st.session_state.get('CustomerLocation', ''), key='eq_customer_location'
            )
            st.caption("Auto-filled from database or enter manually")
        st.markdown("**Project Information:**")
        col1, col2 = st.columns(2)
        with col1:
            project_id = st.text_input("Project ID", value=st.session_state.get('ParentProjectID', ''), key='eq_project_id')
            st.caption("Enter project ID to auto-fill project details")
            if project_id != st.session_state.get('ParentProjectID', '') and project_id.strip():
                auto_filled = auto_populate_field('ParentProjectID', project_id)
                if auto_filled:
                    st.success(f"✅ Auto-filled: {', '.join(f'{k}: {v}' for k, v in auto_filled.items())}")
            st.session_state['ParentProjectID'] = project_id
        with col2:
            st.session_state['Manufacturer'] = st.text_input(
                "Manufacturer", value=st.session_state.get('Manufacturer', ''), key='eq_manufacturer'
            )
            st.caption("Auto-filled from database or enter manually")
        col1, col2 = st.columns(2)
        with col1:
            st.session_state['ManufacturerProjectID'] = st.text_input(
                "Manufacturer Project ID", value=st.session_state.get('ManufacturerProjectID', ''), key='eq_mfg_project'
            )
        with col2:
            st.session_state['ActiveStatus'] = st.text_input(
                "Active Status", value=st.session_state.get('ActiveStatus', ''), key='eq_active_status'
            )
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
        spec_labels = get_specification_columns()
        st.success(f"📋 **Specification fields loaded:** {list(spec_labels.values())}")

        with st.expander("🔍 Manual Search Options", expanded=False):
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
        col1, col2 = st.columns([10, 1])
        with col2:
            if st.button("🔄", key="refresh_data", help="Refresh data from database"):
                st.rerun()
        if st.session_state.get('manual_search_triggered'):
            existing_df = self._manual_search_equipment()
            st.session_state['manual_search_triggered'] = False
        else:
            existing_df = self._load_existing_equipment_data()
        self._render_data_grid(existing_df, spec_labels)

    def _manual_search_equipment(self) -> pd.DataFrame:
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
        try:
            table_name = st.session_state.get('equipment_table_name_override')
            if table_name:
                return table_name
            return find_equipment_table_name() or 'EquipmentDB'
        except Exception:
            return 'EquipmentDB'

    def _load_existing_equipment_data(self) -> pd.DataFrame:
        try:
            engine = get_engine_testdb()
            table_name = self._get_equipment_table_name()
            if not table_name:
                st.error("❌ Could not find equipment table")
                return pd.DataFrame()
            sql_cols = ', '.join(f'[{col}]' for col in SQL_COLUMN_ORDER)
            query = text(f"SELECT {sql_cols} FROM [dbo].[{table_name}]")
            existing_df = pd.read_sql(query, engine)
            return existing_df
        except Exception as e:
            st.error(f"Failed to load existing data: {str(e)}")
            return pd.DataFrame()

    def _render_data_grid(self, existing_df: pd.DataFrame, spec_labels: dict):
        st.markdown("### 📊 Equipment Data Grid")
        grid_df = self._build_complete_grid(existing_df, spec_labels)
        if grid_df.empty:
            st.warning("⚠️ No data to display")
            return
        column_config = self._build_column_config(spec_labels)
        edited_df = st.data_editor(
            grid_df,
            column_config=column_config,
            num_rows="dynamic",
            use_container_width=True,
            height=600,
            key="equipment_data_editor"
        )
        if st.button("💾 Save All Data to Database", type="primary", key="save_equipment_data"):
            self._save_to_database(edited_df)

    def _build_complete_grid(self, existing_df: pd.DataFrame, spec_labels: dict) -> pd.DataFrame:
        all_rows = []
        if not existing_df.empty:
            for idx, row in existing_df.iterrows():
                grid_row = {'Status': f'🔄#{idx+1}'}
                for col in SQL_COLUMN_ORDER:
                    grid_row[col] = row.get(col, '') if col in row else ''
                all_rows.append(grid_row)
        for i in range(10 if existing_df.empty else 5):
            grid_row = {'Status': f'➕{i+1}'}
            for col in SQL_COLUMN_ORDER:
                if col in self.config.FIXED_FIELDS:
                    grid_row[col] = st.session_state.get(col, '')
                elif col == 'EquipmentType':
                    grid_row[col] = st.session_state.get('selected_equipment_type', '')
                else:
                    grid_row[col] = ''
            all_rows.append(grid_row)
        df = pd.DataFrame(all_rows)
        ordered_cols = [col for col in FULL_COLUMN_ORDER if col in df.columns] + [col for col in df.columns if col not in FULL_COLUMN_ORDER]
        return df[ordered_cols]

    def _build_column_config(self, spec_labels: dict) -> dict:
        column_config = {}
        column_config['Status'] = st.column_config.TextColumn('Status', disabled=True, width=80)
        for col in SQL_COLUMN_ORDER:
            column_config[col] = st.column_config.TextColumn(col)
        return column_config

    def _save_to_database(self, edited_df: pd.DataFrame):
        table_name = self._get_equipment_table_name()
        engine = get_engine_testdb()
        success_count = 0
        errors = []
        for idx, row in edited_df.iterrows():
            try:
                if not any(str(row.get(col, '')).strip() for col in edited_df.columns if col != 'Status'):
                    continue
                record = {}
                for col in SQL_COLUMN_ORDER:
                    if col in self.config.FIXED_FIELDS:
                        record[col] = st.session_state.get(col, '')
                    else:
                        val = row.get(col, '')
                        record[col] = str(val) if pd.notna(val) and str(val).strip() != '' else None
                if 'RecordHistory' in record:
                    existing_history = str(row.get('RecordHistory', '')).strip()
                    user_identity = get_user_identity()
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    edit_info = f"[{timestamp}] Edited by: {user_identity}"
                    record['RecordHistory'] = (existing_history + '\n' + edit_info) if existing_history else edit_info
                self._direct_database_save(engine, table_name, record)
                success_count += 1
            except Exception as e:
                errors.append(f"Row {idx+1}: {str(e)}")
                logging.error(f"Save row {idx} failed: {str(e)}")
        if success_count > 0:
            st.success(f"🎉 Successfully saved {success_count} records!")
        if errors:
            st.error(f"❌ {len(errors)} errors occurred:")
            for error in errors[:3]:
                st.write(f"• {error}")
            if len(errors) > 3:
                st.write(f"... and {len(errors)-3} more errors")
