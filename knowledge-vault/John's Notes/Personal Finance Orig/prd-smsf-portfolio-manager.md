---
tags: []
projects: []
---
# PRD: SMSF Portfolio Manager
## Integrated Personal Finance System for Self-Managed Super Funds

**Version:** 1.0  
**Date:** 25 December 2025  
**Author:** Claude (Managing Director, AI Company)  
**Stakeholder:** John, Primary User

---

## 1. Product Overview

### 1.1 Document Title and Version
- **PRD:** SMSF Portfolio Manager - Integrated Personal Finance System
- **Version:** 1.0
- **Status:** Mixed (React Artifact: Prototype Complete | C# Backend: Greenfield)

### 1.2 Product Summary

The SMSF Portfolio Manager is a comprehensive two-component personal finance system designed for self-managed superannuation fund (SMSF) members who need sophisticated tracking, compliance monitoring, and retirement planning capabilities without relying on expensive commercial software or cloud-hosted solutions.

**Primary User Context:**
- Name: John
- Age: 52 (born 26 December 1972, turning 53 in one day)
- Current SMSF Balance: $609,819 (Cash: $60,777 | Plenti Notes: $137,000 @ 9% p.a. | Shares: $412,042)
- Retirement Goal: $2,000,000 by age 60 (December 2032)
- Acceptable Floor: $1,000,000
- Risk Tolerance: High (given acceptable floor)
- Timeline: 7 years

**System Architecture:**

**Component 1: C# Windows Forms Application (Data Manager)**
- Local SQLite database for all portfolio data
- CSV import from CHESS statements and broker reports
- Manual entry for cash, fixed income, and transactions
- JSON export capability for artifact integration
- Privacy-first: all data stored locally, no cloud dependency

**Component 2: Claude Artifact (Analysis & Planning Engine)**
- Interactive portfolio dashboard with real-time calculations
- Scenario modeling with adjustable assumptions
- Compliance tracking (contribution caps, preservation age milestones)
- AI-powered insights through natural language interaction
- Persistent state using window.storage API

**Current State:**
- React artifact (SMSFPortfolioManager.jsx) has been developed and tested with John's actual holdings
- C# backend is in planning/architecture phase
- Integration pattern defined (JSON export/import between components)

The system addresses three critical pain points:
1. **Fragmented visibility**: No single source of truth for complete SMSF position across multiple asset types
2. **Manual compliance burden**: Tracking contribution caps, CGT, franking credits, and preservation age milestones is error-prone
3. **Planning complexity**: Difficulty modeling "what-if" scenarios and assessing probability of reaching retirement goals

---

## 2. Goals

### 2.1 Business Goals
- **Eliminate commercial software costs**: Avoid $132-360/year subscription fees for BGL Simple Fund 360 or Class Super while maintaining equivalent functionality for personal use
- **Maintain regulatory compliance**: Ensure 100% ATO compliance through automated tracking of contribution caps, CGT events, and pension phase requirements
- **Enable data sovereignty**: Keep all financial data under John's control on local storage (no cloud sync, no third-party access)
- **Support aggressive wealth building**: Provide sophisticated scenario modeling to evaluate high-risk/high-return strategies needed to bridge the $1.39M gap to target in 7 years

### 2.2 User Goals
- **Daily confidence**: Know exact SMSF position (total value, unrealized gains, asset allocation) within seconds
- **Strategic clarity**: Understand probability of reaching $2M target under different market scenarios and contribution strategies
- **Proactive compliance**: Receive alerts before breaching contribution caps or missing pension minimums
- **Informed decisions**: Evaluate tax implications (CGT, franking credits) before making portfolio changes
- **Efficient administration**: Reduce time spent on manual tracking from hours/week to minutes/week
- **AI-assisted analysis**: Ask natural language questions ("Should I sell MIN given the 213% gain?") and receive data-driven insights

### 2.3 Non-Goals
- **Multi-fund management**: System is designed for single SMSF with single member (John); not targeting accountants or advisers managing multiple clients
- **Real-time trading**: No broker integration or trade execution; focus is on tracking and planning, not transaction execution
- **Mobile-native experience**: Primary interface is desktop (C# app + browser artifact); mobile access is view-only convenience
- **ATO lodgement integration**: No direct submission of TBAR or annual returns; export data for accountant/auditor instead
- **Automated price feeds** (Phase 1): Manual price entry or CSV import initially; API integration is Phase 5 enhancement
- **Property tracking** (Phase 1): Focus on listed securities (shares, ETFs) and cash/fixed income; LRBA property is future enhancement

---

## 3. User Personas

### 3.1 Key User Types

**Primary User: The Engaged Self-Directed Investor**
- Age: 50-60, nearing retirement with significant SMSF balance ($500k-$1M+)
- Technical proficiency: Comfortable with desktop applications and spreadsheets
- Investment approach: Active, research-driven, willing to take calculated risks
- Time commitment: Willing to spend 1-2 hours/week on portfolio management and planning
- Privacy conscious: Prefers local data storage over cloud services
- Cost-sensitive: Avoids subscription software when DIY alternatives exist

**Secondary User: The DIY Developer/Tinkerer**
- Technical background: Software development or engineering
- Customization desire: Wants to modify/extend system for specific needs
- Open source mindset: Values transparency and control over proprietary solutions

### 3.2 Basic Persona Details

**Persona: John - The Aggressive Wealth Builder**

*Background:*
- Professional services software consultant at Nimbu (formerly Time2Work)
- 52 years old, single member SMSF trustee
- Strong logical reasoning skills, technically competent
- Interest in AI and exploring its limits

*Current Situation:*
- SMSF balance: $609,819 ($1.39M short of $2M target)
- 7 years to retirement (age 60)
- Preservation age reached in 3 years (age 56 - December 2028)
- Personal income: $140,000/year (supports salary sacrifice contributions)

*Portfolio Characteristics:*
- 13 share holdings with wide performance range (-61% to +213%)
- Heavy concentration in resources sector (47.6% of shares)
- Overall portfolio: +42.3% unrealized gain
- Dividend income + franking credits supplement growth
- $137k in Plenti Notes earning guaranteed 9% until maturity (2026-2027)

*Pain Points:*
- No consolidated view of complete position across cash, fixed income, and shares
- Uncertain about probability of reaching $2M target under different scenarios
- Difficulty evaluating which winners to take profits on (MIN +213%, PLS +190%)
- Manual tracking of contribution caps with carry-forward confusion
- Cannot easily model impact of geared ETF strategies (GEAR, GGUS) vs individual stocks

*Goals & Motivations:*
- Retire at 60 with enough passive income to maintain lifestyle
- Willing to accept $1M floor if markets underperform
- Wants to maximize tax-effective contributions while staying compliant
- Interested in aggressive strategies (geared ETFs at 2x leverage) given risk tolerance
- Seeks AI-powered insights to augment decision-making

*Technical Context:*
- Uses Westpac Banking for cash accounts
- Uses Westpac Broking for share trading (CHESS statements available)
- Holds Plenti Notes directly (statements via email)
- Familiar with Windows desktop applications
- Comfortable with JSON, CSV, and database concepts

### 3.3 Role-Based Access

**Single-User System (Phase 1):**
- **Owner/Trustee (John)**: Full access to all features, data entry, configuration, and exports

**Future Consideration (Phase 2+):**
- **Accountant (Read-Only)**: Access to exported reports and financial statements for audit preparation
- **Financial Adviser (Consultation)**: Ability to import scenario data for professional review

---

## 4. Functional Requirements

### 4.1 C# Data Manager - Core Features

#### **Portfolio Tracking** (Priority: HIGH - Phase 1)
- **Multi-asset support**: Track shares, ETFs, cash, and fixed income (Plenti Notes) in unified database
- **CHESS CSV import**: Parse and import holdings from Westpac Broking CHESS statements with automatic code/unit/price extraction
- **Manual entry interface**: Form-based input for cash balances, fixed income positions, and price updates
- **Cost base tracking**: Store purchase date, purchase price, and units for each parcel to enable CGT calculation
- **Current valuation**: Store and update current prices with last-updated timestamp
- **Sector classification**: Categorize holdings (Banks, Resources, ETFs, Other) for allocation analysis
- **Historical snapshots**: Save daily/weekly valuations for performance tracking over time

#### **Transaction Management** (Priority: MEDIUM - Phase 2)
- **Transaction logging**: Record BUY, SELL, DIVIDEND, DISTRIBUTION, DRP, CONTRIBUTION events
- **CGT event tracking**: Flag transactions that trigger capital gains/losses
- **Franking credit capture**: Store franking % and credit amount for each dividend
- **Brokerage/fees**: Include transaction costs in cost base calculations
- **Bulk import**: CSV import for transaction history from broker statements

#### **Compliance Tracking** (Priority: HIGH - Phase 1)
- **Contribution cap monitoring**: Track concessional ($30k) and non-concessional ($120k) against financial year caps
- **Carry-forward calculation**: Determine available unused concessional cap from previous 5 years (requires TSB < $500k check)
- **Bring-forward eligibility**: Calculate 3-year NCC bring-forward availability based on TSB thresholds ($1.76M, $1.88M, $2.0M)
- **TSB tracking**: Maintain total superannuation balance for threshold checks
- **Age-based milestones**: Alert for preservation age (56), unrestricted access (60), downsizer eligibility (55+)

#### **Reporting & Export** (Priority: HIGH - Phase 1)
- **JSON export for artifact**: Generate complete portfolio snapshot in standardized JSON format for Claude artifact consumption
- **PDF reports**: Portfolio summary, performance report, holdings statement (Phase 2)
- **Excel export**: Raw data export for external analysis or accountant sharing (Phase 2)
- **CSV export**: Transaction history and holdings list in standard format

#### **Data Management** (Priority: HIGH - Phase 1)
- **SQLite database**: Local storage with schema supporting holdings, transactions, contributions, valuations
- **Backup/restore**: Manual backup to JSON/ZIP for disaster recovery
- **Data validation**: Ensure data integrity (no negative units, valid dates, reasonable prices)
- **Audit trail**: Track when data was last updated and by which import source

### 4.2 Claude Artifact - Analysis & Planning Features

#### **Portfolio Dashboard** (Priority: HIGH - Status: COMPLETE)
- **Total value display**: Real-time calculation of cash + fixed income + shares with daily change
- **Asset allocation visualization**: Pie charts for shares/fixed income/cash split and sector breakdown
- **Holdings table**: Sortable list showing code, units, price, value, unrealized gain ($ and %), sector
- **Performance metrics**: Total unrealized gain, gain %, top winners/losers
- **Target progress**: Visual indicator of current balance vs $2M goal with % completion
- **Time remaining**: Countdown to age 60 retirement target

#### **Projection Modeling** (Priority: HIGH - Status: COMPLETE)
- **Multi-scenario projections**: Generate Conservative (7%), Base Case (10%), Optimistic (14%), Best Case (17%) return scenarios
- **7-year forecast**: Year-by-year balance projections to age 60 retirement date
- **Contribution modeling**: Include annual contributions ($25,500 net after 15% tax) in projections
- **Interactive assumptions**: Sliders for adjusting return rates, contribution amounts, inflation
- **Probability assessment**: Calculate likelihood of hitting $2M target, $1.5M milestone, $1M floor
- **Milestone tracking**: Identify when fund crosses $1M (preservation assurance) in each scenario
- **Chart visualization**: Line chart showing all scenarios with target ($2M) and floor ($1M) reference lines

#### **Compliance Dashboard** (Priority: HIGH - Status: COMPLETE)
- **Contribution cap gauges**: Visual progress bars for concessional and non-concessional caps with remaining amounts
- **Key dates tracker**: Countdown to preservation age (56), retirement age (60), downsizer eligibility (55)
- **FY tracking**: Automatic financial year detection (July 1 - June 30) for cap resets
- **Bring-forward alerts**: Indicate when 3-year bring-forward is available based on TSB

#### **Scenario Comparison** (Priority: MEDIUM - Status: COMPLETE)
- **Side-by-side comparison**: Compare Conservative vs Base vs Optimistic outcomes at age 60
- **Strategy evaluation**: Model different approaches (keep Plenti to maturity vs early deployment, geared ETF allocation levels)
- **What-if analysis**: Adjust assumptions (contribution increases, market correction timing, geared ETF %) and see impact
- **Sensitivity analysis**: Identify which variables have greatest impact on reaching target

#### **Data Persistence** (Priority: HIGH - Status: COMPLETE)
- **window.storage integration**: Save portfolio data, assumptions, and user adjustments to browser persistent storage
- **State recovery**: Reload last session on artifact reopen
- **Export/import**: Download current state as JSON for backup or sharing

#### **Interactive Analysis** (Priority: MEDIUM - Status: FUTURE)
- **AI conversation**: Ask Claude questions about portfolio in natural language
  - "Should I sell my MIN position?"
  - "What's the tax impact of selling 50% of PLS?"
  - "How does my sector allocation compare to a balanced portfolio?"
- **Strategy recommendations**: Claude analyzes holdings and suggests rebalancing, profit-taking, or diversification actions
- **Alert generation**: Proactive notifications (e.g., "You're approaching 90% of concessional cap")

### 4.3 Integration Features

#### **C# → Artifact Data Flow** (Priority: HIGH - Phase 1)
- **One-click export**: Button in C# app to generate `portfolio_export.json` in standardized format
- **Artifact import**: Claude artifact reads JSON via file upload or paste
- **Schema validation**: Artifact validates JSON structure and displays errors if malformed
- **Version compatibility**: JSON includes schema version for forward compatibility

#### **Artifact → C# Data Flow** (Priority: LOW - Phase 3+)
- **Manual updates**: User can update prices in artifact, export JSON, and import back to C# app (Phase 3)
- **Scenario persistence**: Save artifact scenarios/assumptions to C# database for historical comparison (Phase 3)

---

## 5. User Experience

### 5.1 Entry Points & First-Time User Flow

**C# Application - Initial Setup:**
1. **Installation**: User downloads SMSFPortfolioManager.exe and runs on Windows 10/11 desktop
2. **First launch**: Application creates SQLite database in `%APPDATA%\SMSFPortfolioManager\` and shows welcome wizard
3. **Member setup**: User enters name, date of birth, target retirement age (60), target balance ($2M), floor ($1M)
4. **Data import options presented**:
   - Import CHESS statement CSV (recommended for existing portfolios)
   - Manual entry (for small portfolios or first-time setup)
   - Import from JSON backup (for restoring previous data)
5. **CHESS import walkthrough** (if selected):
   - User downloads CHESS statement CSV from Westpac Broking
   - Drags CSV file to import zone
   - Application parses and displays preview table
   - User confirms import, holdings populate database
6. **Manual entry walkthrough** (if selected):
   - User enters cash balance from bank statement
   - User enters Plenti Notes details (balance: $137k, rate: 9%, maturity: ~2 years)
   - For each share holding: Code, Units, Purchase Price, Purchase Date
   - Application fetches current prices (manual entry for Phase 1, API for Phase 5)
7. **Contribution setup**: User enters current FY contribution amounts (concessional, non-concessional) and carry-forward balances
8. **First export**: Application generates `portfolio_export.json` and saves to desktop
9. **Artifact introduction**: On-screen instructions show how to upload JSON to Claude artifact URL

**Claude Artifact - First Session:**
1. **Access**: User navigates to Claude.ai, opens Project with artifact
2. **Data load prompt**: Artifact shows "Import your portfolio data" file upload button
3. **JSON import**: User uploads `portfolio_export.json` from C# app
4. **Data validation**: Artifact parses JSON, validates schema, displays summary
5. **Dashboard reveal**: Full portfolio dashboard appears with current holdings, allocation charts, projections
6. **Guided tour**: Artifact highlights key sections (Portfolio tab, Projections tab, Compliance tab)
7. **Interactive demo**: User adjusts assumption sliders to see real-time projection changes
8. **Persistence confirmation**: Artifact saves state to window.storage and confirms "Your data will be available next session"

### 5.2 Core Experience

**Weekly Workflow (Typical User Pattern):**

**Step 1: Price Update (Every Monday morning, 5 minutes)**
- User opens C# app
- Clicks "Update Prices" button
- For each holding, enters current price from Westpac Broking or Google Finance (Phase 1 manual, Phase 5 automatic)
- Application recalculates total value, unrealized gains, allocation %
- User clicks "Export to Artifact" to generate updated JSON

**Step 2: Analysis Review (Every Monday morning, 5 minutes)**
- User opens Claude artifact in browser
- Artifact loads previous session state from window.storage
- User clicks "Import Latest Data" and uploads new JSON from C# app
- Dashboard updates to show new total value, gains, and updated projections
- User reviews "Portfolio" tab to check allocation drift
- User reviews "Projections" tab to see if still on track for $2M target
- User notes any alerts (e.g., "Approaching 90% of concessional cap")

**Step 3: Strategic Questions (Ad-hoc, 10-20 minutes)**
- User identifies a decision point (e.g., "MIN is up 213%, should I take profits?")
- User asks Claude (via chat alongside artifact): "What's the tax impact if I sell 50% of MIN?"
- Claude analyzes:
  - Current MIN holding: 893 units @ $52.65 = $47,016 value
  - Cost base: 893 Ã— $16.82 = $15,020
  - Capital gain on 50% sale: ($23,508 - $7,510) = $15,998
  - CGT (10% discount rate, held > 12 months): $15,998 Ã— 10% = $1,600
  - Net proceeds after tax: $23,508 - $1,600 = $21,908
- Claude suggests: "Selling 50% would lock in $16k gain, trigger ~$1,600 CGT, and provide $21,908 to redeploy into diversified ETFs. This reduces your Resources sector concentration from 47.6% to ~36%."
- User evaluates recommendation and makes informed decision

**Step 4: Scenario Planning (Monthly, 20-30 minutes)**
- User opens artifact "Projections" tab
- User creates "What-if" scenario: "What if I deploy Plenti Notes ($137k) into GEAR (2x ASX 200 geared ETF) when it matures in 2026?"
- User adjusts assumptions:
  - GEAR allocation: $137k
  - GEAR expected return: 14% (2x ASX growth minus 0.74% fee)
  - Deployment date: July 2026 (Plenti maturity)
- Artifact recalculates projections with new assumption
- Comparison table shows:
  - Base case (keep Plenti): Age 60 balance = $1,411,000
  - GEAR deployment: Age 60 balance = $1,580,000 (+$169,000)
- User considers risk (geared ETF volatility) vs reward (higher terminal value)

**Step 5: Compliance Check (Quarterly, 5 minutes)**
- User opens artifact "Compliance" tab
- User reviews contribution cap usage:
  - Concessional: $15,000 used / $30,000 cap (50%)
  - Non-concessional: $0 used / $120,000 cap (0%)
  - Carry-forward available: $60,000 (from past 5 years)
- User notes upcoming milestones:
  - Preservation age (56): 3.1 years (December 2028)
  - Retirement age (60): 7.0 years (December 2032)
  - Downsizer eligible (55): NOW (can contribute $300k from home sale if applicable)
- User confirms no alerts requiring immediate action

### 5.3 Advanced Features & Edge Cases

**Edge Case 1: Market Correction (20% Drop)**
- User notices total value dropped from $610k to $488k overnight
- User opens artifact "Projections" tab
- Artifact shows updated projections starting from new $488k base
- Conservative scenario now shows $970k at age 60 (below $1M floor)
- User asks Claude: "How much extra contribution do I need to still hit $1M floor?"
- Claude calculates: "At 7% return, you'd need to increase annual contributions from $25.5k to $40k to reach $1,005,000 at age 60. Alternatively, a single $100k non-concessional contribution now would restore the $1M+ probability to 95%."
- User evaluates options (increase salary sacrifice vs make lump sum contribution)

**Edge Case 2: CHESS Statement Contains Corporate Action**
- User imports CHESS CSV that includes a 1:10 consolidation (TLX)
- C# app detects units changed from 3,280 to 328 (90% reduction) but cost base unchanged
- Application flags as "Corporate Action Detected" and prompts user to confirm
- User confirms consolidation, application adjusts purchase price from $3.04 to $30.42 (10x) to maintain cost base
- Transaction log records: "CORPORATE_ACTION: TLX 1:10 consolidation on [date]"

**Edge Case 3: Contribution Cap Breach**
- User enters concessional contribution that would exceed $30k cap
- C# app displays warning: "This contribution of $5,000 would exceed your concessional cap by $2,000. Excess contributions are taxed at your marginal rate + interest. Confirm?"
- User can choose:
  - Cancel and reduce contribution amount
  - Proceed anyway (if intentional strategy, e.g., Division 293 tax is less than marginal rate)
  - Split contribution (contribute $3k this FY, $2k next FY)

**Edge Case 4: Preservation Age Reached**
- User turns 56 on 26 December 2028
- On next artifact load, compliance dashboard shows: "âœ… Preservation Age Reached! You can now access your super under certain conditions (TTR pension, retirement)."
- Artifact unlocks new "Transition to Retirement" section with TTR pension calculator
- User can model maximum 10% pension drawdown while still working

### 5.4 UI/UX Highlights

**C# Application:**
- **Clean, data-dense interface**: Windows Forms with modern flat design, no unnecessary chrome
- **Quick access toolbar**: Import CSV | Update Prices | Export to Artifact | View Reports
- **Main dashboard**: Summary cards (Total Value, Unrealized Gain, Contribution Caps Used) + Holdings data grid
- **Keyboard-first**: Tab navigation, Enter to save, Esc to cancel, Ctrl+I for import, Ctrl+E for export
- **Validation feedback**: Real-time validation with inline error messages (red border + tooltip)
- **Progress indicators**: Loading spinners for CSV parsing and database operations

**Claude Artifact:**
- **Tabbed navigation**: Portfolio | Projections | Compliance | Settings (persistent across sessions)
- **Responsive charts**: Recharts with tooltips, legends, and interactive elements
- **Color-coded indicators**: Green (gains, on-track), Red (losses, below target), Amber (warnings)
- **Mobile-aware**: Responsive Tailwind layout works on tablet/phone (view-only mode)
- **Dark theme**: Slate-900 background with blue/green accents for readability
- **Accessibility**: Semantic HTML, keyboard navigation, ARIA labels for screen readers

**Integration UX:**
- **Drag-and-drop**: C# app and artifact both support drag-and-drop for JSON/CSV files
- **One-click export**: Single button in C# app generates JSON and copies to clipboard
- **Automatic import**: Artifact detects clipboard JSON and prompts "Import from clipboard?"
- **Version warnings**: If JSON schema version mismatches, artifact shows upgrade prompt

---

## 6. Narrative

John opens his SMSF Portfolio Manager C# application on Monday morning. With a quick glance at the dashboard, he sees his total balance: $612,340—up $2,521 from last week. He updates prices for his 13 holdings by copy-pasting from Westpac Broking (takes 3 minutes). The app recalculates everything instantly: unrealized gains (+42.5%), sector allocation (Resources: 47% - still too high), and his progress toward $2M (30.6% complete).

He clicks "Export to Artifact" and uploads the JSON to his Claude artifact. The interactive projection chart appears, showing four scenarios to age 60. The Base Case line sits at $1,431,000—$569k short of target, but safely above his $1M floor. He moves the "Annual Return" slider from 10% to 12% to see what happens if he adds more geared ETFs. The projection jumps to $1,640,000. He notes this for his weekly strategic review.

Switching to the Compliance tab, he confirms he's used $18,000 of his $30,000 concessional cap this financial year. There's still room for an extra $12k salary sacrifice if he gets a bonus. The artifact reminds him he'll reach preservation age in 3.0 years—meaning he could access super in 2028 if needed.

John asks Claude: "Should I sell my MIN position given the 213% gain?" Claude analyzes the holding, calculates the CGT impact ($1,600 on a 50% sale), and suggests redeploying into VAS to reduce sector concentration. John considers this, then updates his manual notes in the C# app to revisit at month-end.

Five minutes later, John closes the app. He's confident he's on track, knows exactly where he stands, and has a clear picture of the decisions ahead. No spreadsheets, no guesswork, no expensive software subscriptions. Just his data, his system, and his AI partner helping him navigate to a $2M retirement.

---

## 7. Success Metrics

### 7.1 User-Centric Metrics

- **Time to complete weekly review**: < 10 minutes (vs. 30-60 minutes with manual spreadsheets)
  - Target: 90% of weekly reviews completed in < 10 minutes
- **User confidence in position accuracy**: 9/10 rating on "I trust my portfolio data is accurate"
  - Measured via quarterly self-assessment
- **Decision-making confidence**: 8/10 rating on "I feel informed when making portfolio decisions"
  - Measured after major trades (profit-taking, rebalancing)
- **Compliance confidence**: 10/10 rating on "I know I'm within contribution caps"
  - Zero instances of accidental cap breaches

### 7.2 Business Metrics

- **Cost savings**: $132-360/year avoided (BGL Simple Fund 360 subscription)
  - Target: System development cost recouped within 2 years
- **Retirement target probability**: Maintain > 60% probability of reaching $1.5M+
  - Recalculated monthly based on actual performance
- **Portfolio visibility**: 100% of holdings tracked in real-time
  - No manual spreadsheets or paper statements required

### 7.3 Technical Metrics

- **Data accuracy**: 100% match between CHESS statement and C# database after import
  - Validated via automated reconciliation report
- **Export reliability**: 99%+ successful JSON exports (no data corruption)
  - Artifact can parse 100% of generated JSON without errors
- **Performance**: < 2 seconds to recalculate all projections in artifact
  - Even with 20+ holdings and 7-year projection horizon
- **Data persistence**: 100% artifact state recovery after browser close/reopen
  - Using window.storage API

---

## 8. Technical Considerations

### 8.1 Integration Points

**C# Application Integrations:**
- **SQLite Database** (v3.40+): Local relational storage for holdings, transactions, contributions, valuations
  - No server required, single-file database in AppData folder
  - Lightweight ORM (Dapper) for query abstraction
- **CSV Import**: Parse CHESS statements from Westpac Broking
  - CsvHelper library for robust parsing with header detection
  - Custom mapper for ASX code, units, purchase price, current price columns
- **JSON Export**: Newtonsoft.Json for serialization
  - Generate standardized portfolio snapshot with schema version
  - Include member details, holdings, contributions, assumptions
- **Price Feeds** (Phase 5): Optional integration with Alpha Vantage API for automated ASX price updates
  - Free tier allows 5 API calls/minute, 500 calls/day (sufficient for 13 holdings)
- **PDF Generation** (Phase 2): QuestPDF or iTextSharp for report output
  - Portfolio summary, performance report, CGT statement

**Claude Artifact Integrations:**
- **window.storage API**: Browser persistent storage for artifact state
  - Key: `smsf-portfolio` (max 5MB per key)
  - Store portfolio data + user assumptions as JSON
- **File Upload/Download**: Browser File API for JSON import/export
  - Drag-and-drop support via React-Dropzone (optional)
- **Recharts Library**: Interactive charting for projections and allocations
  - Line charts, pie charts, bar charts with tooltips/legends

**External Data Sources (Manual Phase 1):**
- **Westpac Broking**: CHESS statement CSV download (manual)
- **Westpac Banking**: Cash balance from online banking (manual entry)
- **Plenti Notes**: Statement PDF → manual entry of balance and rate
- **ASX Price Lookup**: Google Finance or CommSec price search (manual copy/paste)

### 8.2 Data Storage & Privacy

**Privacy-First Architecture:**
- **Local-only storage**: All financial data stored in SQLite database on user's desktop PC
  - Database file: `%APPDATA%\SMSFPortfolioManager\smsf.db`
  - No cloud sync, no third-party access, no telemetry
- **Artifact storage**: window.storage API in browser (local storage, not synced across devices)
  - Data persists in browser but does not leave user's machine
  - User can clear storage anytime via browser settings
- **Export format**: JSON exports are human-readable and can be audited before sharing
  - User has full control over what data leaves the system

**Data Security:**
- **No encryption** (Phase 1): Data stored in plaintext SQLite (acceptable for local-only, single-user system)
  - Future enhancement: AES-256 encryption of database file with master password
- **Access control**: Windows file system permissions restrict database access to user's account
- **Backup strategy**: User manually backs up database file or exports to JSON
  - No automated cloud backup to avoid data exposure

**Compliance Considerations:**
- **ATO audit readiness**: All transactions logged with date, amount, type for 7-year retention requirement
- **No PII exposure**: JSON exports contain financial data but can be anonymized (replace name with "User") for sharing/debugging

### 8.3 Scalability & Performance

**C# Application Performance:**
- **Database size**: SQLite easily handles 10,000+ transactions with sub-second query times
  - Expected: ~100 transactions/year Ã— 10 years = 1,000 records (minimal load)
- **CSV import speed**: Parse and import 50-row CHESS statement in < 1 second
- **Export generation**: Serialize 20 holdings + 1,000 transactions to JSON in < 500ms
- **UI responsiveness**: Data grid rendering for 50+ holdings in < 100ms

**Claude Artifact Performance:**
- **Projection calculation**: Recalculate 4 scenarios Ã— 7 years (28 data points) in < 100ms (React state update)
  - Uses in-memory JavaScript calculations, no API calls
- **Chart rendering**: Recharts renders 100+ data points in < 200ms
- **Storage I/O**: window.storage write of 5MB JSON in < 50ms
- **Mobile performance**: Responsive layout with lazy loading for charts on slower devices

**Scalability Limits (by design):**
- **Single-user**: No multi-user concurrency to handle
- **Single SMSF**: No need to scale to multiple funds
- **Single member**: No need to aggregate across multiple member accounts

### 8.4 Potential Challenges

**Challenge 1: CHESS Statement Format Changes**
- **Risk**: Westpac Broking changes CSV column headers or format, breaking import
- **Mitigation**: 
  - Use flexible CSV parser with column name mapping
  - Display preview table before import so user can validate
  - Provide manual entry fallback
  - Version CSV import logic with support for multiple formats
- **Likelihood**: Medium (banks do change statement formats occasionally)

**Challenge 2: Price Data Accuracy (Manual Entry)**
- **Risk**: User enters incorrect price, causing portfolio value miscalculation
- **Mitigation**:
  - Validation rules: Price change > 20% from last update triggers confirmation prompt
  - Display last update date/time for each holding to identify stale prices
  - Phase 5: Add automated price feed to eliminate manual entry
- **Likelihood**: Low (user is motivated to keep accurate data)

**Challenge 3: Browser Storage Quota**
- **Risk**: window.storage 5MB limit exceeded if user has large transaction history
- **Mitigation**:
  - Artifact stores only current state + assumptions (~500KB for 100 holdings)
  - Historical data stays in C# SQLite database
  - Provide "Clear Old Data" button in artifact to free space
- **Likelihood**: Very Low (5MB is ~10,000 holdings or 50,000 transactions)

**Challenge 4: JSON Schema Evolution**
- **Risk**: Future versions add new fields, breaking compatibility with old artifacts
- **Mitigation**:
  - Include schema version in JSON header (`schemaVersion: "1.0"`)
  - Artifact validates schema and shows upgrade prompt if mismatch
  - Maintain backward compatibility (new fields optional, old fields never removed)
- **Likelihood**: Medium (as features evolve, schema will change)

**Challenge 5: CGT Calculation Complexity**
- **Risk**: Parcel method selection (FIFO, LIFO, specific), corporate actions, and discount rules create calculation errors
- **Mitigation**:
  - Phase 1: Implement basic CGT (assumes FIFO, 10% discount if > 12 months)
  - Phase 2: Add parcel selection and corporate action tracking
  - Phase 3: Add validation against ATO MyGov records (user compares, not automatic)
  - Recommend user validates with accountant before large sales
- **Likelihood**: Medium (CGT is complex, errors are costly)

---

## 9. Milestones & Sequencing

### 9.1 Project Estimate

- **Size category**: Medium (6-month development with phased rollout)
- **Time estimate**: 24 weeks (assumes 10-15 hours/week effort, single developer)
- **Current status**: 
  - React artifact: ~80% complete (core features working, polish needed)
  - C# backend: 0% complete (architecture defined, implementation not started)

### 9.2 Team Size & Composition

**Single-Developer Project (John + AI Assistance):**
- **John**: Requirements, testing, integration, deployment
- **Claude (AI)**: Code generation, debugging, architecture guidance, documentation

**Optional External Resources:**
- **SMSF Accountant**: Review compliance logic for contribution caps, CGT, pension rules
- **Beta Tester**: Friend/colleague with SMSF to validate import process and UX

### 9.3 Suggested Phases

**Phase 1: MVP - Foundation (Weeks 1-8)**
*Goal: Working C# app that imports CHESS data and exports to existing artifact*

**Week 1-2: Project Setup**
- âœ… Create Visual Studio solution and project structure
- âœ… Set up SQLite database with schema (Member, Holdings, Contributions, Valuations tables)
- âœ… Implement basic Models (Member, Holding, Contribution)
- âœ… Create DatabaseContext with Dapper ORM

**Week 3-4: Holdings Management**
- âœ… Build Holdings CRUD form (manual entry interface)
- âœ… Implement HoldingsRepository with basic queries
- âœ… Add sector classification dropdown (Banks, Resources, ETFs, Other)
- âœ… Create summary calculation service (total value, unrealized gain, allocation %)

**Week 5-6: CSV Import**
- âœ… Design ImportForm with drag-drop zone
- âœ… Implement CsvImportService with column mapping
- âœ… Add preview table to validate import before commit
- âœ… Handle edge cases (missing columns, invalid data, duplicates)

**Week 7-8: JSON Export & Integration**
- âœ… Implement JsonExportService with standardized schema (v1.0)
- âœ… Add "Export to Artifact" button to main form
- âœ… Test export → artifact import → visualization flow
- âœ… Document JSON schema for artifact developers

**Deliverables:**
- C# application can import CHESS CSV, store in SQLite, export to JSON
- Existing React artifact can import JSON and display portfolio
- User (John) can complete weekly workflow: update prices → export → analyze

---

**Phase 2: Transactions & Compliance (Weeks 9-12)**
*Goal: Track transactions and monitor contribution caps*

**Week 9: Transaction Logging**
- âœ… Create Transaction model and database table
- âœ… Build TransactionForm for manual entry (BUY, SELL, DIVIDEND types)
- âœ… Link transactions to holdings (foreign key relationship)

**Week 10: Contribution Tracking**
- âœ… Create Contribution model and database table
- âœ… Build ContributionForm with FY selector and type dropdown
- âœ… Implement cap calculation logic (concessional $30k, NCC $120k)
- âœ… Add cap usage gauges to main dashboard

**Week 11: Carry-Forward & Bring-Forward**
- âœ… Implement carry-forward calculation (5-year lookback, TSB < $500k check)
- âœ… Implement bring-forward eligibility (3-year rule, TSB thresholds)
- âœ… Add alerts when approaching 90% of caps

**Week 12: Compliance Export**
- âœ… Include contribution data in JSON export
- âœ… Update artifact to display compliance dashboard
- âœ… Test end-to-end compliance workflow

**Deliverables:**
- Transaction history logged with CGT event flagging
- Contribution caps tracked with real-time alerts
- Artifact compliance dashboard shows cap usage and carry-forward availability

---

**Phase 3: Reporting & Backup (Weeks 13-16)**
*Goal: Generate reports and enable data backup/restore*

**Week 13-14: PDF Reports**
- âœ… Set up QuestPDF or iTextSharp library
- âœ… Create Portfolio Summary report (holdings, allocation, performance)
- âœ… Create Performance Report (monthly/quarterly returns, benchmarking)
- âœ… Add "Generate Report" button to main menu

**Week 15: Backup & Restore**
- âœ… Implement full database export to ZIP (SQLite file + metadata JSON)
- âœ… Implement restore from ZIP with version checking
- âœ… Add "Backup Now" and "Restore Backup" to File menu

**Week 16: Excel Export**
- âœ… Set up EPPlus or ClosedXML library
- âœ… Create Holdings export (code, units, prices, gains)
- âœ… Create Transactions export (filtered by date range)
- âœ… Test compatibility with Excel/LibreOffice Calc

**Deliverables:**
- PDF reports for portfolio summary and performance
- Backup/restore functionality for disaster recovery
- Excel exports for accountant/auditor handoff

---

**Phase 4: Advanced Planning (Weeks 17-20)**
*Goal: Enhance artifact with scenario modeling and AI insights*

**Week 17: Scenario Builder**
- âœ… Add "Scenarios" tab to artifact
- âœ… Create scenario builder UI (name, assumptions, deployment schedule)
- âœ… Save multiple scenarios to window.storage
- âœ… Compare scenarios side-by-side in table/chart

**Week 18-19: AI Insights Integration**
- âœ… Design Claude conversation interface alongside artifact
- âœ… Implement context passing (artifact state → Claude)
- âœ… Create prompt templates for common questions:
  - "Should I sell [CODE]?"
  - "What's the tax impact of [action]?"
  - "How does my allocation compare to [benchmark]?"
- âœ… Test natural language interaction flow

**Week 20: Monte Carlo Simulation**
- âœ… Implement Monte Carlo projection engine (1,000 runs)
- âœ… Display probability distribution chart
- âœ… Show percentile outcomes (10th, 50th, 90th)
- âœ… Highlight success probability for $2M target

**Deliverables:**
- Scenario builder for "what-if" analysis
- AI-powered insights via Claude conversation
- Monte Carlo simulation for probabilistic projections

---

**Phase 5: Automation & Polish (Weeks 21-24)**
*Goal: Add automated price feeds and final UX improvements*

**Week 21: Price Feed Integration**
- âœ… Sign up for Alpha Vantage free tier API key
- âœ… Implement PriceService with API calls for ASX stocks
- âœ… Add "Auto-Update Prices" button with progress indicator
- âœ… Handle rate limiting (5 calls/minute) with queue

**Week 22: Transaction Import**
- âœ… Extend CSV import to handle transaction history from broker
- âœ… Map transaction types (BUY, SELL, DIVIDEND) from CSV columns
- âœ… Validate against existing holdings to prevent duplicates

**Week 23: UX Polish**
- âœ… Improve main dashboard layout with responsive design
- âœ… Add keyboard shortcuts (Ctrl+I, Ctrl+E, Ctrl+R)
- âœ… Implement dark mode toggle (optional)
- âœ… Add tooltips and help text for complex fields

**Week 24: Testing & Documentation**
- âœ… Perform end-to-end testing with John's real data
- âœ… Write user manual (setup, import, export, workflows)
- âœ… Create troubleshooting guide (common issues, solutions)
- âœ… Package installer with database schema included

**Deliverables:**
- Automated price updates from Alpha Vantage API
- Transaction history import from broker statements
- Polished UX with keyboard shortcuts and help text
- Complete user manual and installer package

---

## 10. User Stories

### 10.1. Initial Portfolio Setup via CHESS Import
- **ID**: US-001
- **Priority**: HIGH (Phase 1)
- **Description**: As John (SMSF trustee), I want to import my share holdings from a CHESS statement CSV so that I don't have to manually enter 13 holdings with purchase dates and prices.
- **Acceptance criteria**:
  - [ ] User can click "Import CHESS Statement" button on main form
  - [ ] User can drag-and-drop CSV file or browse to select file
  - [ ] Application parses CSV and displays preview table with columns: Code, Units, Purchase Price, Current Price, Sector
  - [ ] User can review preview and correct any mismatched data before committing
  - [ ] User can click "Confirm Import" to insert holdings into SQLite database
  - [ ] Application detects duplicate codes and prompts user to update or skip
  - [ ] After import, main dashboard shows updated total value and allocation
  - [ ] Application logs import timestamp and filename for audit trail
- **Edge cases**:
  - CSV has unexpected column headers → Application shows error message with expected format
  - CSV contains non-ASX code (e.g., US stock) → Application flags for manual review
  - CSV has missing prices → Application prompts user to enter current price manually

### 10.2. Weekly Price Update
- **ID**: US-002
- **Priority**: HIGH (Phase 1)
- **Description**: As John, I want to quickly update current prices for all my holdings so that my portfolio value is accurate for this week's analysis.
- **Acceptance criteria**:
  - [ ] User can click "Update Prices" button on main form
  - [ ] Application displays price update form with one row per holding: Code, Last Price, Last Updated, New Price (editable)
  - [ ] User can tab through "New Price" fields and enter values from Westpac Broking or Google Finance
  - [ ] Application validates that new price is within 20% of last price (if not, shows confirmation prompt)
  - [ ] User can click "Save All" to commit updates to database
  - [ ] Application recalculates total value, unrealized gains, and allocation % in real-time
  - [ ] Main dashboard reflects updated values immediately
  - [ ] Application records last updated timestamp for each holding
- **Edge cases**:
  - User enters invalid price (negative or non-numeric) → Show inline error and prevent save
  - User enters price > 20% change → Show confirmation dialog: "ANZ price changed from $36.03 to $45.00 (+24.9%). Confirm?"
  - User closes form without saving → Prompt "Discard changes?"

### 10.3. Export Portfolio to Artifact
- **ID**: US-003
- **Priority**: HIGH (Phase 1)
- **Description**: As John, I want to export my complete portfolio data to a JSON file so that I can import it into the Claude artifact for analysis and projections.
- **Acceptance criteria**:
  - [ ] User can click "Export to Artifact" button on main toolbar
  - [ ] Application generates JSON file with schema version 1.0 including:
    - Member details (name, DOB, target retirement age, target balance, floor)
    - All holdings (code, units, purchase price/date, current price, value, gain, sector)
    - Cash and fixed income balances
    - Contribution summary (FY, caps, usage)
    - Assumptions (annual return, contribution amount, inflation rate)
  - [ ] Application saves JSON to desktop with filename: `smsf_portfolio_YYYYMMDD.json`
  - [ ] Application displays success message: "Portfolio exported to [filepath]. Upload this file to your Claude artifact."
  - [ ] JSON is valid (can be parsed by standard JSON validator)
  - [ ] JSON is human-readable (formatted with indentation)
- **Edge cases**:
  - Desktop folder not accessible → Save to Documents folder instead and notify user
  - File already exists → Append timestamp: `smsf_portfolio_20251225_143022.json`

### 10.4. Import Portfolio into Artifact
- **ID**: US-004
- **Priority**: HIGH (Phase 1, Artifact)
- **Description**: As John, I want to import my portfolio JSON into the Claude artifact so that I can see my current position and projections.
- **Acceptance criteria**:
  - [ ] User can click "Import Portfolio Data" button in artifact
  - [ ] User can select JSON file via file browser or drag-and-drop
  - [ ] Artifact validates JSON schema version (shows error if incompatible)
  - [ ] Artifact parses JSON and extracts member, holdings, contributions, assumptions
  - [ ] Artifact displays confirmation: "Loaded portfolio: 13 holdings, $609,819 total value. Last updated: 2025-12-25."
  - [ ] Portfolio dashboard updates with imported data (allocation charts, holdings table, total value)
  - [ ] Projections tab recalculates using imported assumptions and current balance
  - [ ] Compliance tab shows contribution cap usage from imported data
  - [ ] Artifact saves imported state to window.storage for persistence
- **Edge cases**:
  - JSON file is malformed → Show error: "Invalid JSON format. Please export again from C# app."
  - JSON schema version mismatch → Show warning: "This file was exported from an older version. Some features may not work. Upgrade recommended."
  - File size > 5MB → Show error: "File too large for browser storage. Please contact support."

### 10.5. View 7-Year Projection Scenarios
- **ID**: US-005
- **Priority**: HIGH (Phase 1, Artifact)
- **Description**: As John, I want to see projections of my SMSF balance at age 60 under different return scenarios so that I can assess whether I'm on track to hit $2M.
- **Acceptance criteria**:
  - [ ] User can click "Projections" tab in artifact
  - [ ] Artifact displays line chart with X-axis = Age (53-60), Y-axis = Balance ($0-$2.5M)
  - [ ] Chart shows 4 scenarios: Conservative (7%), Base Case (10%), Optimistic (14%), Best Case (17%)
  - [ ] Chart includes reference lines: Target ($2M, red dashed), Floor ($1M, orange dashed)
  - [ ] Chart legend shows final balance for each scenario at age 60
  - [ ] Below chart, scenario summary table shows:
    - Scenario name | Annual return % | Age 60 balance | vs Target | Probability
  - [ ] Scenarios that hit target show green âœ… indicator, below show red âœ— indicator
  - [ ] Probability assessment displays: "60% chance of reaching $1.5M+"
- **Edge cases**:
  - Current balance already exceeds $2M → Chart adjusts Y-axis max to current balance + 20%
  - User is already 60+ years old → Show message: "You've reached retirement age. Switch to pension phase planning."

### 10.6. Adjust Projection Assumptions
- **ID**: US-006
- **Priority**: MEDIUM (Phase 1, Artifact)
- **Description**: As John, I want to adjust projection assumptions (annual return %, contribution amount) so that I can model different strategies.
- **Acceptance criteria**:
  - [ ] User can see "Assumptions" section below projection chart with sliders:
    - Base Annual Return (%): Range 5-20%, default 10%, step 0.5%
    - Annual Contribution ($): Range 0-50000, default 25500, step 1000
    - Conservative Return (%): Range 3-12%, default 7%, step 0.5%
    - Optimistic Return (%): Range 10-25%, default 14%, step 0.5%
  - [ ] User can drag sliders or click +/- buttons to adjust values
  - [ ] Projection chart updates in real-time (< 100ms) when user changes slider
  - [ ] Current slider values display next to slider (e.g., "10.0%", "$25,500")
  - [ ] Artifact saves adjusted assumptions to window.storage
  - [ ] On next artifact load, assumptions restore from storage
- **Edge cases**:
  - User sets Conservative > Base > Optimistic (illogical ordering) → No validation, allow user flexibility
  - User sets annual contribution > $180k (unrealistic for $140k income) → No validation, advanced users may have external sources

### 10.7. Track Contribution Caps
- **ID**: US-007
- **Priority**: HIGH (Phase 2)
- **Description**: As John, I want to see my concessional and non-concessional contribution usage against FY caps so that I don't accidentally exceed limits and incur penalties.
- **Acceptance criteria**:
  - [ ] User can click "Compliance" tab in artifact (after Phase 2 export includes contribution data)
  - [ ] Artifact displays two progress bars:
    - Concessional: $18,000 / $30,000 (60% used, $12,000 remaining)
    - Non-Concessional: $0 / $120,000 (0% used, $120,000 remaining)
  - [ ] Progress bars color-coded: Green (< 75%), Orange (75-90%), Red (> 90%)
  - [ ] Below progress bars, display:
    - "Carry-forward available: $60,000 (from FY 2020-21 to FY 2024-25)"
    - "Bring-forward eligible: Yes (3-year bring-forward available, TSB $609k < $1.76M)"
  - [ ] If user exceeds cap in C# app, artifact shows alert: "âš  Warning: Concessional cap exceeded by $2,000. Excess taxed at marginal rate."
- **Edge cases**:
  - User has no carry-forward (used full cap every year for 5 years) → Display: "No carry-forward available"
  - User TSB exceeds $2M → Display: "Non-concessional contributions not allowed (TSB >= $2M)"

### 10.8. Manual Transaction Entry
- **ID**: US-008
- **Priority**: MEDIUM (Phase 2)
- **Description**: As John, I want to manually record a BUY transaction so that my cost base is accurate for CGT calculation.
- **Acceptance criteria**:
  - [ ] User can click "Transactions" button on main form
  - [ ] User can click "Add Transaction" button
  - [ ] Transaction form displays fields:
    - Holding: Dropdown of existing holdings (or "Add New Holding")
    - Type: Dropdown (BUY, SELL, DIVIDEND, DISTRIBUTION, DRP, CORPORATE_ACTION)
    - Date: Date picker
    - Units: Decimal (4 places)
    - Price: Decimal (4 places)
    - Brokerage/Fees: Decimal (2 places)
    - Notes: Text area (optional)
  - [ ] User can enter values and click "Save"
  - [ ] Application validates that date is not in future
  - [ ] Application validates that units > 0 for BUY, units < 0 for SELL
  - [ ] Application updates holding cost base for BUY transactions
  - [ ] Application records transaction in database with timestamp
  - [ ] Transaction appears in transaction history grid
- **Edge cases**:
  - User enters BUY transaction for holding not yet in database → Prompt to create holding first or auto-create with transaction details
  - User enters SELL transaction with units > current holding → Show error: "Cannot sell 1000 units of ANZ. You only have 1684 units."

### 10.9. Calculate CGT on Sale
- **ID**: US-009
- **Priority**: MEDIUM (Phase 2)
- **Description**: As John, I want to see the estimated CGT liability when I'm considering selling a holding so that I can make an informed decision.
- **Acceptance criteria**:
  - [ ] User can right-click on holding in holdings grid and select "Calculate CGT"
  - [ ] CGT calculator dialog displays:
    - Holding: ANZ (1684 units @ $36.03 = $60,674)
    - Cost base: $30,248 (1684 units @ $17.96)
    - Holding period: 5 years 3 months (> 12 months, eligible for discount)
    - Units to sell: Editable field (default 100% = 1684 units)
    - Sale price: Editable field (default current price $36.03)
  - [ ] User can enter "Units to sell" (e.g., 842 = 50%)
  - [ ] Application calculates:
    - Sale proceeds: $30,337 (842 Ã— $36.03)
    - Cost base (FIFO): $15,124 (842 Ã— $17.96)
    - Capital gain: $15,213
    - CGT (10% discount): $1,521
    - Net proceeds after tax: $28,816
  - [ ] Calculator displays breakdown table with values
  - [ ] User can click "Apply to Transaction" to create SELL transaction (pre-filled)
- **Edge cases**:
  - Holding period < 12 months → CGT rate 15% (no discount), calculator shows warning
  - User has multiple parcels with different purchase dates → Calculator uses FIFO by default, shows "Change to LIFO or Specific" option (Phase 3 feature)

### 10.10. Identify Plenti Maturity and Deployment
- **ID**: US-010
- **Priority**: MEDIUM (Phase 3, Artifact Scenarios)
- **Description**: As John, I want to model what happens when my Plenti Notes mature in 2026-2027 and I deploy that capital into geared ETFs so that I can see the impact on my age 60 projection.
- **Acceptance criteria**:
  - [ ] User can click "Scenarios" tab in artifact
  - [ ] User can click "New Scenario" button
  - [ ] Scenario builder form displays:
    - Scenario name: Text field (e.g., "Deploy Plenti to GEAR")
    - Deployment event: Checkbox "Plenti matures" with date picker (default: July 2026)
    - Amount to deploy: Auto-filled $137,000 (from Plenti balance)
    - Target allocation: Dropdown (GEAR, GGUS, VAS, WDS, Other)
    - Expected return for target: Editable % (default based on selection)
  - [ ] User selects "GEAR" and sets expected return to 14%
  - [ ] User clicks "Save Scenario"
  - [ ] Artifact recalculates projection with new assumption:
    - Plenti earns 9% until July 2026
    - $137k deploys to GEAR in July 2026
    - GEAR earns 14% from July 2026 to Dec 2032
  - [ ] Projection chart shows new "Plenti→GEAR" scenario line alongside base scenarios
  - [ ] Scenario summary table shows: Base Case ($1.41M) vs Plenti→GEAR ($1.58M) vs Target ($2.0M)
- **Edge cases**:
  - User sets deployment date in past → Show warning: "Deployment date is in the past. Use current date?"
  - User sets expected return > 30% → Show warning: "This return assumption is very aggressive. Are you sure?"

### 10.11. AI-Powered Portfolio Analysis
- **ID**: US-011
- **Priority**: MEDIUM (Phase 4)
- **Description**: As John, I want to ask Claude natural language questions about my portfolio so that I can get AI-powered insights without manually calculating.
- **Acceptance criteria**:
  - [ ] User can type question in chat interface alongside artifact: "Should I sell my MIN position?"
  - [ ] Claude receives context from artifact state (holdings, projections, assumptions)
  - [ ] Claude analyzes MIN holding:
    - Current: 893 units @ $52.65 = $47,016 value
    - Cost base: $16,824 (893 Ã— $18.82)
    - Unrealized gain: $30,193 (+179%)
    - Sector: Resources (contributes to 47.6% concentration)
  - [ ] Claude generates response:
    - "MIN has performed exceptionally well (+179%), but it represents 11.4% of your portfolio and contributes to your heavy Resources sector concentration (47.6%). Selling 50% would:
      - Lock in ~$15k gain (after ~$1,500 CGT)
      - Provide $22k to redeploy into diversified ETFs
      - Reduce Resources concentration from 47.6% to ~42%
    - Consider selling 50% to take profits and rebalance, while keeping 50% for further upside."
  - [ ] User can follow up: "What's the exact CGT calculation?"
  - [ ] Claude provides detailed breakdown (uses CGT calculator logic from US-009)
- **Edge cases**:
  - User asks question about holding not in portfolio → Claude responds: "I don't see [CODE] in your current holdings. Did you mean [similar code]?"
  - User asks about future event (e.g., "Will MIN keep going up?") → Claude clarifies: "I can't predict future prices, but I can analyze historical volatility and correlations if helpful."

### 10.12. Monte Carlo Simulation
- **ID**: US-012
- **Priority**: LOW (Phase 4, Advanced)
- **Description**: As John, I want to see a probability distribution of outcomes at age 60 so that I can understand the range of possible results, not just fixed scenarios.
- **Acceptance criteria**:
  - [ ] User can click "Monte Carlo" button in Projections tab
  - [ ] Artifact displays configuration:
    - Number of simulations: 1,000 (default, range 100-10,000)
    - Return distribution: Normal (mean = 10%, std dev = 15%)
    - Run simulations button
  - [ ] User clicks "Run Simulations"
  - [ ] Artifact executes 1,000 projections with randomized annual returns (sampled from normal distribution)
  - [ ] Progress indicator shows "Running simulation 347/1000..."
  - [ ] After completion, artifact displays:
    - Histogram of age 60 outcomes (X-axis = balance, Y-axis = frequency)
    - Percentile table:
      - 10th percentile: $980,000
      - 50th percentile (median): $1,420,000
      - 90th percentile: $2,050,000
    - Probability metrics:
      - P(balance >= $2M): 22%
      - P(balance >= $1.5M): 58%
      - P(balance >= $1M): 94%
  - [ ] Reference line on histogram shows $2M target
- **Edge cases**:
  - User runs 10,000 simulations → Browser may freeze; show warning: "Large simulations may take 10-20 seconds. Continue?"
  - User closes artifact mid-simulation → Simulation stops, no state saved

### 10.13. Automated Price Updates via API
- **ID**: US-013
- **Priority**: LOW (Phase 5)
- **Description**: As John, I want to click a button to automatically update all share prices from an API so that I don't have to manually enter 13 prices every week.
- **Acceptance criteria**:
  - [ ] User can enter Alpha Vantage API key in Settings menu (one-time setup)
  - [ ] User can click "Auto-Update Prices" button on main toolbar
  - [ ] Application displays progress: "Updating ANZ... 1/13"
  - [ ] Application calls Alpha Vantage API for each holding's ASX code (e.g., ANZ.AX)
  - [ ] Application respects rate limit (5 calls/minute) by queuing requests
  - [ ] Application updates current price and last updated timestamp for each holding
  - [ ] Application displays summary: "13/13 holdings updated successfully. 0 failed."
  - [ ] If API call fails (rate limit, network error), show error: "Failed to update MIN. Try again later."
  - [ ] User can see individual status in holdings grid: ANZ âœ… (2 mins ago), MIN âŒ (API error)
- **Edge cases**:
  - API key invalid → Show error: "Invalid API key. Check Settings."
  - API rate limit exceeded → Queue remaining requests and show "Waiting 60 seconds for rate limit reset..."
  - ASX code not found in Alpha Vantage → Show warning: "MVP not found in API. Enter price manually."

---

## 11. Next Steps

### 11.1 Immediate Actions (Next 7 Days)
- **Dec 25-26**: Review this PRD with John for feedback and approval
- **Dec 27-28**: Finalize React artifact polish (minor UX improvements, export/import edge cases)
- **Dec 29-31**: Begin Phase 1 C# project setup (Visual Studio solution, SQLite schema, basic models)

### 11.2 Technical Review Requirements
- **SMSF Accountant Consultation**: Review contribution cap logic, CGT calculation rules, pension phase requirements
  - Schedule: Before Phase 2 implementation (Week 9)
  - Deliverable: Validated compliance rules document
- **Beta Testing**: Recruit 1-2 SMSF trustees to test C# app import process and provide UX feedback
  - Schedule: After Phase 1 MVP (Week 8)
  - Deliverable: Bug reports and feature requests

### 11.3 Stakeholder Approval
- **John (Primary User)**: Approve PRD, phase priorities, and UI mockups
  - Deadline: December 28, 2025
  - Decision: Proceed with Phase 1 or adjust scope
- **Claude (AI Development Partner)**: Confirm technical feasibility and provide code generation support
  - Ongoing throughout project

### 11.4 Development Planning
- **Sprint Structure**: 2-week sprints aligned with phase milestones
- **Velocity Assumption**: 10-15 hours/week (John's availability)
- **Code Review**: AI-assisted review via Claude for each component before commit
- **Testing Strategy**: Manual testing by John after each sprint, automated unit tests for critical calculations (CGT, projections)

### 11.5 Dependencies
- **External**: 
  - Alpha Vantage API availability (Phase 5) - Free tier sufficient
  - Windows 10/11 desktop environment for C# app
- **Internal**:
  - Claude artifact must be accessible via Claude.ai project
  - window.storage API must remain stable in browser
- **User**:
  - John must provide real CHESS statement CSV for testing import
  - John must validate compliance logic against accountant/ATO resources

### 11.6 Risk Mitigation
- **Risk**: John's availability drops below 10 hours/week
  - Mitigation: Extend timeline or reduce scope (defer Phase 4/5 to future versions)
- **Risk**: Browser storage API changes or artifact hosting becomes unavailable
  - Mitigation: Maintain offline JSON export/import as fallback
- **Risk**: ATO rules change (contribution caps, CGT rates, pension minimums)
  - Mitigation: Design configurable rules engine (editable via Settings, not hard-coded)

---

## Appendix

### A. Glossary

- **SMSF**: Self-Managed Super Fund - Australian retirement savings vehicle with member-trustees
- **TSB**: Total Superannuation Balance - aggregate balance across all super accounts
- **Concessional Contributions**: Pre-tax contributions (salary sacrifice, employer SG, personal deductible)
- **Non-Concessional Contributions**: After-tax contributions
- **Carry-Forward**: Ability to use unused concessional cap from previous 5 years
- **Bring-Forward**: Ability to contribute 3 years of non-concessional cap in one year
- **Preservation Age**: Age at which super can be accessed (56-60 depending on DOB)
- **CGT**: Capital Gains Tax - 15% in accumulation phase (10% if held > 12 months), 0% in pension phase
- **CHESS**: Clearing House Electronic Subregister System - ASX's settlement system
- **DRP**: Dividend Reinvestment Plan - automatic reinvestment of dividends to buy more shares
- **TTR**: Transition to Retirement - pension while still working (after preservation age)
- **LRBA**: Limited Recourse Borrowing Arrangement - SMSF property loan structure
- **GEAR**: Betashares Geared Australian Equity Fund - 2x leveraged ASX 200 ETF
- **GGUS**: Betashares Geared US Equity Fund - 2x leveraged S&P 500 ETF

### B. Reference Documents

- SMSF_SYSTEM_FEATURES.md - Comprehensive feature requirements research
- ARCHITECTURE.md - System architecture and data model design
- SMSFPortfolioManager.jsx - React artifact source code (current version)
- smsf_aggressive_plan_revised_dec_2025.md - John's retirement plan with projections
- ATO SMSF Compliance Guidelines (2025-26) - https://www.ato.gov.au/super/self-managed-super-funds

### C. Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 25-Dec-2025 | Claude | Initial PRD creation covering MVP to Phase 5 |

---

**Document Status**: âœ… Ready for Review  
**Next Milestone**: John approval by December 28, 2025  
**Project Start**: January 2, 2026 (Phase 1, Week 1)

---

*End of Product Requirements Document*
---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: John's Notes/Personal Finance Orig/prd-smsf-portfolio-manager.md
