# Document Management Gap Report

## Comparison to Tier-1 Freight Forwarding ERPs

| Feature | Smart Freight NTT | Tier-1 ERP (e.g., CargoWise) | Gap Status |
| :--- | :--- | :--- | :--- |
| **Manual Document Upload** | ✅ Supported | ✅ Supported | Feature Parity |
| **Version History** | ✅ Supported | ✅ Supported | Feature Parity |
| **Document Search** | ✅ Supported | ✅ Supported | Feature Parity |
| **Tenant Isolation** | ✅ Supported | ✅ Supported | Feature Parity |
| **Security Validation** | ✅ Supported | ✅ Supported | Feature Parity |
| **File Preview** | ❌ Download Only | ✅ In-App Preview | Minor UX Gap |
| **Automated OCR** | ❌ None | ✅ AI Extraction | Capability Gap |
| **Email Ingestion** | ❌ Manual Only | ✅ Direct SMTP | Capability Gap |
| **AP/Vendor Integration** | ❌ Missing UI | ✅ Integrated | Capability Gap |
| **Document Expiry Alerts** | ❌ DB Only | ✅ Active Alerts | Capability Gap |
| **Storage Abstraction** | ❌ Local filesystem | ✅ S3 / Azure Blob | Architecture Gap |

## Remediation Path
1. **S3 Abstraction:** Move `get_storage_path` logic to an interface that supports `boto3`.
2. **AP UI Integration:** Expose the document capabilities to the Finance module.
3. **Email Hooks:** Expand `managers/email_manager.py` to route inbound attachments into `document_manager.py`.
