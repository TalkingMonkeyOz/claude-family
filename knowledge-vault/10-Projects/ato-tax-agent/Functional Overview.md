---
projects:
- ato-tax-agent
tags:
- overview
- architecture
- user-journey
synced: false
---

# ATO Tax Agent - Functional Overview

**Purpose**: Help Australians complete their individual tax returns accurately
**Domain**: talkingape.com.au
**Status**: Implementation Phase

---

## What It Does

| Feature | Description |
|---------|-------------|
| **Guided Wizard** | Step-by-step tax return completion |
| **Discovery Flow** | Yes/No questions to identify relevant sections |
| **Calculations** | Automatic tax calculations using ATO rules |
| **PDF Generation** | Download completed return as PDF |
| **AI Assistant** | Context-aware help (planned) |

---

## User Journey

```
Landing Page → Register/Login → Dashboard
      ↓
Discovery (yes/no questions)
      ↓
Wizard (section by section)
      ↓
Summary (review + calculations)
      ↓
Download PDF → Lodge via myGov
```

---

## Two-Layer System

| Layer | Purpose | AI Used? |
|-------|---------|----------|
| **Layer 1** | Guided process, pure ATO rules | No |
| **Layer 2** | AI assistant, deduction prompts | Yes (Claude) |

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Next.js 16, React, MUI |
| Backend | FastAPI (Python) |
| Database | PostgreSQL (tax_calculator schema) |
| Auth | JWT tokens |
| Storage | IndexedDB (client), PostgreSQL (server) |

---

## Database Tables (13 total)

**Core**: users, tax_returns, tax_return_data, tax_return_sections, tax_return_calculations, audit_log, password_reset_tokens

**Reference**: section_analysis_master, section_data_requirements, tax_return_binary_gates, tax_return_cross_references, tax_return_multi_entry_sections, tax_return_instructional_content

See [[Database Schema]] for full details.

---

**Version**: 1.0
**Created**: 2026-01-04
**Location**: knowledge-vault/10-Projects/ato-tax-agent/
