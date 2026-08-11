# PHASE 21 — SUPABASE SCHEMA GAP ANALYSIS

This document details the schema mismatches between the expected application schema and the actual production database (Supabase).

| TABLE | COLUMN | EXPECTED | ACTUAL | MIGRATION REQUIRED |
| :--- | :--- | :--- | :--- | :--- |
| `bookings` | `tenant_id` | `TEXT` | `NULL` (Missing) | `ALTER TABLE bookings ADD COLUMN tenant_id TEXT DEFAULT 'default';` |
| `quotations` | `tenant_id` | `TEXT` | `NULL` (Missing) | `ALTER TABLE quotations ADD COLUMN tenant_id TEXT DEFAULT 'default';` |
| `bills_of_lading` | (All columns) | Table exists | Table missing | `CREATE TABLE bills_of_lading (...);` |
| `bl_containers` | (All columns) | Table exists | Table missing | `CREATE TABLE bl_containers (...);` |
| `booking_revisions` | (All columns) | Table exists | Table missing | `CREATE TABLE booking_revisions (...);` |

> [!IMPORTANT]
> In accordance with Phase 25 instructions, no modifications have been automatically made to the production Supabase database.
