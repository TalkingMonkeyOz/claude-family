---
tags: []
projects: []
---
# PRD: Holistic Personal Finance System
## AI-Powered Financial Management with SMSF Specialization

**Version:** 1.0 (Strategic)  
**Date:** 26 December 2025  
**Author:** Claude (Managing Director, AI Company)  
**Stakeholder:** John

---

## 1. Purpose

Build a **comprehensive, AI-powered personal finance system** that provides complete visibility and control over all financial accounts, with specialized SMSF compliance and retirement planning capabilities. The system addresses the fundamental problem: **fragmented financial data across multiple institutions with no intelligent aggregation, analysis, or proactive guidance**.

### Core Problem Statement
Existing solutions (YNAB, Pocketbook, MoneyBrilliant) fail because:
- **Auto-categorization is poor**: Generic rules miss context and patterns
- **No SMSF specialization**: Retirement funds treated like bank accounts
- **Cloud-dependent**: Privacy concerns with third-party data hosting
- **Limited AI insights**: No proactive pattern detection or anomaly alerts
- **Subscription fatigue**: Ongoing costs for basic functionality

### Solution Vision
A **local-first, PostgreSQL-backed system** that:
1. **Automatically ingests** transactions from all financial institutions
2. **AI-categorizes** using Claude (Sonnet/Haiku) with RAG-enhanced learning
3. **Holistically tracks** net worth, cash flow, and goal progress
4. **Specializes in SMSF** compliance, documents, and retirement planning
5. **Proactively identifies** spending anomalies, hidden costs, and optimization opportunities

---

## 2. Core Functions

### 2.1 Universal Account Aggregation

**Purpose**: Single source of truth for all financial accounts

**Functions**:
- **Account Types Supported**:
  - Transaction accounts (everyday, savings)
  - Credit cards
  - Loans (home, personal, car)
  - Investment accounts (shares, ETFs, managed funds)
  - Cryptocurrency wallets
  - Property valuations
  - SMSF (specialized module - see 2.6)

- **Data Ingestion**:
  - Automated transaction downloads via Open Banking APIs (CDR)
  - CSV import from banks/brokers for manual refresh
  - Manual entry for cash transactions or unsupported accounts
  - Real-time balance updates (where supported by CDR)

- **Transaction Tracking**:
  - Capture date, merchant, amount, category, account
  - Deduplication across multiple import sources
  - Support for split transactions (e.g., Costco groceries + fuel)
  - Attachment storage (receipts, invoices)

### 2.2 AI-Powered Categorization

**Purpose**: Intelligent, context-aware transaction classification

**Functions**:
- **Claude-Based Categorization**:
  - Use Claude Haiku for fast, low-cost batch categorization
  - Use Claude Sonnet for complex/ambiguous transactions
  - RAG enhancement: Learn from user corrections and historical patterns
  - Context awareness: "Bunnings" → Home Improvement vs Lunch (café)

- **Category Hierarchy**:
  - Top-level: Income, Housing, Transport, Food, Entertainment, etc.
  - Sub-categories: Groceries, Dining Out, Takeaway, Coffee
  - User-definable custom categories

- **Anomaly Detection**:
  - Identify unusual spending patterns (MS Money scenario: accumulated subscriptions)
  - Flag duplicate charges or potential fraud
  - Highlight merchant name changes (e.g., Netflix → Netflix Australia Pty Ltd)

- **Learning System**:
  - Store user corrections in vector database (RAG)
  - Improve accuracy over time per user's unique spending patterns
  - Confidence scoring: Auto-apply high confidence, flag low confidence for review

### 2.3 Bill & Subscription Tracking

**Purpose**: Capture recurring expenses and track price changes over time

**Functions**:
- **Bill Capture**:
  - Detect recurring transactions (monthly, quarterly, annual)
  - Store bill details: provider, amount, frequency, due date
  - No payment reminders (user manages externally), just tracking

- **Historical Price Analysis**:
  - Track price changes for same bill over time
  - Example: "Electricity bill: $450 (Q4 2024) → $520 (Q1 2025) = +15.6%"
  - Identify inflation trends across categories
  - Compare to CPI data for context

- **Subscription Identification**:
  - Auto-detect streaming services, gym memberships, software subscriptions
  - Flag "forgotten" subscriptions (low usage vs cost)
  - Annual cost summaries: "Total subscriptions: $2,400/year"

### 2.4 Net Worth & Cash Flow Tracking

**Purpose**: Holistic financial health monitoring

**Functions**:
- **Net Worth Dashboard**:
  - Assets (accounts, investments, property, super) minus Liabilities (loans, credit cards)
  - Historical trend chart (monthly snapshots)
  - Allocation breakdown (liquid, invested, property, super)

- **Cash Flow Analysis**:
  - Income vs Expenses over time (monthly, quarterly, annual)
  - Burn rate calculation for runway planning
  - Seasonal pattern detection (e.g., December spending spike)

- **Goal Tracking**:
  - Define goals: Emergency fund ($20k), House deposit ($100k), Retirement ($2M)
  - Track progress with projected completion dates
  - Scenario modeling: "If I save $1k/month extra, goal reached by..."

### 2.5 Investment Portfolio Tracking

**Purpose**: Monitor non-SMSF investments (personal brokerage, ETFs, crypto)

**Functions**:
- **Holdings Tracking**:
  - Shares, ETFs, managed funds, crypto
  - Cost base, current value, unrealized gains
  - Dividend/distribution history

- **Performance Metrics**:
  - Total return, time-weighted return
  - Benchmarking (vs ASX 200, All Ords)
  - Asset allocation (domestic/international, sectors)

- **Tax Tracking**:
  - CGT events and holding periods
  - Franking credits (for shares)
  - Cost base adjustments (DRP, corporate actions)

- **Integration**:
  - Import from broker statements (CSV)
  - Link to transaction accounts (dividends, purchases)
  - Separate from SMSF portfolio (different tax treatment)

### 2.6 SMSF Module (Specialized Subsystem)

**Purpose**: Comprehensive SMSF management with compliance, documents, and retirement planning

#### 2.6.1 Portfolio Tracking
- All functions from 2.5 (Investment Portfolio) plus:
- **SMSF-Specific Holdings**:
  - Segregate SMSF assets from personal investments
  - Track accumulation vs pension phase allocations
  - Property tracking (if LRBA used)

- **Performance Attribution**:
  - Separate returns by asset class
  - Account for contributions and withdrawals
  - Compare to target return needed for retirement goal

#### 2.6.2 Compliance Monitoring
- **Contribution Caps**:
  - Track concessional ($30k) and non-concessional ($120k) against FY limits
  - Calculate carry-forward eligibility (TSB < $500k check)
  - Calculate bring-forward availability (TSB thresholds)
  - Alert when approaching 90% of caps

- **Total Superannuation Balance (TSB)**:
  - Maintain TSB for threshold checks
  - Track against key limits ($500k, $1.76M, $2M, $3M)

- **Pension Phase Compliance**:
  - Calculate minimum pension drawdown based on age
  - Track payments against minimum requirement
  - Alert if minimum not met by 30 June

- **Transfer Balance Cap**:
  - Track personal TBC
  - Monitor pension account against limit
  - Flag excess transfer balance issues

#### 2.6.3 Document Management
- **Document Storage**:
  - Trust deed and amendments
  - Investment strategy (with annual review reminders)
  - Member statements
  - Trustee declarations and minutes
  - Financial statements (7-year retention)
  - Audit reports
  - ATO correspondence

- **Document Organization**:
  - Auto-categorize by type and financial year
  - Full-text search
  - Version control for updated documents
  - Scan/upload receipts for transactions

#### 2.6.4 Compliance Calendar & Reminders
- **Key Dates Tracking**:
  - Preservation age milestone
  - Unrestricted access age (60)
  - Downsizer contribution eligibility (55+)

- **Annual Tasks**:
  - Investment strategy review (annual reminder)
  - Asset valuations (30 June deadline)
  - Financial statements preparation
  - Audit completion
  - SMSF annual return lodgement
  - Member statements distribution

- **Quarterly Tasks**:
  - TBAR lodgement (if in pension phase)
  - Minimum pension payment check

- **Ad-hoc Reminders**:
  - Trustee meeting scheduling
  - Document expiry alerts

#### 2.6.5 Retirement Planning & Projections
- **7-Year Projection Model** (as per existing artifact):
  - Multiple scenarios (Conservative, Base, Optimistic)
  - Contribution modeling
  - Interactive assumption adjustments
  - Probability assessment for goal attainment

- **Scenario Comparison**:
  - Model different strategies (Plenti deployment, geared ETFs)
  - What-if analysis
  - Monte Carlo simulation (advanced)

- **Transition to Retirement**:
  - TTR pension calculator
  - Tax arbitrage modeling
  - Pension vs accumulation optimization

- **Retirement Income Projection**:
  - Drawdown modeling
  - Age pension interaction
  - Longevity planning (to age 95)

---

## 3. Key Differentiators

### 3.1 AI-Powered Intelligence
- **Proactive anomaly detection**: Find hidden costs like MS Money did
- **Context-aware categorization**: Better than rule-based systems
- **Natural language queries**: "How much did I spend on coffee last month?"
- **Predictive insights**: "Your electricity bill is trending 20% higher than last year"

### 3.2 Privacy-First Architecture
- **Local data storage**: PostgreSQL on your infrastructure
- **No cloud sync**: Data never leaves your control
- **Open source potential**: Full transparency and auditability

### 3.3 SMSF Specialization
- **Only system combining** personal finance + SMSF compliance
- **Document management**: No other tool handles SMSF docs
- **Compliance automation**: Contribution caps, pension minimums, TBC tracking
- **Retirement planning**: Integrated with overall financial picture

### 3.4 Automated & Holistic
- **Complete visibility**: All accounts, all transactions, all assets
- **Minimal manual effort**: Auto-download, auto-categorize, auto-reconcile
- **Integrated workflows**: Link transactions to bills, investments, goals

---

## 4. System Architecture (High-Level)

### 4.1 Data Layer
- **PostgreSQL Database**: Primary data store
  - Accounts, transactions, categories, bills
  - SMSF holdings, contributions, documents
  - User corrections and RAG vectors
  
- **Vector Database** (pgvector extension): 
  - Store transaction embeddings for similarity search
  - Learn from user corrections
  - Improve categorization over time

### 4.2 Integration Layer
- **CDR (Consumer Data Right) / Open Banking**: 
  - Automated transaction downloads from Australian banks
  - Real-time balance updates
  - Standardized API across institutions

- **Broker/Registry APIs** (where available):
  - Share price feeds
  - Dividend notifications
  - CHESS holdings sync

- **Fallback: CSV Import**: 
  - Manual imports for unsupported institutions
  - One-time historical data migration

### 4.3 AI Layer
- **Claude Haiku**: Fast batch categorization
- **Claude Sonnet**: Complex transactions, anomaly investigation
- **RAG Pipeline**: 
  - Embed transaction descriptions
  - Search similar historical transactions
  - Apply learned categories with confidence scoring

### 4.4 Application Layer
- **Backend API** (Python/FastAPI or C#/.NET):
  - Transaction ingestion and processing
  - Category assignment and learning
  - Report generation

- **Frontend** (TBD):
  - Web dashboard (React)
  - Desktop app (C# WinForms or Electron)
  - Mobile view (responsive web)

- **Claude Artifact** (Analysis & Planning):
  - Interactive visualizations
  - Scenario modeling
  - Natural language insights

---

## 5. Phased Approach

### Phase 1: Foundation (Core Personal Finance)
**Goal**: Basic account aggregation and transaction tracking

- PostgreSQL schema and data models
- CDR integration for 1-2 major banks (CBA, Westpac)
- Manual CSV import for unsupported accounts
- Basic transaction storage and deduplication
- Simple category assignment (manual initially)
- Net worth dashboard (assets, liabilities, trend)

### Phase 2: AI Categorization
**Goal**: Automated, intelligent transaction classification

- Claude Haiku integration for batch categorization
- RAG pipeline with pgvector
- User correction feedback loop
- Confidence scoring and flagging
- Anomaly detection rules

### Phase 3: Bills & Analysis
**Goal**: Recurring expense tracking and historical insights

- Bill detection and tracking
- Historical price analysis
- Subscription identification
- Spending pattern visualization
- Budget vs actual reporting

### Phase 4: SMSF Core
**Goal**: SMSF portfolio tracking and compliance basics

- SMSF account segregation
- Holdings import (CHESS CSV)
- Contribution cap tracking
- TSB calculation
- Basic compliance dashboard

### Phase 5: SMSF Advanced
**Goal**: Full SMSF compliance and document management

- Document storage and organization
- Compliance calendar and reminders
- Pension phase tracking
- CGT and franking credit tracking
- Annual return data export

### Phase 6: Retirement Planning
**Goal**: Projection modeling and scenario analysis

- 7-year projection engine
- Scenario builder
- Monte Carlo simulation
- Claude artifact integration
- Retirement income modeling

### Phase 7: Polish & Automation
**Goal**: Refinement and enhanced automation

- Automated price feeds for investments
- Enhanced AI insights
- Mobile optimization
- Performance tuning
- User documentation

---

## 6. Success Criteria

### Personal Finance Module
- **Account Coverage**: 100% of John's financial accounts tracked
- **Categorization Accuracy**: >95% correct after 3 months of learning
- **Time Savings**: Weekly review reduced from 30+ min to <10 min
- **Anomaly Detection**: Identify at least 1 hidden cost or optimization in first 6 months
- **Net Worth Visibility**: Real-time accurate within <1% of manual calculation

### SMSF Module
- **Compliance Confidence**: 100% accuracy on contribution cap tracking
- **Document Accessibility**: All SMSF docs retrievable in <30 seconds
- **Retirement Planning**: Maintain >60% probability of reaching $1.5M target
- **ATO Readiness**: Generate audit-ready reports in <5 minutes
- **Zero Breaches**: No accidental contribution cap or pension minimum violations

### Technical
- **Automation Rate**: >80% of transactions auto-categorized correctly
- **Data Sync**: CDR sync completes in <2 minutes for 1000 transactions
- **Performance**: Dashboard loads in <3 seconds with 50,000 transactions
- **Uptime**: System available 99%+ (local hosting)
- **Privacy**: Zero data leakage (all local, no cloud sync)

---

## 7. Open Questions & Decisions Needed

### Technical Decisions
1. **Backend Technology**: Python (FastAPI) vs C# (.NET 8)?
   - Python: Better AI integration, pgvector libraries
   - C#: John's familiarity, Windows Forms option

2. **Frontend Strategy**: Web-only vs Desktop app vs Hybrid?
   - Web: Single codebase, mobile-friendly
   - Desktop: Richer features, offline capability
   - Hybrid: Electron (web tech, desktop deployment)

3. **CDR Provider**: Basiq vs Frollo vs Direct bank APIs?
   - Basiq: Mature, good coverage
   - Frollo: Cheaper, newer
   - Direct: Most control, highest effort

4. **RAG Implementation**: Dedicated vector DB vs pgvector extension?
   - pgvector: Simple, single database
   - Pinecone/Weaviate: Specialized, potentially faster

### Functional Decisions
5. **Bill Reminder Implementation**: Passive tracking only or light notifications?
   - Current: Just track, no reminders
   - Alternative: Optional email/notification for due dates

6. **Multi-Currency Support**: Australia-only initially, or plan for USD/EUR?
   - Phase 1: AUD only
   - Phase 3+: Multi-currency with conversion tracking

7. **Property Valuation**: Manual entry vs API integration (CoreLogic)?
   - Manual: Free, less accurate
   - API: Automated, costs $$

8. **Crypto Tracking**: Basic (manual balance) vs Advanced (API integration)?
   - Basic: Manual entry, simple tracking
   - Advanced: Exchange APIs, DeFi wallet tracking

### AI & Categorization
9. **RAG Training Data**: How much history needed before categorization is reliable?
   - Hypothesis: 3 months of corrected data
   - Test: Measure accuracy over time

10. **Anomaly Thresholds**: How to define "unusual" spending?
    - Z-score approach (statistical outliers)?
    - User-defined thresholds per category?
    - Claude judgment call?

---

## 8. Next Steps

### Immediate (Next 7 Days)
1. **Review & Approve** this strategic PRD
2. **Technical Stack Decision**: Python or C#? Web or Desktop?
3. **CDR Provider Research**: Compare Basiq vs Frollo pricing and capabilities
4. **Database Schema Design**: Start designing PostgreSQL schema for accounts/transactions

### Short-Term (Next 30 Days)
5. **Phase 1 Kickoff**: Build foundation (database, CDR integration, basic UI)
6. **Test CDR Integration**: Connect to one bank, import transactions
7. **Basic Categorization**: Manual category assignment UI
8. **Net Worth Dashboard**: Simple visualization of accounts

### Medium-Term (Next 90 Days)
9. **AI Integration**: Implement Claude Haiku categorization
10. **RAG Pipeline**: Build pgvector learning system
11. **SMSF Module Start**: Begin Phase 4 planning

---

## Appendix A: Technology Considerations

### PostgreSQL vs SQLite (Decision: PostgreSQL)
| Factor | PostgreSQL | SQLite | Winner |
|--------|------------|--------|--------|
| Scalability | 100k+ transactions easily | Limited for large datasets | **PostgreSQL** |
| Concurrent access | Multi-user ready | Single-writer bottleneck | PostgreSQL |
| Vector support | pgvector native | External libraries | **PostgreSQL** |
| Backup/recovery | Robust tools | Manual file copy | PostgreSQL |
| John's preference | âœ… Has Postgres running | N/A | **PostgreSQL** |

### CDR Providers (Australian Open Banking)
| Provider | Coverage | Cost | Notes |
|----------|----------|------|-------|
| **Basiq** | 80+ banks | ~$50/mo | Mature, well-documented |
| **Frollo** | 90+ banks | ~$30/mo | Newer, good pricing |
| **Illion** | 100+ banks | $$$$ | Enterprise-focused |
| **Direct APIs** | Limited | Free | High effort, inconsistent |

**Recommendation**: Start with **Basiq** (free sandbox for development), evaluate Frollo for production.

### AI Model Selection
| Task | Model | Reasoning |
|------|-------|-----------|
| Batch categorization | Claude Haiku | Fast, cheap, accurate for simple cases |
| Complex transactions | Claude Sonnet | Better reasoning for ambiguous merchants |
| Anomaly explanation | Claude Sonnet | Natural language insights |
| RAG embeddings | voyage-2 or OpenAI | Specialized for semantic search |

---

## Appendix B: Example Workflows

### Workflow 1: Weekly Review (Target: <10 min)
1. **Auto-sync**: CDR pulls last 7 days of transactions (2 min)
2. **AI categorization**: Claude Haiku processes uncategorized (1 min)
3. **User review**: Check flagged low-confidence transactions (3 min)
4. **Dashboard check**: Review spending vs budget, net worth trend (2 min)
5. **SMSF update**: Import CHESS statement if applicable (2 min)

**Total: 10 minutes** (vs 30-60 min manually updating spreadsheets)

### Workflow 2: Month-End Close
1. **Reconciliation**: Verify all accounts synced correctly
2. **Category cleanup**: Review and correct any miscategorizations
3. **Bill analysis**: Check for price increases on recurring bills
4. **Savings rate**: Calculate monthly savings vs target
5. **Net worth snapshot**: Save monthly valuation
6. **SMSF compliance**: Check contribution cap usage if applicable

### Workflow 3: SMSF Annual Tasks (June 30)
1. **Valuation**: Update prices for all SMSF holdings
2. **Contributions**: Finalize FY contributions, check caps
3. **Documents**: Ensure all trades/statements uploaded
4. **Investment strategy**: Review and update if needed
5. **Export**: Generate data for accountant/auditor
6. **Pension check**: Verify minimum pension paid (if applicable)

---

**Document Status**: âœ… Ready for Review  
**Next Milestone**: Technical stack decision by Dec 31, 2025  
**Phase 1 Start**: January 2026

---

*End of Strategic PRD - Purpose & Functions Focus*
---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: John's Notes/Personal Finance Orig/prd-personal-finance-system.md
