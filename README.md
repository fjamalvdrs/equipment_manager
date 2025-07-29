# Van Dyk Equipment Manager

A scalable Streamlit application for centralized equipment management, rapid search, and data-driven insights at Van Dyk Recycling Solutions. Designed for modular growth, with direct SQL Server connectivity, Excel-like editing, and optional network visualization.

---

## **Table of Contents**

* [Overview](#overview)
* [Features](#features)
* [Architecture](#architecture)
* [Getting Started](#getting-started)
* [Configuration](#configuration)
* [Usage](#usage)
* [File Structure](#file-structure)
* [Deployment](#deployment)
* [Advanced Usage](#advanced-usage)
* [Troubleshooting](#troubleshooting)
* [Contributing](#contributing)
* [License](#license)

---

## **Overview**

Van Dyk Equipment Manager is a modular Streamlit platform for managing, visualizing, and auditing equipment records, with full SQL Server integration and smart Excel import/export. Designed for data engineers and operations teams handling thousands of equipment records across projects.

---

## **Features**

* **Equipment CRUD:** Add, edit, and delete records with validation and audit trail.
* **Excel-like Table UI:** Inline editing, batch import/export, duplicate detection.
* **Advanced Search:** Multi-field, fuzzy, and serial-based lookup.
* **Network Visualization:** Optional graph view of equipment relationships.
* **SQL Server Integration:** Supports both TestDB and PowerApps databases.
* **Audit Trail:** History logging for all changes.
* **Modular Architecture:** Plug-and-play modules (management, search, visualization).
* **Flexible Configuration:** Session state, sidebar tools, custom environment support.
* **Secure Secrets:** Encrypted credential handling for cloud and on-premise use.

---

## **Architecture**

* **Frontend:** Streamlit with session state and custom JS/CSS.
* **Backend:** Python, SQLAlchemy, Pandas.
* **DB:** Azure SQL Server (`testDB`, `PowerAppsDatabase`).
* **Modularity:** All features in isolated modules for scalability and testing.

---

## **Getting Started**

### **Prerequisites**

* Python 3.8 or newer
* Access to Van Dyk SQL Server (contact admin for credentials)
* (Optional) Excel 2016+ for advanced import/export

### **Installation**

```sh
git clone https://github.com/YOUR_ORG/equipment_manager.git
cd equipment_manager
pip install -r requirements.txt
```

### **Configuration**

For local use, edit `db_utils.py` or set environment variables:

```env
DB_SERVER=your_db_server
DB_USER=your_username
DB_PASSWORD=your_password
```

For **Streamlit Cloud**, use the **Secrets Manager** (recommended):

```toml
# Streamlit Cloud secrets.toml
DB_SERVER = "your_server"
DB_USER = "your_user"
DB_PASSWORD = "your_password"
```

### **Running the App**

```sh
streamlit run appv1.py
```

---

## **Usage**

* Launch the app in your browser (default: [http://localhost:8501](http://localhost:8501))
* Use sidebar tabs to:

  * Manage equipment (CRUD)
  * Search records (filter, export, audit)
  * Visualize equipment network (optional)
* Test DB connection via sidebar utility
* Import/export via Excel using UI tools

---

## **File Structure**

```
equipment_manager/
├── appv1.py                # Main Streamlit entrypoint
├── equipment_manager.py    # Equipment CRUD module
├── search_equipment.py     # Search/lookup logic
├── network_visualization.py# (Optional) Network visualization
├── db_utils.py             # SQL Server utilities & engine
├── validation.py           # Data validation helpers
├── shared_config.py        # Global config/session helpers
├── requirements.txt        # Python dependencies
├── lib/                    # JS/CSS (optional, for graphs)
├── logs/                   # App logs (auto-generated)
├── old_versions/           # Archives/unused
```

---

## **Deployment**

### **Local/On-Prem**

* Ensure all dependencies in `requirements.txt` are installed.
* Use `streamlit run appv1.py`
* Configure firewall for network use (`--server.address=0.0.0.0`).

### **Streamlit Cloud**

* Push code to GitHub.
* Deploy via [streamlit.io/cloud](https://streamlit.io/cloud).
* Configure secrets for DB credentials in Advanced Settings.

### **Production/Advanced**

* Clean unused modules.
* (Optional) Use Docker or reverse proxy for HTTPS and scalability.
* Set up secure log management and backup.

---

## **Advanced Usage**

* **Excel Imports:** Use advanced Excel features (see requirements.txt for optional packages like `openpyxl`, `xlrd`).
* **Sidebar Utilities:** DB connection test, session reset.
* **Custom Config:** Edit `shared_config.py` or inject via secrets/environment.

---

## **Troubleshooting**

| Issue                   | Fix/Tip                                                 |
| ----------------------- | ------------------------------------------------------- |
| App not starting        | Check Python version, all deps installed                |
| DB connection fails     | Check secrets, environment variables, SQL Server access |
| Module import errors    | Ensure all .py files are present in the app directory   |
| Excel import errors     | Install optional Excel packages, check file formats     |
| Cloud deployment issues | Ensure requirements.txt and secrets.toml are correct    |

---

## **Contributing**

* No Changes Thanks

---

## **License**

MIT License

---

**Questions?**
Contact: Ajith Srikanth

---

Let me know if you want a one-liner project badge section, GIF demo, or explicit CI/CD instructions included.
