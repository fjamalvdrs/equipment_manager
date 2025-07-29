import os
from datetime import datetime
import streamlit as st
st.set_page_config(layout="wide", page_title="Equipment Manager", page_icon="⚙️")
"""
Van Dyk Equipment Manager - Master Application
============================================

Main application that coordinates all modules:
- Equipment Management (Add/Edit)
- Search Equipment 
- Network Visualization

Version: 5.0 - Modular Architecture
"""

import logging

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
    logging.basicConfig(
        filename='logs/app.log',
        level=logging.INFO,
        format='%(asctime)s %(levelname)s:%(message)s',
        filemode='a'
    )

    logging.basicConfig(
        filename='logs/app.log',
        level=logging.INFO,
        format='%(asctime)s %(levelname)s:%(message)s',
        filemode='a'
    )

def render_sidebar():
    """Render sidebar with system information and controls"""
    with st.sidebar:
        st.header("🔧 System Status")
        
        # Database connection testing
        if st.button("🔍 Test All Connections", key='test_all_connections'):
            with st.spinner("Testing database connections..."):
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
                    from equipment_manager import find_equipment_table_name
                    table_name = find_equipment_table_name()
                    if table_name:
                        st.success(f"✅ Equipment Table: {table_name}")
                    else:
                        st.error("❌ No Equipment Table Found")
                except Exception as e:
                    st.error(f"❌ Table Test Failed: {str(e)}")
        
        st.markdown("---")
        
        # Module information
        st.header("📋 Available Modules")
        st.markdown("**🏗️ Equipment Manager**")
        st.caption("Add, edit, and manage equipment data with Excel-like interface")
        
        st.markdown("**🔍 Search Equipment**") 
        st.caption("Advanced search and data retrieval")
        
        st.markdown("**🌐 Network Visualization**")
        st.caption("Interactive relationship visualization")
        
        st.markdown("---")
        
        # User information
        st.header("👤 Session Info")
        st.write(f"**User:** {os.getenv('USERNAME', 'Unknown')}")
        st.write(f"**Session:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        # Session management
        if st.button("🔄 Reset Session", key='reset_session'):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success("✅ Session reset")
            st.rerun()

def main():
    """Main application entry point"""
    try:
        # Setup
        setup_logging()
        initialize_session_state()
        
        # App header
        st.markdown("# ⚙️ Van Dyk Equipment Management System")
        st.markdown("**Complete Equipment Lifecycle Management** - Modular Architecture")
        
        # Quick start guide
        with st.expander("🚀 Quick Start Guide", expanded=False):
            st.markdown("### **Choose Your Task:**")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("#### 📝 Equipment Management")
                st.markdown("- Add new equipment data")
                st.markdown("- Edit existing records") 
                st.markdown("- Excel-like interface")
                st.markdown("- Smart auto-fill features")
            
            with col2:
                st.markdown("#### 🔍 Search Equipment")
                st.markdown("- Find equipment by any detail")
                st.markdown("- Advanced filtering")
                st.markdown("- Export search results")
                st.markdown("- View equipment history")
            
            with col3:
                st.markdown("#### 🌐 Network Visualization")
                st.markdown("- See equipment relationships")
                st.markdown("- Interactive network graphs")
                st.markdown("- Customer-project connections")
                st.markdown("- Equipment flow analysis")
        
        # Render sidebar
        render_sidebar()
        
        # Main content tabs
        tab1, tab2, tab3 = st.tabs([
            "📝 Equipment Manager", 
            "🔍 Search Equipment", 
            "🌐 Network Visualization"
        ])
        
        # Tab 1: Equipment Management
        with tab1:
            st.caption("Add, edit, and manage equipment data with Excel-like interface and smart features")
            
            try:
                # Ensure database connection
                
                equipment_manager = EquipmentManager()
                equipment_manager.render()
            except Exception as e:
                st.error(f"❌ Equipment Manager Error: {str(e)}")
                logging.error(f"Equipment Manager failed: {str(e)}")
        
        # Tab 2: Search Equipment
        with tab2:
            st.caption("Search and retrieve equipment data with advanced filtering capabilities")
            
            try:
                search_equipment = SearchEquipment()
                search_equipment.render()
            except Exception as e:
                st.error(f"❌ Search Equipment Error: {str(e)}")
                logging.error(f"Search Equipment failed: {str(e)}")
        
        # Tab 3: Network Visualization
        with tab3:
            st.caption("Interactive visualization of equipment relationships and network connections")
            
            try:
                network_viz = NetworkVisualization()
                network_viz.render()
            except Exception as e:
                st.error(f"❌ Network Visualization Error: {str(e)}")
                logging.error(f"Network Visualization failed: {str(e)}")
        
        # Footer
        st.markdown("---")
        st.markdown("*Van Dyk Equipment Management System v5.0 - Modular Architecture*")
        
    except Exception as e:
        st.error(f"❌ **Critical Application Error:** {str(e)}")
        st.info("💡 **Troubleshooting:** Check that all module files exist and database connections are working")
        logging.critical(f"Application crashed: {str(e)}")

if __name__ == "__main__":
    main()
