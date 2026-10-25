namespace sap.smartrepair;

using { cuid, managed } from '@sap/cds/common';

entity TelemetryLogs : cuid, managed {
    vin             : String(17);
    componentGroup  : String(30);
    errorCode       : String(50);
    readingValue    : Decimal(5, 2);
    triageAction    : String(40);
    criticalityScore: Integer;
}
