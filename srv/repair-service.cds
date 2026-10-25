using { sap.smartrepair as my } from '../db/schema';

service RepairService {
    @readonly entity TelemetryLogs as projection on my.TelemetryLogs;
}
