---
tags: []
projects: []
---
# Personal Finance System - Documentation Index
## Complete Documentation Package
**Date:** 26 December 2025  
**Status:** Planning & Design Phase (No Implementation Yet)

---

## What This Is

A complete set of **planning documents** for building a comprehensive personal finance system with specialized SMSF tracking. These documents are for **handoff to developers** (human or AI) to implement the system.

**Nothing has been built yet - this is pure documentation.**

---

## Document Inventory

### 1. **prd-personal-finance-system.md** (Strategic PRD)
**Purpose:** High-level product vision and core functions  
**Audience:** Product owner, stakeholders, project planners  
**Contents:**
- What problem we're solving
- 6 major function areas (account aggregation, AI categorization, bills, SMSF, etc.)
- Why this is different from existing tools
- 7 development phases (Foundation → Polish)
- Open questions and decisions needed

**Read this first** to understand the overall vision.

---

### 2. **DATABASE_SCHEMA.md** (Technical Specification)
**Purpose:** Complete PostgreSQL database design  
**Audience:** Database developers, backend engineers  
**Contents:**
- Full schema with all tables (accounts, transactions, SMSF, etc.)
- Indexes for performance
- Relationships and foreign keys
- Views for common queries
- pgvector setup for AI/RAG
- Example data and utility functions

**Use this to create the database.**

---

### 3. **ORM_COMPARISON.md** (Technology Decision Guide)
**Purpose:** Explain Entity Framework Core vs Dapper  
**Audience:** C# developers (especially those new to data access)  
**Contents:**
- What EF Core and Dapper are (simplified explanation)
- Side-by-side code examples
- Performance comparison
- When to use each
- **Recommendation:** Start with EF Core

**Read this if you don't know what EF Core or Dapper are.**

---

### 4. **CDR_OPEN_BANKING.md** (Integration Research)
**Purpose:** Research on automated bank transaction downloads  
**Audience:** Integration developers, product owner  
**Contents:**
- What is CDR (Consumer Data Right) in Australia
- Free vs paid options
- Aggregator comparison (Basiq vs Frollo)
- Cost analysis ($0 manual vs $35/month CDR)
- **Recommendation:** Start with manual CSV import, add CDR later if needed

**Read this to understand how to get bank data.**

---

### 5. **prd-smsf-portfolio-manager.md** (Detailed SMSF PRD - DEPRECATED)
**Purpose:** Original SMSF-only PRD with 13 user stories  
**Audience:** Reference only  
**Status:** âš ï¸ **Superseded by prd-personal-finance-system.md**  
**Contents:**
- Detailed user stories for SMSF-only system
- Full implementation plan
- 24-week timeline

**Don't use this** - it's been replaced by the broader personal finance system. Kept for reference only.

---

## Technology Stack Summary

Based on decisions in the documents:

| Component | Technology | Reason |
|-----------|------------|--------|
| **Database** | PostgreSQL 14+ | You already have it, powerful, pgvector support |
| **Backend** | C# .NET 8 | Your preference, mature ecosystem |
| **Data Access** | Entity Framework Core | Easier to start with (see ORM_COMPARISON.md) |
| **Bank Sync** | Manual CSV (Phase 1) → CDR (Phase 2+) | Start free, add automation later |
| **AI** | Claude (Haiku + Sonnet) via Anthropic API | Categorization, insights, anomaly detection |
| **RAG** | pgvector extension | Learn from user corrections |
| **API** | ASP.NET Core | REST API for Claude to query data |
| **UI** | TBD | Console/WinForms to start, web later |

---

## Implementation Roadmap

### Phase 1: Foundation (4-6 weeks)
**Goal:** Basic account and transaction tracking

**Tasks:**
1. Create PostgreSQL database (use DATABASE_SCHEMA.md)
2. Set up C# project with EF Core
3. Build CSV importer (Westpac format)
4. Create basic models (Account, Transaction, Category)
5. Simple console UI to view data
6. REST API with 3-5 endpoints

**Deliverable:** Can import bank CSV, store in database, query via API

---

### Phase 2: AI Categorization (2-3 weeks)
**Goal:** Automated transaction classification

**Tasks:**
1. Integrate Anthropic API (Claude Haiku)
2. Build categorization service
3. Set up pgvector for RAG
4. User correction feedback loop
5. Confidence scoring

**Deliverable:** Transactions auto-categorized with >80% accuracy

---

### Phase 3: Bills & Analysis (2-3 weeks)
**Goal:** Recurring expense tracking

**Tasks:**
1. Bill detection algorithm
2. Historical price tracking
3. Subscription identification
4. Spending pattern visualization
5. Net worth dashboard

**Deliverable:** See recurring bills, track price changes, view net worth

---

### Phase 4: SMSF Core (3-4 weeks)
**Goal:** SMSF portfolio tracking and basic compliance

**Tasks:**
1. SMSF holdings import (CHESS CSV)
2. Contribution cap tracking
3. TSB calculation
4. Basic compliance dashboard

**Deliverable:** SMSF portfolio tracked, contribution caps monitored

---

### Phase 5: SMSF Advanced (3-4 weeks)
**Goal:** Document management and full compliance

**Tasks:**
1. Document storage system
2. Compliance calendar
3. Pension phase tracking
4. CGT/franking credit tracking

**Deliverable:** Complete SMSF compliance management

---

### Phase 6: Retirement Planning (2-3 weeks)
**Goal:** Projection modeling and scenario analysis

**Tasks:**
1. 7-year projection engine
2. Scenario builder
3. Monte Carlo simulation
4. Integration with Claude for insights

**Deliverable:** Retirement projections with probability analysis

---

### Phase 7: Automation & Polish (2-3 weeks)
**Goal:** Add CDR automation and UX improvements

**Tasks:**
1. Integrate Frollo CDR API
2. Automated daily sync
3. Enhanced AI insights
4. Performance optimization
5. User documentation

**Deliverable:** Fully automated, polished system

---

## Open Questions (Decisions Needed)

### Critical Decisions
1. **UI Approach:** Console app, WinForms, or web-based?
2. **CDR Timing:** When to add automation (Month 2? Month 6? Never?)
3. **Scope:** Build everything or start with Phases 1-3 only?

### Technical Decisions
4. **EF Core vs Dapper:** Stick with EF Core or switch to Dapper? (Recommendation: EF Core)
5. **Hybrid approach:** Use both EF Core (CRUD) + Dapper (complex queries)?
6. **RAG implementation:** pgvector or external vector DB?

### Functional Decisions
7. **Bill reminders:** Passive tracking only or light notifications?
8. **Multi-currency:** Australia-only or plan for USD/EUR?
9. **Property tracking:** Manual entry or CoreLogic API ($$$)?
10. **Crypto tracking:** Basic or full exchange integration?

---

## Next Steps

### For Project Owner (You)
1. âœ… Review prd-personal-finance-system.md (strategic PRD)
2. âœ… Read ORM_COMPARISON.md (understand EF Core vs Dapper)
3. âœ… Read CDR_OPEN_BANKING.md (decide on bank sync approach)
4. âœ… Decide on Phase 1 scope (do we build all 7 phases or start smaller?)
5. âœ… Answer open questions above

### For Implementation Team (Developer/AI)
1. âœ… Read DATABASE_SCHEMA.md
2. âœ… Set up PostgreSQL database
3. âœ… Create C# project with EF Core
4. âœ… Build Phase 1 (basic account/transaction tracking)
5. âœ… Iterate based on feedback

---

## File Locations

All documents are in: `/mnt/user-data/outputs/`

```
outputs/
├── prd-personal-finance-system.md     (Main strategic PRD)
├── DATABASE_SCHEMA.md                  (PostgreSQL schema)
├── ORM_COMPARISON.md                   (EF Core vs Dapper guide)
├── CDR_OPEN_BANKING.md                 (Bank sync options)
├── prd-smsf-portfolio-manager.md      (Deprecated, SMSF-only)
└── README.md                           (This file)
```

---

## Success Criteria

### Phase 1 Success
- âœ… Import 3-6 months of Westpac transactions
- âœ… Store in PostgreSQL
- âœ… Query via REST API
- âœ… Claude can query and provide insights

### Full System Success
- âœ… All accounts tracked automatically (or easily)
- âœ… >95% categorization accuracy
- âœ… Weekly review < 10 minutes
- âœ… SMSF compliance confidence: 100%
- âœ… Retirement planning projections working
- âœ… $0-420/year cost (vs $132-360 for commercial software)

---

## Cost Estimate

### Development Cost (Time)
- **Phase 1:** 40-60 hours (foundation)
- **Phase 2:** 20-30 hours (AI categorization)
- **Phase 3:** 20-30 hours (bills & analysis)
- **Phase 4-6:** 60-80 hours (SMSF)
- **Phase 7:** 20-30 hours (polish)
- **Total:** 160-230 hours

**At 10 hours/week:** 16-23 weeks (4-6 months)

### Operational Cost (Ongoing)
- PostgreSQL: $0 (self-hosted)
- Anthropic API: ~$5-10/month (categorization)
- CDR (optional): $35/month (Frollo) or $0 (manual)
- **Total:** $5-45/month

**Compared to BGL Simple Fund 360:** $132-360/year  
**Savings:** $87-315/year

---

## Recommended Starting Point

1. **This week:** Read all 4 main documents
2. **Next week:** Set up PostgreSQL with schema
3. **Week 3:** Build Phase 1 (CSV import + basic API)
4. **Week 4:** Test with real Westpac data
5. **Month 2:** Decide on Phases 2-3 scope

**Don't try to build everything at once.** Phase 1 alone is valuable - you'll have a working system to track all your finances.

---

**Documentation Status:** âœ… Complete and Ready for Implementation  
**Next Milestone:** Database setup and Phase 1 development  
**Target Start Date:** January 2026

---

*End of Documentation Index*
---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: John's Notes/Personal Finance Orig/README.md
