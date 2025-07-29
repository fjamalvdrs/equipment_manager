"""
Network Visualization Module
===========================

Interactive network visualization of equipment relationships including:
- Customer-Project-Equipment relationships
- Circular network layouts
- Interactive exploration tools
- Network statistics and analysis

Version: 5.0 - Modular Architecture
"""

import streamlit as st
import pandas as pd
import logging
import math
from typing import Dict, List, Optional, Tuple, Any

# Import shared utilities
from shared_config import Config, find_equipment_table_name
from db_utils import get_engine_testdb, get_engine_powerapps

# Visualization imports (optional)
try:
    import networkx as nx
    from pyvis.network import Network
    import streamlit.components.v1 as components
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False

class NetworkVisualization:
    """Network visualization and analysis class"""
    
    def __init__(self):
        self.config = Config()
    
    def render(self):
        """Main render method for network visualization"""
        st.title("🌐 Equipment Network Visualization")
        st.markdown("**Interactive visualization of equipment relationships and connections**")
        
        if not VISUALIZATION_AVAILABLE:
            self._render_installation_guide()
            return
        
        # Visualization controls
        self._render_controls()
        
        # Main visualization
        self._render_network_visualization()
    
    def _render_installation_guide(self):
        """Render installation guide for missing libraries"""
        st.error("❌ **Visualization libraries not installed**")
        
        st.markdown("### 🔧 Installation Required")
        st.markdown("**To enable network visualization, install these packages:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.code("""
# Install required packages
pip install networkx pyvis
            """)
        
        with col2:
            st.markdown("**After installation:**")
            st.markdown("1. Restart the Streamlit application")
            st.markdown("2. Come back to this tab")
            st.markdown("3. Enjoy interactive network visualization!")
        
        st.markdown("### 🎯 What You'll Get")
        st.info("**Interactive Features:** Drag nodes, zoom, explore relationships")
        st.info("**Circular Layout:** Customers around perimeter, projects and equipment in center")
        st.info("**Live Data:** Real-time visualization of your equipment database")
        
        # Show preview of features
        with st.expander("📸 Preview of Network Visualization Features", expanded=False):
            st.markdown("**🌐 Interactive Network Features:**")
            st.markdown("- **🟢 Green nodes** = Customers (outer circle)")
            st.markdown("- **🔵 Blue nodes** = Projects (middle)")
            st.markdown("- **🟣 Purple nodes** = Equipment/Machines (inner)")
            st.markdown("- **🟠 Orange nodes** = Manufacturers (center)")
            
            st.markdown("**🖱️ Interaction Capabilities:**")
            st.markdown("- Drag nodes to rearrange")
            st.markdown("- Zoom in/out with mouse wheel")
            st.markdown("- Click nodes to highlight connections")
            st.markdown("- Navigation controls built-in")
    
    def _render_controls(self):
        """Render visualization controls and options"""
        st.markdown("### ⚙️ Visualization Controls")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Refresh Network Data", key="refresh_network"):
                if hasattr(st, 'cache_data'):
                    st.cache_data.clear()
                st.success("✅ Data refreshed")
                st.rerun()
            st.caption("Reload latest data from PowerApps database")
        
        with col2:
            layout_style = st.selectbox(
                "🎨 Network Layout:",
                ["Circular", "Force-Directed", "Hierarchical"],
                key="network_layout"
            )
            st.caption("Choose how nodes are arranged in the visualization")
        
        with col3:
            max_machines = st.slider(
                "🔧 Max Equipment to Show:",
                min_value=10, max_value=100, value=50,
                key="max_machines_slider"
            )
            st.caption("Limit equipment shown for better performance")
    
    def _render_network_visualization(self):
        """Render the main network visualization"""
        st.markdown("### 🌐 Equipment Relationship Network")
        
        # Load data
        with st.spinner("🔍 Loading network data from PowerApps database..."):
            network_data = self._load_network_data()
        
        if not network_data:
            st.error("❌ Failed to load network data")
            st.info("💡 **Troubleshooting:** Check PowerApps database connection and ensure equipmentDB table exists")
            return
        
        customer_df, project_df, machine_df, manufacturer_df = network_data
        
        # Show data summary
        self._display_data_summary(customer_df, project_df, machine_df, manufacturer_df)
        
        # Create and display network
        with st.spinner("🎨 Creating interactive network visualization..."):
            network_html = self._create_network(customer_df, project_df, machine_df, manufacturer_df)
        
        if network_html:
            st.markdown("#### 🎯 Interactive Network")
            st.info("💡 **Instructions:** Drag nodes • Zoom with mouse wheel • Click to highlight connections")
            
            # Display the network
            components.html(network_html, height=800, scrolling=False)
            
            # Show network statistics
            self._display_network_statistics(customer_df, project_df, machine_df, manufacturer_df)
        else:
            st.error("❌ Failed to create network visualization")
        
        # Display legend and help
        self._display_legend_and_help()
    
    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def _load_network_data(_self) -> Optional[Tuple[pd.DataFrame, ...]]:
        """Load data for network visualization from PowerApps database"""
        try:
            engine_powerapps = get_engine_powerapps()
            
            # Load equipment data from PowerApps database
            equipment_df = pd.read_sql("SELECT * FROM [dbo].[equipmentDB]", engine_powerapps)
            
            if equipment_df.empty:
                st.warning("⚠️ No equipment data found in PowerApps database")
                return None
            
            st.info(f"📊 **Loaded {len(equipment_df)} equipment records from PowerApps database**")
            
            # Extract entity dataframes
            customers_df = _self._extract_customers(equipment_df)
            projects_df = _self._extract_projects(equipment_df)
            machines_df = equipment_df.copy()  # All equipment records
            manufacturers_df = _self._extract_manufacturers(equipment_df)
            
            return customers_df, projects_df, machines_df, manufacturers_df
            
        except Exception as e:
            st.error(f"Failed to load network data: {str(e)}")
            logging.error(f"Network data loading failed: {str(e)}")
            return None
    
    def _extract_customers(self, equipment_df: pd.DataFrame) -> pd.DataFrame:
        """Extract unique customers from equipment data"""
        if 'CustomerID' in equipment_df.columns and 'CustomerName' in equipment_df.columns:
            return equipment_df[['CustomerID', 'CustomerName']].drop_duplicates()
        return pd.DataFrame()
    
    def _extract_projects(self, equipment_df: pd.DataFrame) -> pd.DataFrame:
        """Extract unique projects from equipment data"""
        if 'ParentProjectID' in equipment_df.columns and 'CustomerID' in equipment_df.columns:
            return equipment_df[['ParentProjectID', 'CustomerID']].drop_duplicates()
        return pd.DataFrame()
    
    def _extract_manufacturers(self, equipment_df: pd.DataFrame) -> pd.DataFrame:
        """Extract unique manufacturers from equipment data"""
        if 'Manufacturer' in equipment_df.columns:
            mfg_df = equipment_df[['Manufacturer']].drop_duplicates()
            if not mfg_df.empty:
                mfg_df = mfg_df.reset_index(drop=True)
                mfg_df['ManufacturerID'] = mfg_df.index + 1
            return mfg_df
        return pd.DataFrame()
    
    def _display_data_summary(self, customer_df: pd.DataFrame, project_df: pd.DataFrame, 
                            machine_df: pd.DataFrame, manufacturer_df: pd.DataFrame):
        """Display summary of loaded network data"""
        with st.expander("📊 Network Data Summary", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("👥 Customers", len(customer_df))
                st.caption("Unique customer organizations")
            
            with col2:
                st.metric("📁 Projects", len(project_df))
                st.caption("Individual projects")
            
            with col3:
                equipment_count = min(len(machine_df), st.session_state.get('max_machines_slider', 50))
                st.metric("⚙️ Equipment", equipment_count)
                st.caption(f"Equipment items (showing {equipment_count})")
            
            with col4:
                st.metric("🏭 Manufacturers", len(manufacturer_df))
                st.caption("Equipment manufacturers")
    
    def _create_network(self, customer_df: pd.DataFrame, project_df: pd.DataFrame, 
                       machine_df: pd.DataFrame, manufacturer_df: pd.DataFrame) -> Optional[str]:
        """Create interactive network visualization"""
        try:
            # Create NetworkX graph
            G = nx.DiGraph()
            
            # Add nodes
            self._add_customer_nodes(G, customer_df)
            self._add_project_nodes(G, project_df)
            self._add_machine_nodes(G, machine_df)
            self._add_manufacturer_nodes(G, manufacturer_df)
            
            # Add relationships
            self._add_relationships(G, customer_df, project_df, machine_df, manufacturer_df)
            
            if len(G.nodes()) == 0:
                st.warning("⚠️ No network nodes created - check data structure")
                return None
            
            # Create PyVis network
            net = self._create_pyvis_network(G)
            
            # Generate HTML
            return net.generate_html()
            
        except Exception as e:
            st.error(f"Network creation failed: {str(e)}")
            logging.error(f"Network creation failed: {str(e)}")
            return None
    
    def _add_customer_nodes(self, G: Any, customer_df: pd.DataFrame):
        """Add customer nodes to the graph"""
        if customer_df.empty:
            return
        
        for _, row in customer_df.iterrows():
            customer_id = str(row.get('CustomerID', ''))
            customer_name = str(row.get('CustomerName', 'Unknown'))
            
            if customer_id and customer_id != 'nan':
                G.add_node(
                    f"C_{customer_id}",
                    label=customer_name[:20],
                    title=f"Customer: {customer_name}",
                    color="lightgreen",
                    size=30,
                    node_type="customer"
                )
    
    def _add_project_nodes(self, G: Any, project_df: pd.DataFrame):
        """Add project nodes to the graph"""
        if project_df.empty:
            return
        
        for _, row in project_df.iterrows():
            project_id = str(row.get('ParentProjectID', ''))
            
            if project_id and project_id != 'nan':
                G.add_node(
                    f"P_{project_id}",
                    label=project_id[:15],
                    title=f"Project: {project_id}",
                    color="lightblue",
                    size=25,
                    node_type="project"
                )
    
    def _add_machine_nodes(self, G: Any, machine_df: pd.DataFrame):
        """Add machine nodes to the graph (limited for performance)"""
        if machine_df.empty:
            return
        
        max_machines = st.session_state.get('max_machines_slider', 50)
        count = 0
        
        for _, row in machine_df.iterrows():
            if count >= max_machines:
                break
            
            serial = str(row.get('SerialNumber', ''))
            equipment_type = str(row.get('EquipmentType', 'Unknown'))
            
            if serial and serial != 'nan':
                G.add_node(
                    f"M_{serial}",
                    label=f"{equipment_type[:8]}\\n{serial[:10]}",
                    title=f"Equipment: {equipment_type} (SN: {serial})",
                    color="plum",
                    size=20,
                    node_type="machine"
                )
                count += 1
    
    def _add_manufacturer_nodes(self, G: Any, manufacturer_df: pd.DataFrame):
        """Add manufacturer nodes to the graph"""
        if manufacturer_df.empty:
            return
        
        for _, row in manufacturer_df.iterrows():
            mfg_id = str(row.get('ManufacturerID', ''))
            manufacturer = str(row.get('Manufacturer', 'Unknown'))
            
            if mfg_id and mfg_id != 'nan':
                G.add_node(
                    f"MF_{mfg_id}",
                    label=manufacturer[:15],
                    title=f"Manufacturer: {manufacturer}",
                    color="orange",
                    size=25,
                    node_type="manufacturer"
                )
    
    def _add_relationships(self, G: Any, customer_df: pd.DataFrame, project_df: pd.DataFrame, 
                          machine_df: pd.DataFrame, manufacturer_df: pd.DataFrame):
        """Add relationship edges to the graph"""
        # Customer -> Project relationships
        for _, row in project_df.iterrows():
            customer_id = str(row.get('CustomerID', ''))
            project_id = str(row.get('ParentProjectID', ''))
            
            if (customer_id and customer_id != 'nan' and 
                project_id and project_id != 'nan' and
                G.has_node(f"C_{customer_id}") and G.has_node(f"P_{project_id}")):
                G.add_edge(f"C_{customer_id}", f"P_{project_id}", 
                          title="Customer → Project", color="green")
        
        # Project -> Machine relationships
        max_machines = st.session_state.get('max_machines_slider', 50)
        count = 0
        
        for _, row in machine_df.iterrows():
            if count >= max_machines:
                break
            
            project_id = str(row.get('ParentProjectID', ''))
            serial = str(row.get('SerialNumber', ''))
            
            if (project_id and project_id != 'nan' and 
                serial and serial != 'nan' and
                G.has_node(f"P_{project_id}") and G.has_node(f"M_{serial}")):
                G.add_edge(f"P_{project_id}", f"M_{serial}", 
                          title="Project → Equipment", color="blue")
                count += 1
        
        # Machine -> Manufacturer relationships
        if not manufacturer_df.empty:
            count = 0
            for _, row in machine_df.iterrows():
                if count >= max_machines:
                    break
                
                serial = str(row.get('SerialNumber', ''))
                manufacturer = str(row.get('Manufacturer', ''))
                
                # Find manufacturer ID
                mfg_row = manufacturer_df[manufacturer_df['Manufacturer'] == manufacturer]
                if not mfg_row.empty:
                    mfg_id = str(mfg_row.iloc[0]['ManufacturerID'])
                    
                    if (serial and serial != 'nan' and 
                        mfg_id and mfg_id != 'nan' and
                        G.has_node(f"M_{serial}") and G.has_node(f"MF_{mfg_id}")):
                        G.add_edge(f"M_{serial}", f"MF_{mfg_id}", 
                                  title="Equipment → Manufacturer", color="orange")
                        count += 1
    
    def _create_pyvis_network(self, G: Any) -> Network:
        """Create PyVis network with circular layout"""
        net = Network(
            height=self.config.NETWORK_HEIGHT,
            width=self.config.NETWORK_WIDTH,
            directed=True,
            bgcolor="#1e1e1e",
            font_color="white"
        )
        
        # Get layout style
        layout_style = st.session_state.get('network_layout', 'Circular')
        
        # Add nodes with positioning
        if layout_style == "Circular":
            self._add_circular_layout(net, G)
        else:
            # Use NetworkX layout for other styles
            net.from_nx(G)
        
        # Configure network options
        self._configure_network_options(net, layout_style)
        
        return net
    
    def _add_circular_layout(self, net: Network, G: Any):
        """Add nodes with circular layout positioning"""
        # Categorize nodes
        customers = [n for n, d in G.nodes(data=True) if d.get('node_type') == 'customer']
        projects = [n for n, d in G.nodes(data=True) if d.get('node_type') == 'project']
        machines = [n for n, d in G.nodes(data=True) if d.get('node_type') == 'machine']
        manufacturers = [n for n, d in G.nodes(data=True) if d.get('node_type') == 'manufacturer']
        
        # Add customers in outer circle
        self._add_circle_nodes(net, G, customers, self.config.CUSTOMER_RADIUS, physics=False)
        
        # Add projects in middle circle
        self._add_circle_nodes(net, G, projects, self.config.PROJECT_RADIUS, physics=True)
        
        # Add machines in inner circle
        self._add_circle_nodes(net, G, machines, self.config.MACHINE_RADIUS, physics=True)
        
        # Add manufacturers in center
        self._add_circle_nodes(net, G, manufacturers, self.config.MANUFACTURER_RADIUS, physics=True)
        
        # Add all edges
        for source, target, edge_data in G.edges(data=True):
            if net.get_node(source) and net.get_node(target):
                net.add_edge(source, target, 
                           title=edge_data.get('title', ''),
                           color=edge_data.get('color', 'gray'),
                           width=2)
    
    def _add_circle_nodes(self, net: Network, G: Any, nodes: List[str], radius: int, physics: bool = True):
        """Add nodes arranged in a circle"""
        if not nodes:
            return
        
        for i, node in enumerate(nodes):
            angle = 2 * math.pi * i / len(nodes) if len(nodes) > 1 else 0
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            
            node_data = G.nodes[node]
            net.add_node(
                node,
                label=node_data.get('label', node),
                title=node_data.get('title', node),
                color=node_data.get('color', 'lightgray'),
                size=node_data.get('size', 20),
                x=x, y=y,
                physics=physics
            )
    
    def _configure_network_options(self, net: Network, layout_style: str):
        """Configure network visualization options"""
        if layout_style == "Circular":
            options = """
            {
              "layout": {"randomSeed": 42},
              "edges": {
                "arrows": {"to": {"enabled": true, "scaleFactor": 1.2}},
                "smooth": {"enabled": true, "type": "continuous"}
              },
              "interaction": {
                "navigationButtons": true,
                "keyboard": true,
                "dragNodes": true,
                "dragView": true,
                "zoomView": true
              },
              "physics": {
                "enabled": true,
                "stabilization": {"iterations": 100}
              },
              "nodes": {
                "font": {"size": 14, "color": "white"},
                "borderWidth": 2,
                "shadow": {"enabled": true}
              }
            }
            """
        elif layout_style == "Force-Directed":
            options = """
            {
              "layout": {"randomSeed": 2},
              "physics": {"enabled": true, "stabilization": {"iterations": 200}},
              "interaction": {"navigationButtons": true, "keyboard": true},
              "nodes": {"font": {"size": 14, "color": "white"}}
            }
            """
        else:  # Hierarchical
            options = """
            {
              "layout": {
                "hierarchical": {
                  "direction": "UD",
                  "sortMethod": "directed"
                }
              },
              "physics": {"enabled": false},
              "interaction": {"navigationButtons": true, "keyboard": true},
              "nodes": {"font": {"size": 14, "color": "white"}}
            }
            """
        
        net.set_options(options)
    
    def _display_network_statistics(self, customer_df: pd.DataFrame, project_df: pd.DataFrame, 
                                  machine_df: pd.DataFrame, manufacturer_df: pd.DataFrame):
        """Display network statistics"""
        with st.expander("📈 Network Statistics", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_nodes = len(customer_df) + len(project_df) + len(machine_df) + len(manufacturer_df)
                st.metric("Total Network Nodes", total_nodes)
            
            with col2:
                # Estimate edges (relationships)
                estimated_edges = len(project_df) + min(len(machine_df), 50) * 2
                st.metric("Estimated Connections", estimated_edges)
            
            with col3:
                if total_nodes > 0:
                    density = estimated_edges / (total_nodes * (total_nodes - 1)) if total_nodes > 1 else 0
                    st.metric("Network Density", f"{density:.3f}")
    
    def _display_legend_and_help(self):
        """Display visualization legend and help"""
        col1, col2 = st.columns(2)
        
        with col1:
            with st.expander("🎨 Network Color Legend", expanded=False):
                st.markdown("**Node Types and Colors:**")
                st.markdown("🟢 **Customers** - Green circles (outer ring)")
                st.markdown("🔵 **Projects** - Blue circles (middle ring)")
                st.markdown("🟣 **Equipment** - Purple circles (inner ring)")
                st.markdown("🟠 **Manufacturers** - Orange circles (center)")
                
                st.markdown("**Connection Types:**")
                st.markdown("➡️ **Green arrows** = Customer to Project")
                st.markdown("➡️ **Blue arrows** = Project to Equipment")
                st.markdown("➡️ **Orange arrows** = Equipment to Manufacturer")
        
        with col2:
            with st.expander("🎮 Interactive Controls", expanded=False):
                st.markdown("**Mouse Controls:**")
                st.markdown("- **Drag nodes** to move them around")
                st.markdown("- **Mouse wheel** to zoom in/out")
                st.markdown("- **Click nodes** to select and highlight")
                st.markdown("- **Right-click** for context menu")
                
                st.markdown("**Navigation:**")
                st.markdown("- **Arrow keys** to pan the view")
                st.markdown("- **+/- keys** for zoom control")
                st.markdown("- **Built-in navigation** buttons in visualization")
