import json
import pandas as pd
from pydantic import BaseModel, Field, ValidationError
from typing import List, Dict, Any
from db_writer import RepairDatabaseWriter  # Import our new database connector

# ==========================================
# PHASE 1: DATA MODEL DEFINITIONS (PYDANTIC)
# ==========================================
class SensorPayload(BaseModel):
    sensor_id: str = Field(..., description="Unique hardware identifier for the sensor")
    reading_value: float = Field(..., description="Numeric telemetry value from the module")
    unit: str = Field(..., description="Measurement unit (e.g., Celsius, RPM, Volts)")

class TelemetryLogEntry(BaseModel):
    vin: str = Field(..., min_length=17, max_length=17, description="Standard 17-character Vehicle Identification Number")
    timestamp: str = Field(..., description="ISO 8601 string recording the exact moment of the fault")
    component_group: str = Field(..., description="Hardware bucket: LIDAR, RADAR, CAMERA, or COMPUTE")
    error_code: str = Field(..., description="The system fault signature code")
    sensor_data: SensorPayload = Field(..., description="Nested sub-payload containing raw hardware parameters")

# ==========================================
# PHASE 2: PROCESSING ENGINE LAYER (PANDAS)
# ==========================================
class TelemetryParserEngine:
    def __init__(self):
        self.validated_records: List[Dict[str, Any]] = []
        self.rejected_records: List[Dict[str, Any]] = []
        self.db_writer = RepairDatabaseWriter()  # Instantiate our database connection layer

    def process_raw_batch(self, raw_json_strings: List[str]) -> None:
        for index, raw_string in enumerate(raw_json_strings):
            try:
                parsed_json = json.loads(raw_string)
                validated_model = TelemetryLogEntry(**parsed_json)
                flat_record = validated_model.model_dump()
                
                flat_record['sensor_id'] = validated_model.sensor_data.sensor_id
                flat_record['reading_value'] = validated_model.sensor_data.reading_value
                flat_record['unit'] = validated_model.sensor_data.unit
                del flat_record['sensor_data']
                
                if flat_record['component_group'] in ['LIDAR', 'COMPUTE'] and flat_record['reading_value'] > 85.0:
                    flat_record['criticality_score'] = 100
                    flat_record['triage_action'] = "GROUND_AND_REPAIR"
                elif flat_record['reading_value'] > 65.0:
                    flat_record['criticality_score'] = 50
                    flat_record['triage_action'] = "SCHEDULE_MAINTENANCE"
                else:
                    flat_record['criticality_score'] = 10
                    flat_record['triage_action'] = "MONITOR_LOGS"
                    
                self.validated_records.append(flat_record)
                
            except (json.JSONDecodeError, ValidationError) as validation_error:
                self.rejected_records.append({
                    "raw_index": index,
                    "error_log_trace": str(validation_error),
                    "original_payload": raw_string
                })

        # CRUCIAL INTEGRATION STEP: Automatically save all verified entries down to our SAP Database table rows
        if self.validated_records:
            records_saved = self.db_writer.insert_triage_records(self.validated_records)
            print(f"\n[SAP BTP Integration Success] Saved {records_saved} verified records directly into database storage.")

    def generate_recruiter_analytics_summary(self) -> str:
        if not self.validated_records:
            return "No valid telemetry data available to calculate fleet metrics."
            
        df = pd.DataFrame(self.validated_records)
        sorted_df = df.sort_values(by="criticality_score", ascending=False)
        
        summary_string = "\n=== BTP AUTOMATED FLEET REPAIR ANALYSIS ENGINE ===\n"
        summary_df = sorted_df[['vin', 'component_group', 'error_code', 'reading_value', 'triage_action']]
        summary_string += summary_df.to_string(index=False)
        summary_string += f"\n\n[System Metrics] Successfully Validated: {len(self.validated_records)} logs | Corrupted/Rejected: {len(self.rejected_records)} logs"
        
        return summary_string

# ==========================================
# PHASE 3: VERIFICATION WORKFLOW (LOCAL RUN)
# ==========================================
if __name__ == "__main__":
    mock_fleet_stream = [
        '{"vin": "FLEETROBOTAXI0001", "timestamp": "2026-10-24T19:20:00Z", "component_group": "LIDAR", "error_code": "ERR_LDR_OBSTRUCTION", "sensor_data": {"sensor_id": "LDR_FRONT_TOP", "reading_value": 92.4, "unit": "Celsius"}}',
        '{"vin": "FLEETROBOTAXI0002", "timestamp": "2026-10-24T19:21:05Z", "component_group": "COMPUTE", "error_code": "WARN_CPU_THROTTLING", "sensor_data": {"sensor_id": "MAIN_AI_CORE", "reading_value": 71.2, "unit": "Celsius"}}',
        '{"vin": "BAD_LOG_SAMPLE_INVALID", "timestamp": "MISSING_FIELDS_HERE"}' 
    ]
    
    engine = TelemetryParserEngine()
    engine.process_raw_batch(mock_fleet_stream)
    print(engine.generate_recruiter_analytics_summary())
