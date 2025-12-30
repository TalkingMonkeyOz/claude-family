# Project Management Domain - Data Gateway Overview

**Database Schema**: `claude`
**Analysis Date**: 2025-12-04
**Purpose**: Design specification for Data Gateway workflow tools

---

## Introduction

This documentation provides a comprehensive analysis of the Project Management (PM) domain tables and workflow specifications. The PM domain manages projects, programs, phases, tasks, and ideas within the `claude` schema.

**Scope**: This analysis covers:
- 5 core tables (PROGRAMS, PROJECTS, PHASES, PM_TASKS, IDEAS)
- 5 workflow tools for data gateway operations
- Business rules and state machines
- Data quality issues and performance recommendations

---

## Table of Contents

1. [PM_GATEWAY_Table_Analysis.md](PM_GATEWAY_Table_Analysis.md)
   - Detailed schema analysis for each table
   - Valid values, required fields, business rules
   - Relationships and constraints

2. [PM_GATEWAY_Workflows.md](PM_GATEWAY_Workflows.md)
   - Workflow tool specifications (5 tools)
   - Business rules summary
   - Recommended database and application validations

3. [PM_GATEWAY_Design_Quality.md](PM_GATEWAY_Design_Quality.md)
   - Entity Relationship Diagram (ERD)
   - Workflow state machines (project, phase, task, idea)
   - Sample workflow scenarios
   - Data quality issues found
   - Performance recommendations
   - Testing checklist
   - Next steps

---

## Document Navigation

This document is split into 4 parts for easier navigation:

| File | Purpose | Audience |
|------|---------|----------|
| **PM_GATEWAY_Overview.md** (this file) | Navigation and introduction | All |
| **PM_GATEWAY_Table_Analysis.md** | Schema details, validation rules | Database architects, developers |
| **PM_GATEWAY_Workflows.md** | Tool specs, business rules, validations | Workflow designers, backend devs |
| **PM_GATEWAY_Design_Quality.md** | Quality, performance, testing | QA, architects, performance engineers |

---

## Key Findings Summary

### Data Issues
- ✗ Inconsistent status casing ('active' vs 'ACTIVE')
- ✗ Inconsistent priority scales (1-4, 6-10, NULL values)
- ✗ Missing foreign key constraints
- ✗ Missing unique constraints on codes

### Recommendations
- ✓ Standardize to 1-5 priority scale across all tables
- ✓ Enforce UPPER_CASE for all status values
- ✓ Add FK and unique constraints
- ✓ Add default values and NOT NULL constraints
- ✓ Implement workflow tool layer for validation

---

## Quick Stats

- **Tables**: 5 (PROGRAMS, PROJECTS, PHASES, PM_TASKS, IDEAS)
- **Workflow Tools**: 5 (`create_project`, `update_project_status`, `add_phase`, `convert_idea_to_task`, `convert_idea_to_phase`)
- **Relationships**: Program → Project → Phase → Task (hierarchical)
- **Key Business Flows**: Project creation, phase management, idea conversion, status transitions

---

## Related Documents

- **Original Full Analysis**: `PM_DOMAIN_DATA_GATEWAY_ANALYSIS.md` (archived)
- **Family Rules**: `40-Procedures/Family Rules.md`
- **Data Gateway Pattern**: `20-Domains/Data_Gateway_Pattern.md`

---

**Analysis Complete**: 2025-12-04
**Database**: PostgreSQL `ai_company_foundation.claude`
**Analyst**: Claude (Sonnet 4.5)

---

**Version**: 2.0
**Created**: 2025-12-04
**Updated**: 2025-12-26
**Location**: docs/PM_GATEWAY_Overview.md
