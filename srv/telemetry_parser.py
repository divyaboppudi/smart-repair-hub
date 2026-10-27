import json
import pandas as pd
import requests  # Used to connect to our enterprise generative AI endpoint
from pydantic import BaseModel, Field, ValidationError
from typing import List, Dict, Any
from db_writer import RepairDatabaseWriter  # Our database connector

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
# PHASE 2: PROCESSING & AI INFERENCE LAYER
# ==========================================
class TelemetryParserEngine:
    def __init__(self):
        self.validated_records: List[Dict[str, Any]] = []
        self.rejected_records: List[Dict[str, Any]] = []
        self.db_writer = RepairDatabaseWriter()

    def call_generative_ai_engine(self, unstructured_text: str) -> Dict[str, Any]:
        """
        Connects to a Generative AI endpoint to parse unstructured car text logs 
        and translate them into clean, structured data records.
        """
        # Architectural Framework: This prompt forces the LLM to output pure JSON data
        system_prompt = (
            "You are an AI Diagnostics Engine for an autonomous vehicle fleet. "
            "Analyze the unstructured error message and extract information strictly in this JSON format: "
            '{"component_group": "LIDAR"|"RADAR"|"CAMERA"|"COMPUTE", '
            '"error_code": "SHORT_CODE", "sensor_id": "ID", "reading_value": 0.0, "unit": "Unit"}'
        )

        # Simulation/Fallback Loop: Runs natively without requiring a paid API key
        # In a production BTP space, this targets the SAP Generative AI Hub URL endpoint
        try:
            # Simulated response payload matching enterprise LLM text transformations
            if "lens blurry" in unstructured_text.lower():
                return {
                    "component_group": "CAMERA",
                    "error_code": "BLURRY_LENS_CRITICAL",
                    "sensor_id": "CAM_FRONT_WIDE",
                    "reading_value": 94.2,
                    "unit": "Percentage"
                }
            elif "laser tracking failed" in unstructured_text.lower():
                return {
                    "component_group": "LIDAR",
                    "error_code": "LDR_ROTATION_FAIL",
                    "sensor_id": "LDR_ROOF_CENTER",
                    "reading_value": 12.0,
                    "unit": "RPM"
                }
            
            # This is where your live enterprise REST API POST connection sits:
            # response = requests.post("https://sap-ai-hub.com", json={...})
            # return json.loads(response.json()['choices'][0]['message']['content'])
            
            return {
                "component_group": "COMPUTE",
                "error_code": "UNKNOWN_SYSTEM_ALERT",
                "sensor_id": "UNKNOWN_MODULE",
                "reading_value": 0.0,
                "unit": "None"
            }
        except Exception as e:
            print(f"[AI Gateway Exception] Connection failed: {str(e)}")
            return {}

    def process_raw_batch(self, raw_logs: List[Dict[str, Any]]) -> None:
        """
        Loops through incoming logs. If a log is unstructured text, it routes it to the AI.
        If it is pre-structured JSON, it validates it via Pydantic.
        """
        for index, log_packet in enumerate(raw_logs):
            try:
                # 1. Check if the log payload is an unstructured text dump message
                if log_packet.get("type") == "UNSTRUCTURED_TEXT":
                    print(f"\n[AI Inference Activity] Processing raw car diagnostic text log via LLM Gateway...")
                    ai_extracted_data = self.call_generative_ai_engine(log_packet["payload"])
                    
                    # Merge the AI's diagnostic extraction output with the vehicle metadata identification
                    full_log = {
                        "vin": log_packet["vin"],
                        "timestamp": log_packet["timestamp"],
                        "component_group": ai_extracted_data["component_group"],
                        "error_code": ai_extracted_data["error_code"],
                        "sensor_data": {
                            "sensor_id": ai_extracted_data["sensor_id"],
                            "reading_value": ai_extracted_data["reading_value"],
                            "unit": ai_extracted_data["unit"]
                        }
                    }
                else:
                    # Otherwise, read it as standard pre-structured data row
                    full_log = json.loads(log_packet["payload"])

                # 2. Run Pydantic strict structure schema verification check
                validated_model = TelemetryLogEntry(**full_log)
                flat_record = validated_model.model_dump()
                
                # Flatten the data structure for relational database storage operations
                flat_record['sensor_id'] = validated_model.sensor_data.sensor_id
                flat_record['reading_value'] = validated_model.sensor_data.reading_value
                flat_record['unit'] = validated_model.sensor_data.unit
                del flat_record['sensor_data']
                
                # 3. Apply Triage Criticality Score Engine Logic
                if flat_record['component_group'] in ['LIDAR', 'COMPUTE', 'CAMERA'] and flat_record['reading_value'] > 85.0:
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
                    "original_payload": str(log_packet)
                })

        # 4. Automatically save all AI-parsed and verified records into the SAP schema table
        if self.validated_records:
            records_saved = self.db_writer.insert_triage_records(self.validated_records)
            print(f"[SAP BTP Integration Success] Saved {records_saved} records directly into database storage.")

    def generate_recruiter_analytics_summary(self) -> str:
        if not self.validated_records:
            return "No valid telemetry data available to calculate fleet metrics."
            
        df = pd.DataFrame(self.validated_records)
        sorted_df = df.sort_values(by="criticality_score", ascending=False)
        
        summary_string = "\n=== BTP AUTOMATED AI FLEET REPAIR ANALYSIS ENGINE ===\n"
        summary_df = sorted_df[['vin', 'component_group', 'error_code', 'reading_value', 'triage_action']]
        summary_string += summary_df.to_string(index=False)
        summary_string += f"\n\n[System Metrics] Successfully Processed: {len(self.validated_records)} logs | Rejected: {len(self.rejected_records)} logs"
        
        return summary_string

# ==========================================
# PHASE 3: SIMULATED INBOUND VEHICLE TRAFFIC
# ==========================================
if __name__ == "__main__":
    # We now pass a diverse batch: 1 pre-structured JSON log, and 1 messy unstructured text text log from a vehicle crash dump
    mixed_telemetry_stream = [
        {
            "type": "STRUCTURED_JSON",
            "vin": "FLEETROBOTAXI0001",
            "timestamp": "2026-10-24T19:20:00Z",
            "payload": '{"vin": "FLEETROBOTAXI0001", "timestamp": "2026-10-24T19:20:00Z", "component_group": "LIDAR", "error_code": "ERR_LDR_OBSTRUCTION", "sensor_data": {"sensor_id": "LDR_FRONT_TOP", "reading_value": 42.1, "unit": "Celsius"}}'
        },
        {
            "type": "UNSTRUCTURED_TEXT",
            "vin": "FLEETROBOTAXI0003",
            "timestamp": "2026-10-24T19:25:12Z",
            "payload": "CRITICAL EXCEPTION ALERT: Front camera lens blurry due to heavy dust accumulation at intersection. Visibility degraded below safety operational limits. Threat index high."
        }
    ]
    
    engine = TelemetryParserEngine()
    engine.process_raw_batch(mixed_telemetry_stream)
    print(engine.generate_recruiter_analytics_summary())
