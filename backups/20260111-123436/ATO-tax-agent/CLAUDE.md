# ATO Tax Agent - Tax Return Assistance Application

**Type**: Web Application
**Status**: Implementation
**Project ID**: `9fd54603-8f6d-407d-8404-43c3ff2f36dd`
**Identity**: `claude-ato-tax-agent` (`49699105-dd58-460a-817a-06a30f6f3a17`)

---

## Problem Statement

Enable Australian individuals to complete their tax returns accurately with:
- Step-by-step guidance based on pure ATO rules (no AI hallucination)
- AI-assisted prompts for maximizing deductions (within bounds)
- Document analysis for extracting tax-relevant information
- Compliance with Australian tax regulations and ATO requirements

**Full details**: See `ARCHITECTURE.md`

---

## Current Phase

**Phase**: Implementation
**Focus**: Building two-layer system (Guided Process + AI Assistant)
**Progress**: 75% complete (103 database records, awaiting 4th PDF)

---

## Architecture Overview

### Two-Layer System

**Layer 1: Guided Process** (No AI)
- Binary decision tree from ATO rules
- Pure YES/NO navigation
- ATO content lookup from database
- Progress tracking

**Layer 2: AI Assistant** (Bounded AI)
- Helpful prompts for deductions
- Document analysis (bank statements, payslips)
- Year-end tax advice
- NO financial advice, stays in lane

**Tech Stack**:
- **Backend**: Python (FastAPI/Flask) + PostgreSQL
- **Frontend**: React + Node.js
- **Database**: PostgreSQL (`ai_company_foundation` schema)
- **Deployment**: TBD

**Full details**: See `ARCHITECTURE.md`

---

## Project Structure

```
ATO-Tax-Agent/
├── CLAUDE.md              # This file - AI constitution
├── ARCHITECTURE.md        # System design
├── backend/
│   ├── requirements.txt   # Python dependencies
│   └── ...                # API, database, services
├── frontend/
│   ├── package.json       # Node.js dependencies
│   └── ...                # React components, UI
├── docs/                  # Analysis artifacts, summaries
├── tests/                 # Test suites
└── analyze-*.js           # Section analysis scripts
```

---

## Domain Expertise

As `claude-ato-tax-agent`, you are a **specialist in**:
- 🇦🇺 **Australian tax law and regulations**
- 📋 **ATO Individual Tax Return forms and schedules**
- 💼 **Tax deductions, offsets, and thresholds**
- 📊 **Tax return sections and cross-references**
- ✅ **Compliance requirements and evidence thresholds**
- 🤖 **Bounded AI assistance (no financial advice)**

---

## Coding Standards (Auto-Loaded)

@~/.claude/standards/core/markdown-documentation.md
@~/.claude/standards/language/typescript.md
@~/.claude/standards/pattern/security-aspnet.md
@~/.claude/standards/pattern/docker.md
@~/.claude/standards/pattern/github-actions.md

---

## Project-Specific Coding Standards

### Python (Backend)
- **Style**: PEP 8, type hints for public APIs
- **Framework**: FastAPI preferred (async support)
- **Database**: Use SQLAlchemy or psycopg3
- **Testing**: pytest with fixtures
- **Validation**: Pydantic models for API schemas

### JavaScript/React (Frontend)
- **Style**: ESLint + Prettier
- **Framework**: React functional components + hooks
- **State**: Context API or Redux Toolkit
- **Styling**: Tailwind CSS or Material-UI
- **Testing**: Jest + React Testing Library

### Database
- **Schema**: Use appropriate schema (not `claude` schema)
- **Migrations**: Alembic (Python) or custom migration scripts
- **Queries**: Parameterized to prevent SQL injection
- **Indexes**: Add for frequently queried columns

---

## Key Data Sources

### Tax Return Tables (103 records)
- `tax_return_binary_gates` (19) - YES/NO decision points
- `tax_return_conditional_flows` (6) - Section navigation logic
- `tax_return_cross_references` (6) - Related sections
- `tax_return_evidence_thresholds` (13) - Documentation requirements
- `tax_return_instructional_content` (PENDING - 4th PDF)

### ATO Compliance
- **Thresholds**: $300 substantiation limit
- **Sections**: 1-24 (income, deductions, offsets, Medicare)
- **Schedules**: D1-D15 (work-related, rental, CGT, etc.)

---

## Work Tracking

| I have... | Put it in... | How |
|-----------|--------------|-----|
| A bug | claude.feedback | type='bug', project_id='9fd54603...' |
| A feature idea | claude.features | link to project |
| A task to do | claude.build_tasks | link to feature |
| Work right now | TodoWrite | session only |

**Data Gateway**: Before writing to `claude.*` tables, check `claude.column_registry` for valid values.

---

## Key Procedures

1. **Session Start**: Run `/session-start` (auto-logs with `claude-ato-tax-agent` identity)
2. **Session End**: Run `/session-end` (saves summary)
3. **Tax Law Changes**: Document in knowledge vault under `10-Projects/ato-tax-agent/`
4. **ATO Updates**: Track in feedback system with `type='change'`

**SOPs**: See `docs/` folder (if created)

---

## Domain-Specific Rules

### What AI CAN Do
✅ Prompt questions about deductions ("Did you work from home?")
✅ Analyze documents (bank statements, payslips) to extract data
✅ Explain ATO rules and thresholds from database
✅ Suggest sections to complete based on user profile
✅ Provide year-end tax planning advice (general)

### What AI CANNOT Do
❌ Give specific financial advice ("You should claim $X")
❌ Hallucinate tax rules (all rules from database/ATO content)
❌ Guarantee outcomes ("You'll get a refund of $Y")
❌ Bypass ATO compliance requirements
❌ Access user's actual ATO account or lodge returns

### Compliance Boundaries
- **No hallucination**: All tax rules from verified ATO sources
- **No financial advice**: Stay within tax information bounds
- **No guarantees**: Avoid promises about refunds or outcomes
- **Cite sources**: Reference ATO documents and sections
- **Evidence requirements**: Prompt for receipts when needed

---

## Testing Strategy

### Backend Tests
- Unit tests for tax calculation logic
- Integration tests for database queries
- API endpoint tests with FastAPI TestClient
- Validation tests for ATO rules compliance

### Frontend Tests
- Component tests for React UI
- Integration tests for user flows
- Accessibility tests (WCAG AA)
- Cross-browser compatibility

### Tax Logic Validation
- Test against known ATO examples
- Edge case testing (thresholds, limits)
- Cross-reference validation between sections
- Regression testing for tax law changes

---

## Australian Tax Context

### Financial Year
- **FY 2023-24**: July 1, 2023 - June 30, 2024
- **Lodgment**: October 31 (individuals), May 15 (agents)

### Common Deductions
- **Work-related expenses**: D1-D5 (car, travel, clothing, self-education)
- **Home office**: $0.67/hour method or actual costs
- **Investment**: D7-D15 (rental, dividends, CGT)

### Thresholds
- **$300 rule**: Substantiation not required under $300
- **Low income offset**: Up to $700 (income < $66,667)
- **Medicare levy**: 2% (exemptions available)

---

## Quick Queries

```sql
-- Check project status
SELECT * FROM claude.projects WHERE project_name = 'ATO-Tax-Agent';

-- Recent sessions for this project
SELECT session_start, summary FROM claude.sessions
WHERE project_name = 'ATO-Tax-Agent'
ORDER BY session_start DESC LIMIT 5;

-- Tax return data completeness
SELECT COUNT(*) FROM tax_return_binary_gates;
SELECT COUNT(*) FROM tax_return_conditional_flows;
SELECT COUNT(*) FROM tax_return_evidence_thresholds;
```

---

## Knowledge Vault

Tax-specific knowledge should be captured in:
- `knowledge-vault/10-Projects/ato-tax-agent/` - Project-specific patterns
- `knowledge-vault/20-Domains/ATO/` - Australian tax law domain knowledge
- `knowledge-vault/30-Patterns/` - Reusable tax calculation patterns

**Sync**: Run `python scripts/sync_obsidian_to_db.py` after creating vault docs

---

## Recent Changes

| Date | Change |
|------|--------|
| 2025-12-26 | **CLAUDE.md created**: Identity-per-project system, domain expertise documented |
| 2025-10-19 | **Two-layer architecture**: Guided process + AI assistant defined |
| 2025-XX-XX | **Database schema**: 103 tax return records created |

**Full changelog**: See git log or `docs/CHANGELOG.md`

---

## Related Projects

- **claude-family**: Infrastructure for Claude coordination
- **nimbus-import/nimbus-user-loader**: WFM data integration (different domain)
- **claude-family-manager-v2**: Launcher for this project

---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: C:\Projects\ATO-Tax-Agent\CLAUDE.md
