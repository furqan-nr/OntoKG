# Fault-injection ablation (error-detection, not component removal)

Valid graph: `data/demo_psx.ttl` (SHACL-conformant). Each row injects one realistic data error into a fresh copy; we report whether SHACL detects it. **Detected 8/8.**

| Injected fault | SHACL result |
|---|---|
| wrong metric value datatype (decimal->string) | detected (non-conformant) |
| company missing hasCompanyName | detected (non-conformant) |
| market observation missing isObservationOf | detected (non-conformant) |
| malformed announcement date (date->string) | detected (non-conformant) |
| observation missing hasMetricName | detected (non-conformant) |
| fundamental linked to wrong reporting-period class | detected (non-conformant) |
| duplicate hasMetricValue (maxCount 1) | detected (non-conformant) |
| evidence item missing hasEvidenceSource | detected (non-conformant) |
