---
projects:
- ato-tax-agent
tags:
- database
- postgresql
- schema
synced: false
---

# ATO Tax Agent - Database Schema

**Schema**: `tax_calculator` | **Database**: `ai_company_foundation` | **Tables**: 13

---

## Entity Relationships

```
users ──1:N──▶ tax_returns ──1:N──┬──▶ tax_return_data
                                  ├──▶ tax_return_sections
                                  ├──▶ tax_return_calculations
                                  └──▶ audit_log
```

---

## Core Tables

| Table | Rows | Purpose |
|-------|------|---------|
| `users` | 16 | Login accounts (email, password_hash) |
| `tax_returns` | 9 | Return sessions (user_id, tax_year, status) |
| `tax_return_data` | 22 | Form values as JSONB (section_code, field_data) |
| `tax_return_sections` | 5 | Section completion (status, timestamps) |
| `tax_return_calculations` | 1 | Cached totals (income, deductions, tax) |
| `audit_log` | 0 | Change tracking |
| `password_reset_tokens` | 0 | Auth tokens |

---

## Reference Tables (ATO Content)

| Table | Purpose | Queried By |
|-------|---------|------------|
| `section_analysis_master` | Section metadata | wizard.py |
| `section_data_requirements` | Field definitions | wizard.py |
| `tax_return_binary_gates` | YES/NO gates | wizard.py |
| `tax_return_cross_references` | Section dependencies | wizard.py |
| `tax_return_multi_entry_sections` | Multi-entry config | wizard.py |
| `tax_return_instructional_content` | RAG content (12 rows) | AI Assistant |

---

## Key Design Decisions

1. **JSONB for field data** - Flexible, no schema changes for new fields
2. **Reference tables empty** - Wizard falls back to JSON files
3. **Multi-user ready** - All data isolated by user_id
4. **Multi-year ready** - tax_year column in tax_returns

---

## Foreign Keys

| Child | Column | → Parent |
|-------|--------|----------|
| tax_returns | user_id | users |
| tax_return_data | return_id | tax_returns |
| tax_return_sections | return_id | tax_returns |
| tax_return_calculations | return_id | tax_returns |
| section_data_requirements | section_code | section_analysis_master |

---

**Version**: 1.0
**Created**: 2026-01-04
**Location**: knowledge-vault/10-Projects/ato-tax-agent/
