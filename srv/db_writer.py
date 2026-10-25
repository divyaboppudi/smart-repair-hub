import sqlite3
from datetime import datetime

# ==========================================
# ENTERPRISE DATABASE CONNECTOR LAYER
# ==========================================
# This class acts as the data highway. It opens a pipeline to our
# SAP BTP database layer, maps data rows, and securely commits records.

class RepairDatabaseWriter:
    def __init__(self, db_path: str = "db/repair.db"):
        self.db_path = db_path

    def insert_triage_records(self, flat_records: list) -> int:
        """
        Accepts a list of flattened, validated python dictionaries
        and runs a secure SQL transactional batch-insert process.
        """
        if not flat_records:
            return 0

        # 1. Establish transactional line connection to our database engine
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()
        
        inserted_count = 0
        current_time_str = datetime.utcnow().isoformat() + "Z"

        # 2. Construct our SQL Insert statement targeting our SAP Schema definition
        insert_query = """
            INSERT INTO sap_smartrepair_TelemetryLogs (
                ID, createdAt, modifiedAt, vin, componentGroup, errorCode, readingValue, triageAction, criticalityScore
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        try:
            for record in flat_records:
                # Generate standard hex-string surrogate keys to prevent primary key overlap collisions
                unique_row_id = record['vin'] + "-" + str(int(datetime.utcnow().timestamp()))
                
                # Bind our runtime python dictionary key variables cleanly into database row slots
                row_parameters = (
                    unique_row_id,
                    current_time_str,
                    current_time_str,
                    record.get('vin'),
                    record.get('component_group'),
                    record.get('error_code'),
                    record.get('reading_value'),
                    record.get('triage_action'),
                    record.get('criticality_score')
                )
                
                # Execute transactional step parameters
                cursor.execute(insert_query, row_parameters)
                inserted_count += 1
            
            # Commit the safe batch values permanently down to disk storage
            connection.commit()
            
        except sqlite3.Error as database_exception:
            print(f"[Database Critical Rollback Exception]: {database_exception}")
            connection.rollback()
            raise database_exception
            
        finally:
            # Always close connections to prevent physical cloud container memory leak bottlenecks
            connection.close()

        return inserted_count
