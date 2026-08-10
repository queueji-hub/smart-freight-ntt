# Freight Forwarding Capability Matrix

| Module | Sub-Module | Capability Status | Notes |
| :--- | :--- | :--- | :--- |
| **Document Management** | Core Repository | 🟢 Full | Upload, download, hash, isolation. |
| | Pre-Shipment | 🟢 Full | Booking confirmation attachments. |
| | Operations | 🟢 Full | Job, Container, B/L attachments. |
| | Finance | 🟡 Partial | UI missing in AP workflows. |
| | Post-Shipment | 🟢 Full | Status tracking, version control. |
| | Automation | 🔴 Missing | OCR, Email parser lacking. |
| | Storage | 🟡 Partial | Requires S3 implementation for scale. |
| **System Security** | Tenant Context | 🟢 Full | Hard-boundary DB isolation implemented. |
| | File Security | 🟢 Full | 50MB cap, executable block, sanitization. |
| | RBAC | 🟡 Partial | Coarse roles built; granular doc-level ACLs pending. |
