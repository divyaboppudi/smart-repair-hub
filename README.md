# Autonomous Vehicle Telemetry & SAP Smart Repair Hub

A high-performance cloud-native side-by-side extensibility application built using the SAP Cloud Application Programming (CAP) framework for Python. This engine intercepts unstructured real-time hardware error streams from self-driving vehicle networks, validates parsing structures, executes conditional logic data validation arrays, and securely logs telemetry metrics straight into an SAP HANA Cloud schema repository.

## 🛠️ The Architecture
* **Ingestion Guard (Pydantic Layer):** Processes streaming data packets, enforcing strict type-casting validations on incoming variables (VIN constraints, float parameters, hardware groupings) to reject malformed records before reaching persistence tables.
* **Triage Analytics Core (Pandas Layer):** Converts arrays into multi-dimensional internal DataFrames to run quick array-sorting mechanics, prioritizing critical overheated vehicle components right to the top of operator dashboard monitor logs.
* **Database Ledger (SAP CAP & SQL Sync):** Orchestrates transaction commit sequences, writing clean data configurations side-by-side with central core tables while maintaining strict clean-core infrastructure separation rules.

## 💻 Elite Code Insight (Clean Core Sorting & DB Commit Sync)
```python
# Our engine tracks temperature ceilings and flattens nested logs cleanly:
if flat_record['component_group'] in ['LIDAR', 'COMPUTE'] and flat_record['reading_value'] > 85.0:
    flat_record['criticality_score'] = 100
    flat_record['triage_action'] = "GROUND_AND_REPAIR"

# Automated insert sequence maps rows securely using standard SQL pooling:
cursor.execute(insert_query, row_parameters)
connection.commit()
```

## 🚀 How to Execute and Validate Locally
1. Initialize the virtual workspace partition: `source .venv/bin/activate`
2. Install standard dependencies from the target cache ledger: `pip install -r requirements.txt`
3. Deploy structural relational schemas: `cds deploy --to sqlite:db/repair.db`
4. Run the core analytics simulation engine: `python srv/telemetry_parser.py`
