# Van Dyk Equipment Manager

## Overview
 A modular Streamlit application for managing equipment, searching records, and visualizing equipment networks. Includes Excel-like interfaces and database integration.

## Features

## Getting Started

### Prerequisites

### Installation
1. Clone or download this repository.
2. Install dependencies:
   ```
pip install -r requirements.txt
   ```

### Running the App
Run the main application:
```
streamlit run appv1.py
```

### File Structure

## Deployment

## Notes

## License
MIT

# Van Dyk Equipment Manager

## Overview
A modular Streamlit application for managing equipment, searching records, and visualizing equipment networks. Includes Excel-like interfaces and database integration.

## Features
- Equipment add/edit with smart Excel-like UI
- Search and analysis tools
- Network visualization (optional)
- Modular code structure
- Database connectivity (SQL Server)
- Audit trail and history tracking
- Advanced Excel import/export
- Flexible configuration and session management

## Getting Started

### Prerequisites
- Python 3.8+
- SQL Server database (TestDB and PowerApps)
- All module files in the same directory

### Installation
1. Clone or download this repository.
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

### Running the App
Run the main application:
```
streamlit run appv1.py
```

### File Structure
- `appv1.py` - Main entry point
- `equipment_manager.py` - Equipment management module
- `search_equipment.py` - Search module
- `network_visualization.py` - Visualization module
- `shared_config.py` - Shared config/utilities
- `db_utils.py` - Database utilities
- `validation.py` - Data validation
- `requirements.txt` - Python dependencies
- `lib/` - JS/CSS for visualization (optional)
- `logs/` - Application logs
- `old_versions/` - Archived/unused files

## Deployment
- Remove unused files for a clean deployment
- Ensure all dependencies are installed
- Optionally, use Docker or cloud deployment for production

## Advanced Usage
- For advanced Excel features, install optional packages listed in `requirements.txt`
- Use the sidebar to test database connections and reset session state
- Use tabs for equipment management, search, and visualization

## Troubleshooting
- Ensure all module files are present in the same directory
- Check database connection settings in `db_utils.py`
- Review logs in `logs/app.log` for errors

## License
MIT
