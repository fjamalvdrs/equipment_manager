# ========== PAGE CONFIG MUST BE FIRST - BEFORE ALL IMPORTS ==========
import streamlit as st
st.set_page_config(layout="wide", page_title="Van Dyk Equipment Manager", page_icon="⚙️")

# ========== IMPORTS ==========
import os
import logging
from datetime import datetime

# Import our custom modules
try:
    from equipment_manager import EquipmentManager
    from search_equipment import SearchEquipment  
    from network_visualization import NetworkVisualization
    from shared_config import Config, initialize_session_state, test_database_connections
except ImportError as e:
    st.error(f"❌ **Module Import Error:** {str(e)}")
    st.info("💡 **Solution:** Make sure all module files are in the same directory as app.py")
    st.stop()

def setup_logging():
    """Setup application logging"""
    os.makedirs('logs', exist_ok=True)
    logging.basicConfig(
        filename='logs/app.log',
        level=logging.INFO,
        format='%(asctime)s %(levelname)s:%(message)s',
        filemode='a'
    )

def render_sidebar():
    """Render clean navigation sidebar"""
    with st.sidebar:
        # ========== SYSTEM HEADER ==========
        st.markdown("# ⚙️ Van Dyk Equipment")
        st.markdown("**Management System**")
        st.markdown("---")
        
        # ========== NAVIGATION ==========
        st.markdown("### 📋 Navigation")
        
        page_options = [
            ("📝 Equipment Manager", "Add, edit, and manage equipment data with Excel-like interface"),
            ("🔍 Search Equipment", "Advanced search and data retrieval with dynamic filtering"),
            ("🌐 Network Visualization", "Interactive relationship visualization and network graphs")
        ]
        
        # Navigation selection
        selected_page = st.radio(
            "Select Page:",
            options=[option[0] for option in page_options],
            key="page_selection",
            help="Choose which module to use"
        )
        
        # Show description for selected page
        for page_name, description in page_options:
            if selected_page == page_name:
                st.caption(f"📄 **{description}**")
                break
        
        st.markdown("---")
        
        # ========== USER LOGIN ==========
        st.markdown("### 👤 User Login")
        username = st.text_input(
            "Enter your name:", 
            value=st.session_state.get("username", ""), 
            key="username",
            placeholder="Required for audit trail",
            help="Your name will be recorded with all equipment changes"
        )
        
        if username.strip():
            st.success(f"✅ Welcome, **{username.strip()}**!")
        else:
            st.warning("⚠️ Please enter your name to continue")
        
        st.caption(f"🕒 Session: {datetime.now().strftime('%H:%M %Y-%m-%d')}")
        
        st.markdown("---")
        
        # ========== DATABASE CONNECTION TESTING ==========
        st.markdown("### 🔧 System Status")
        
        if st.button("🔍 Test Database Connections", key='test_db_connections', use_container_width=True):
            with st.spinner("Testing connections..."):
                results = test_database_connections()
                
                if results.get('testdb'):
                    st.success("✅ TestDB Connected")
                else:
                    st.error("❌ TestDB Failed")
                
                if results.get('powerapps'):
                    st.success("✅ PowerApps Connected")
                else:
                    st.error("❌ PowerApps Failed")
                
                # Test table access
                try:
                    from shared_config import find_equipment_table_name
                    table_name = find_equipment_table_name()
                    if table_name:
                        st.success(f"✅ Equipment Table: {table_name}")
                    else:
                        st.error("❌ No Equipment Table Found")
                except Exception as e:
                    st.error(f"❌ Table Test Failed: {str(e)}")
        
        # ========== SESSION MANAGEMENT ==========
        st.markdown("---")
        if st.button("🔄 Reset Session", key='reset_session', use_container_width=True):
            for key in list(st.session_state.keys()):
                if key != 'page_selection':  # Keep page selection
                    del st.session_state[key]
            st.success("✅ Session reset")
            st.rerun()
        
        st.caption("🔄 Reset clears all cached data and session state")

def main():
    """Main application entry point"""
    try:
        setup_logging()
        initialize_session_state()
        
        # ========== FULL-WIDTH CSS - BEFORE EVERYTHING ==========
        st.markdown("""
            <style>
            /* ========== GLOBAL FULL-WIDTH LAYOUT ========== */
            .block-container {
                padding-left: 1rem !important;
                padding-right: 1rem !important;
                padding-top: 1rem !important;
                padding-bottom: 1rem !important;
                max-width: 98vw !important;
                width: 98vw !important;
            }
            .main .block-container {
                max-width: 98vw !important;
                width: 98vw !important;
            }
            
            /* ========== FORCE ST.COLUMNS TO FULL WIDTH ========== */
            .stColumns {
                width: 100% !important;
                max-width: 100vw !important;
            }
            .stColumns > div {
                width: 100% !important;
                flex: 1 !important;
            }
            .stColumns [data-testid="column"] {
                width: 100% !important;
                flex: 1 !important;
                min-width: 0 !important;
            }
            
            /* ========== DATAFRAME FULL WIDTH ========== */
            .stDataFrame {
                width: 100% !important;
                max-width: 96vw !important;
            }
            .stDataFrame > div {
                width: 100% !important;
                max-width: 96vw !important;
                overflow-x: auto !important;
            }
            .stDataFrame table {
                width: 100% !important;
                table-layout: auto !important;
                min-width: 100% !important;
            }
            .stDataFrame th {
                min-width: 120px !important;
                padding: 12px 16px !important;
                white-space: nowrap !important;
                font-weight: 600 !important;
            }
            .stDataFrame td {
                min-width: 120px !important;
                padding: 10px 16px !important;
                white-space: nowrap !important;
            }
            
            /* ========== BUTTON FULL WIDTH ========== */
            .stButton > button {
                width: 100% !important;
                min-width: 100% !important;
                padding: 0.5rem 1rem !important;
                min-height: 2.5rem !important;
            }
            
            /* ========== METRICS STYLING ========== */
            .equipment-metrics {
                display: flex !important;
                justify-content: space-around !important;
                align-items: center !important;
                padding: 1rem 0 !important;
                background: rgba(255, 255, 255, 0.05) !important;
                border-radius: 8px !important;
                margin: 1rem 0 !important;
                width: 100% !important;
                flex-wrap: wrap !important;
            }
            .equipment-metric-item {
                text-align: center !important;
                padding: 0.5rem 1rem !important;
                min-width: 120px !important;
                flex: 1 !important;
            }
            .equipment-metric-value {
                font-size: 2rem !important;
                font-weight: bold !important;
                color: #00ff00 !important;
                display: block !important;
                line-height: 1.2 !important;
            }
            .equipment-metric-label {
                font-size: 0.9rem !important;
                color: #888 !important;
                display: block !important;
                margin-top: 0.25rem !important;
            }
            .equipment-header {
                background: linear-gradient(90deg, rgba(0,255,0,0.1) 0%, rgba(0,255,0,0.05) 100%) !important;
                border-left: 4px solid #00ff00 !important;
                padding: 1rem 1.5rem !important;
                margin: 1.5rem 0 1rem 0 !important;
                border-radius: 8px !important;
                width: 100% !important;
            }
            .equipment-header h3 {
                margin: 0 !important;
                color: #ffffff !important;
                font-size: 1.5rem !important;
            }
            
            /* ========== DARK MODE COMPATIBILITY ========== */
            [data-theme="dark"] .equipment-metrics {
                background: rgba(255, 255, 255, 0.08) !important;
            }
            [data-theme="dark"] .equipment-header {
                background: linear-gradient(90deg, rgba(0,255,0,0.15) 0%, rgba(0,255,0,0.08) 100%) !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        # ========== RENDER SIDEBAR FIRST ==========
        render_sidebar()
        
        # ========== ENFORCE LOGIN ==========
        if not st.session_state.get("username", "").strip():
            st.warning("⚠️ Please enter your name in the sidebar to begin using the system.")
            st.stop()
        
        # ========== MAIN CONTENT BASED ON SIDEBAR SELECTION ==========
        selected_page = st.session_state.get("page_selection", "📝 Equipment Manager")
        
        # Page header
        st.markdown(f"# {selected_page}")
        
        # Render selected page content
        if selected_page == "📝 Equipment Manager":
            st.markdown("**Add, edit, and manage equipment data with Excel-like interface and smart features**")
            try:
                equipment_manager = EquipmentManager()
                equipment_manager.render()
            except Exception as e:
                st.error(f"❌ Equipment Manager Error: {str(e)}")
                logging.error(f"Equipment Manager failed: {str(e)}")
                
        elif selected_page == "🔍 Search Equipment":
            st.markdown("**Advanced search and data retrieval with dynamic filtering capabilities**")
            try:
                search_equipment = SearchEquipment()
                search_equipment.render()
            except Exception as e:
                st.error(f"❌ Search Equipment Error: {str(e)}")
                logging.error(f"Search Equipment failed: {str(e)}")
                
        elif selected_page == "🌐 Network Visualization":
            st.markdown("**Interactive visualization of equipment relationships and network connections**")
            try:
                network_viz = NetworkVisualization()
                network_viz.render()
            except Exception as e:
                st.error(f"❌ Network Visualization Error: {str(e)}")
                logging.error(f"Network Visualization failed: {str(e)}")
        
        # ========== FOOTER ==========
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("*Van Dyk Equipment Management System v5.0 - Professional Edition*")
        
    except Exception as e:
        st.error(f"❌ **Critical Application Error:** {str(e)}")
        st.info("💡 **Troubleshooting:** Check that all module files exist and database connections are working")
        logging.critical(f"Application crashed: {str(e)}")

if __name__ == "__main__":
    main()
