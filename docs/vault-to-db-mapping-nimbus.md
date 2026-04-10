# Vault-to-DB Mapping: Nimbus Projects

Parent: [vault-to-db-mapping.md](vault-to-db-mapping.md)

Covers nimbus-mui, nimbus-import, and nimbus-user-loader.

## nimbus-mui

### DB Knowledge (15 entries, confidence 95-100)

| Title | Type |
|-------|------|
| Cross-Database Comparison Module Pattern | pattern |
| Nimbus Entity Creation Dependency Order | procedure |
| Monash Nimbus Test Environment Access | fact |
| nimbus-knowledge MCP server location | gotcha |
| T2WDemo Azure SQL Server Connection Details | fact |
| Nimbus API Authentication - Correct Endpoint and Response Format | pattern |
| Nimbus OData Pagination Pattern | pattern |
| Nimbus ScheduleShift Location Chain | gotcha |
| Nimbus OData Filter Limitations - Deleted Field Silently Ignored | gotcha |
| ScheduleShiftAgreement duplicate prevention | gotcha |
| Standalone Tauri apps cannot use MCP servers at runtime | gotcha |
| Tauri File Export - Use Dialog and FS Plugins Not Browser APIs | gotcha |
| Nimbus CoreApi vs ODataApi Endpoint Differences | pattern |
| Nimbus OData Adhoc Fields Retrieval Pattern | pattern |
| Nimbus PartNumber Extraction SQL Pattern | pattern |

### Domain Concepts (7)

Nimbus Authentication, Nimbus Parallel Run Pipeline, Nimbus Time2Work, UserSDK, Nimbus REST API, Monash Nimbus Environment, Nimbus OData API

### OData Entities (15 cataloged)

Shift, SnapshotScheduleShiftActivity, UserLoginAttempt, UserNoteHistory, UserSkillApproval, SnapshotScheduleShiftAgreement, UserAssociation, UserLoginFailedAttempt, AwardRuleDetailActivityType, Agreement, User, ScheduleShiftOffer, Schedule, ScheduleShiftAgreement, UserSDK Hours child

### Workfiles (10 active)

Components: dashboards (1), parallel-run (5), usersdk-discovery (1), session-handoff (2+)

### Vault: No folder. All knowledge in DB. Domain docs in 20-Domains/APIs/ (9 files).

---

## nimbus-import

### DB Knowledge (15 entries, confidence 90-100)

Shares most entries with nimbus-mui. Additional unique entries: Nimbus REST API returns XML by default, Nimbus REST Authentication Headers, Nimbus REST CRUD Pattern, Nimbus Activity Type Prefixes, Nimbus Agreement Comma Parsing.

### Domain Concepts: None project-specific. Shares nimbus domain concepts.
### Workfiles: None.
### Vault: Folder exists but empty. All knowledge in DB.

---

## nimbus-user-loader

### DB Knowledge (15 entries, confidence 100)

Mix of Nimbus API patterns and WinForms gotchas: Azure SQL connection, DataGridView ScrollBars Reset Bug, Control Initialization Order, Roslyn MCP mandate, Nimbus UserSDK Batch Import, ClosedXML Bulk Insert, Hidden WinForms Controls layout.

### Domain Concepts: None project-specific. Shares nimbus domain concepts.
### Workfiles: None.
### Vault: No folder. WinForms docs in 20-Domains/WinForms/ (4 files).

---

**Version**: 1.0
**Created**: 2026-04-11
**Updated**: 2026-04-11
**Location**: docs/vault-to-db-mapping-nimbus.md
