---
tags:
- database
projects: []
---
# Personal Finance System - Database Schema
## PostgreSQL Schema Design
**Version:** 1.0  
**Date:** 26 December 2025  
**Database:** PostgreSQL 14+

---

## Overview

This schema supports a comprehensive personal finance system with specialized SMSF tracking. All monetary values stored as DECIMAL(12,2) for precision. All timestamps in UTC.

---

## Core Financial Tables

### accounts
Stores all financial accounts (bank, credit cards, loans, investments, SMSF)

```sql
CREATE TABLE accounts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    account_type VARCHAR(50) NOT NULL, -- checking, savings, credit_card, loan, investment, smsf, crypto
    institution VARCHAR(100),
    account_number VARCHAR(50),
    bsb VARCHAR(10),
    balance DECIMAL(12,2) DEFAULT 0.00,
    currency VARCHAR(3) DEFAULT 'AUD',
    is_active BOOLEAN DEFAULT TRUE,
    is_smsf BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT check_account_type CHECK (account_type IN (
        'checking', 'savings', 'credit_card', 'loan', 
        'investment', 'smsf', 'crypto', 'property'
    ))
);

CREATE INDEX idx_accounts_active ON accounts(is_active);
CREATE INDEX idx_accounts_type ON accounts(account_type);
CREATE INDEX idx_accounts_smsf ON accounts(is_smsf) WHERE is_smsf = TRUE;
```

### transactions
All financial transactions across all accounts

```sql
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    transaction_date DATE NOT NULL,
    posted_date DATE,
    description TEXT NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    balance_after DECIMAL(12,2),
    
    -- Categorization
    category_id INTEGER REFERENCES categories(id),
    merchant_name VARCHAR(200),
    is_categorized BOOLEAN DEFAULT FALSE,
    categorization_confidence DECIMAL(3,2), -- 0.00 to 1.00
    
    -- Metadata
    transaction_type VARCHAR(20), -- debit, credit, transfer
    reference_number VARCHAR(100),
    notes TEXT,
    
    -- Import tracking
    source VARCHAR(50), -- cdr, csv_import, manual
    import_batch_id UUID,
    external_id VARCHAR(100), -- ID from bank/CDR for deduplication
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT check_transaction_type CHECK (transaction_type IN ('debit', 'credit', 'transfer'))
);

CREATE INDEX idx_transactions_account ON transactions(account_id);
CREATE INDEX idx_transactions_date ON transactions(transaction_date);
CREATE INDEX idx_transactions_category ON transactions(category_id);
CREATE INDEX idx_transactions_merchant ON transactions(merchant_name);
CREATE INDEX idx_transactions_external ON transactions(external_id);
CREATE UNIQUE INDEX idx_transactions_unique ON transactions(account_id, external_id) 
    WHERE external_id IS NOT NULL; -- Prevent duplicate imports
```

### categories
Hierarchical category structure for transaction classification

```sql
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    parent_category_id INTEGER REFERENCES categories(id),
    category_type VARCHAR(20) NOT NULL, -- income, expense, transfer
    icon VARCHAR(50),
    color VARCHAR(7), -- Hex color code
    is_system BOOLEAN DEFAULT FALSE, -- System categories can't be deleted
    display_order INTEGER DEFAULT 0,
    
    CONSTRAINT check_category_type CHECK (category_type IN ('income', 'expense', 'transfer'))
);

CREATE INDEX idx_categories_parent ON categories(parent_category_id);
CREATE INDEX idx_categories_type ON categories(category_type);

-- Example categories
INSERT INTO categories (name, category_type, is_system) VALUES
    ('Income', 'income', TRUE),
    ('Salary', 'income', TRUE),
    ('Investment Income', 'income', TRUE),
    
    ('Housing', 'expense', TRUE),
    ('Groceries', 'expense', TRUE),
    ('Dining Out', 'expense', TRUE),
    ('Transport', 'expense', TRUE),
    ('Entertainment', 'expense', TRUE),
    ('Healthcare', 'expense', TRUE),
    ('Utilities', 'expense', TRUE),
    
    ('Transfer', 'transfer', TRUE);
```

### merchants
Merchant database for improved categorization

```sql
CREATE TABLE merchants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    normalized_name VARCHAR(200) NOT NULL, -- Cleaned/standardized name
    default_category_id INTEGER REFERENCES categories(id),
    website VARCHAR(200),
    
    -- For fuzzy matching
    name_variations TEXT[], -- Array of known name variations
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_merchants_normalized ON merchants(normalized_name);
CREATE INDEX idx_merchants_name_gin ON merchants USING gin(name_variations);
```

---

## Categorization & AI Tables

### categorization_rules
User-defined rules for auto-categorization

```sql
CREATE TABLE categorization_rules (
    id SERIAL PRIMARY KEY,
    rule_name VARCHAR(100),
    match_type VARCHAR(20) NOT NULL, -- exact, contains, starts_with, regex
    match_pattern TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    merchant_id INTEGER REFERENCES merchants(id),
    priority INTEGER DEFAULT 0, -- Higher priority rules run first
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT check_match_type CHECK (match_type IN ('exact', 'contains', 'starts_with', 'regex'))
);

CREATE INDEX idx_rules_active ON categorization_rules(is_active, priority DESC);
```

### categorization_history
Track AI categorization decisions for learning

```sql
CREATE TABLE categorization_history (
    id SERIAL PRIMARY KEY,
    transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    suggested_category_id INTEGER REFERENCES categories(id),
    confidence_score DECIMAL(3,2),
    model_version VARCHAR(50), -- e.g., "claude-haiku-20250514"
    reasoning TEXT, -- Why this category was suggested
    
    -- User feedback
    was_accepted BOOLEAN,
    user_corrected_category_id INTEGER REFERENCES categories(id),
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_cat_history_transaction ON categorization_history(transaction_id);
CREATE INDEX idx_cat_history_accepted ON categorization_history(was_accepted);
```

---

## Bills & Subscriptions

### recurring_transactions
Track bills, subscriptions, and recurring expenses

```sql
CREATE TABLE recurring_transactions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL, -- "Netflix", "Electricity Bill"
    merchant_id INTEGER REFERENCES merchants(id),
    category_id INTEGER REFERENCES categories(id),
    
    -- Amount tracking
    current_amount DECIMAL(12,2),
    historical_amounts JSONB, -- Track price changes: [{"date":"2024-01","amount":15.99}]
    
    -- Frequency
    frequency VARCHAR(20) NOT NULL, -- monthly, quarterly, annual, weekly
    next_due_date DATE,
    last_paid_date DATE,
    
    -- Detection
    is_confirmed BOOLEAN DEFAULT FALSE, -- User confirmed vs auto-detected
    detection_confidence DECIMAL(3,2),
    
    account_id INTEGER REFERENCES accounts(id),
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT check_frequency CHECK (frequency IN ('weekly', 'fortnightly', 'monthly', 'quarterly', 'annual'))
);

CREATE INDEX idx_recurring_active ON recurring_transactions(is_active);
CREATE INDEX idx_recurring_next_due ON recurring_transactions(next_due_date);
```

---

## Net Worth & Goals

### net_worth_snapshots
Historical net worth tracking

```sql
CREATE TABLE net_worth_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL UNIQUE,
    
    -- Assets
    total_assets DECIMAL(12,2) NOT NULL,
    liquid_assets DECIMAL(12,2), -- Cash + savings
    invested_assets DECIMAL(12,2), -- Shares, ETFs, etc.
    retirement_assets DECIMAL(12,2), -- SMSF
    property_assets DECIMAL(12,2),
    other_assets DECIMAL(12,2),
    
    -- Liabilities
    total_liabilities DECIMAL(12,2) NOT NULL,
    credit_card_debt DECIMAL(12,2),
    loan_debt DECIMAL(12,2),
    other_liabilities DECIMAL(12,2),
    
    -- Net Worth
    net_worth DECIMAL(12,2) GENERATED ALWAYS AS (total_assets - total_liabilities) STORED,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_networth_date ON net_worth_snapshots(snapshot_date DESC);
```

### financial_goals
Track savings and financial goals

```sql
CREATE TABLE financial_goals (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    goal_type VARCHAR(50), -- emergency_fund, house_deposit, retirement, vacation, other
    
    target_amount DECIMAL(12,2) NOT NULL,
    current_amount DECIMAL(12,2) DEFAULT 0.00,
    target_date DATE,
    
    linked_account_id INTEGER REFERENCES accounts(id),
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## SMSF Specific Tables

### smsf_members
SMSF member details

```sql
CREATE TABLE smsf_members (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    tax_file_number VARCHAR(20), -- Encrypted in production
    
    preservation_age INTEGER DEFAULT 56,
    target_retirement_age INTEGER,
    target_balance DECIMAL(12,2),
    floor_balance DECIMAL(12,2),
    
    is_trustee BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### smsf_holdings
SMSF investment holdings

```sql
CREATE TABLE smsf_holdings (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES smsf_members(id),
    
    code VARCHAR(10) NOT NULL, -- ASX code or identifier
    name VARCHAR(100),
    asset_type VARCHAR(50), -- shares, etf, fixed_income, property, cash
    sector VARCHAR(50),
    
    units DECIMAL(12,4) NOT NULL,
    purchase_price DECIMAL(10,4) NOT NULL,
    purchase_date DATE NOT NULL,
    current_price DECIMAL(10,4),
    
    -- Calculated fields
    cost_base DECIMAL(12,2),
    current_value DECIMAL(12,2),
    unrealised_gain DECIMAL(12,2),
    
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_smsf_holdings_member ON smsf_holdings(member_id);
CREATE INDEX idx_smsf_holdings_code ON smsf_holdings(code);
CREATE INDEX idx_smsf_holdings_active ON smsf_holdings(is_active);
```

### smsf_transactions
SMSF-specific transactions (buy, sell, dividend, etc.)

```sql
CREATE TABLE smsf_transactions (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES smsf_members(id),
    holding_id INTEGER REFERENCES smsf_holdings(id),
    
    transaction_date DATE NOT NULL,
    transaction_type VARCHAR(50) NOT NULL, -- buy, sell, dividend, distribution, drp, contribution, withdrawal
    
    units DECIMAL(12,4),
    price DECIMAL(10,4),
    amount DECIMAL(12,2) NOT NULL,
    fees DECIMAL(10,2) DEFAULT 0.00,
    
    -- Tax tracking
    franking_credit DECIMAL(10,2),
    franking_percentage DECIMAL(5,2),
    is_cgt_event BOOLEAN DEFAULT FALSE,
    
    notes TEXT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT check_smsf_transaction_type CHECK (transaction_type IN (
        'buy', 'sell', 'dividend', 'distribution', 'drp', 
        'contribution', 'withdrawal', 'transfer_in', 'transfer_out'
    ))
);

CREATE INDEX idx_smsf_trans_member ON smsf_transactions(member_id);
CREATE INDEX idx_smsf_trans_date ON smsf_transactions(transaction_date);
CREATE INDEX idx_smsf_trans_type ON smsf_transactions(transaction_type);
```

### smsf_contributions
Track SMSF contributions for cap monitoring

```sql
CREATE TABLE smsf_contributions (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES smsf_members(id),
    
    financial_year VARCHAR(7) NOT NULL, -- "2024-25"
    contribution_date DATE NOT NULL,
    contribution_type VARCHAR(50) NOT NULL, -- concessional, non_concessional, downsizer
    source VARCHAR(50), -- salary_sacrifice, employer, personal, spouse
    
    amount DECIMAL(12,2) NOT NULL,
    
    notes TEXT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT check_contribution_type CHECK (contribution_type IN (
        'concessional', 'non_concessional', 'downsizer'
    ))
);

CREATE INDEX idx_smsf_contrib_member ON smsf_contributions(member_id);
CREATE INDEX idx_smsf_contrib_fy ON smsf_contributions(financial_year);
CREATE INDEX idx_smsf_contrib_type ON smsf_contributions(contribution_type);
```

### smsf_compliance
Track compliance metrics by financial year

```sql
CREATE TABLE smsf_compliance (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES smsf_members(id),
    financial_year VARCHAR(7) NOT NULL UNIQUE,
    
    -- Contribution caps
    concessional_cap DECIMAL(12,2) DEFAULT 30000.00,
    concessional_used DECIMAL(12,2) DEFAULT 0.00,
    non_concessional_cap DECIMAL(12,2) DEFAULT 120000.00,
    non_concessional_used DECIMAL(12,2) DEFAULT 0.00,
    
    -- Carry-forward
    carry_forward_available DECIMAL(12,2) DEFAULT 0.00,
    bring_forward_eligible BOOLEAN DEFAULT TRUE,
    
    -- Balance tracking
    total_super_balance DECIMAL(12,2),
    transfer_balance_cap DECIMAL(12,2) DEFAULT 2000000.00,
    
    -- Pension phase (if applicable)
    minimum_pension_required DECIMAL(12,2),
    pension_paid_ytd DECIMAL(12,2) DEFAULT 0.00,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_smsf_compliance_member ON smsf_compliance(member_id);
CREATE INDEX idx_smsf_compliance_fy ON smsf_compliance(financial_year);
```

### smsf_documents
Document management for SMSF compliance

```sql
CREATE TABLE smsf_documents (
    id SERIAL PRIMARY KEY,
    member_id INTEGER REFERENCES smsf_members(id),
    
    document_type VARCHAR(50) NOT NULL, -- trust_deed, investment_strategy, minutes, statement, audit, etc.
    document_name VARCHAR(200) NOT NULL,
    financial_year VARCHAR(7),
    
    file_path TEXT NOT NULL, -- Path to stored document
    file_size_kb INTEGER,
    mime_type VARCHAR(100),
    
    upload_date DATE DEFAULT CURRENT_DATE,
    document_date DATE, -- Actual date of document
    
    tags TEXT[], -- For categorization and search
    notes TEXT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT check_smsf_document_type CHECK (document_type IN (
        'trust_deed', 'investment_strategy', 'minutes', 'member_statement',
        'financial_statement', 'audit_report', 'ato_correspondence', 
        'trade_confirmation', 'dividend_statement', 'other'
    ))
);

CREATE INDEX idx_smsf_docs_member ON smsf_documents(member_id);
CREATE INDEX idx_smsf_docs_type ON smsf_documents(document_type);
CREATE INDEX idx_smsf_docs_fy ON smsf_documents(financial_year);
CREATE INDEX idx_smsf_docs_tags_gin ON smsf_documents USING gin(tags);
```

---

## Import & Sync Tables

### import_batches
Track import operations for audit trail

```sql
CREATE TABLE import_batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    import_type VARCHAR(50) NOT NULL, -- cdr_sync, csv_import, manual
    source VARCHAR(100), -- "Westpac CDR", "Westpac CSV Export"
    
    records_imported INTEGER DEFAULT 0,
    records_skipped INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    
    status VARCHAR(20) DEFAULT 'in_progress', -- in_progress, completed, failed
    error_message TEXT,
    
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX idx_import_batches_date ON import_batches(started_at DESC);
```

### cdr_connections
Store CDR consent and connection details

```sql
CREATE TABLE cdr_connections (
    id SERIAL PRIMARY KEY,
    institution VARCHAR(100) NOT NULL,
    connection_status VARCHAR(20) DEFAULT 'active', -- active, expired, revoked
    
    consent_id VARCHAR(200), -- From CDR provider
    consent_expires_at TIMESTAMP,
    
    last_sync_at TIMESTAMP,
    sync_frequency_hours INTEGER DEFAULT 24,
    
    account_id INTEGER REFERENCES accounts(id),
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## AI & RAG Tables (using pgvector extension)

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Store transaction embeddings for similarity search
CREATE TABLE transaction_embeddings (
    id SERIAL PRIMARY KEY,
    transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    embedding vector(1536), -- OpenAI/Voyage embedding dimension
    model_version VARCHAR(50),
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_transaction_embeddings_vector ON transaction_embeddings 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Store categorization patterns learned from user corrections
CREATE TABLE learned_patterns (
    id SERIAL PRIMARY KEY,
    pattern TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    confidence DECIMAL(3,2) DEFAULT 0.50,
    
    times_seen INTEGER DEFAULT 1,
    times_correct INTEGER DEFAULT 1,
    last_seen_at TIMESTAMP DEFAULT NOW(),
    
    embedding vector(1536),
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_learned_patterns_embedding ON learned_patterns 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
```

---

## Utility Functions

```sql
-- Calculate financial year from date
CREATE OR REPLACE FUNCTION get_financial_year(input_date DATE) 
RETURNS VARCHAR(7) AS $$
BEGIN
    IF EXTRACT(MONTH FROM input_date) >= 7 THEN
        RETURN EXTRACT(YEAR FROM input_date)::TEXT || '-' || 
               LPAD((EXTRACT(YEAR FROM input_date) + 1 - 2000)::TEXT, 2, '0');
    ELSE
        RETURN (EXTRACT(YEAR FROM input_date) - 1)::TEXT || '-' || 
               LPAD((EXTRACT(YEAR FROM input_date) - 2000)::TEXT, 2, '0');
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to relevant tables
CREATE TRIGGER update_accounts_updated_at BEFORE UPDATE ON accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_transactions_updated_at BEFORE UPDATE ON transactions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_smsf_members_updated_at BEFORE UPDATE ON smsf_members
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_smsf_holdings_updated_at BEFORE UPDATE ON smsf_holdings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

---

## Views for Common Queries

```sql
-- Current account balances
CREATE VIEW v_account_balances AS
SELECT 
    a.id,
    a.name,
    a.account_type,
    a.institution,
    a.balance,
    a.is_smsf,
    COUNT(t.id) as transaction_count,
    MAX(t.transaction_date) as last_transaction_date
FROM accounts a
LEFT JOIN transactions t ON a.id = t.account_id
WHERE a.is_active = TRUE
GROUP BY a.id;

-- Monthly spending by category
CREATE VIEW v_monthly_spending AS
SELECT 
    DATE_TRUNC('month', t.transaction_date) as month,
    c.name as category,
    COUNT(*) as transaction_count,
    SUM(ABS(t.amount)) as total_amount
FROM transactions t
JOIN categories c ON t.category_id = c.id
WHERE t.amount < 0 -- Expenses only
GROUP BY DATE_TRUNC('month', t.transaction_date), c.name;

-- SMSF portfolio summary
CREATE VIEW v_smsf_portfolio AS
SELECT 
    h.member_id,
    h.code,
    h.name,
    h.asset_type,
    h.sector,
    h.units,
    h.purchase_price,
    h.current_price,
    h.cost_base,
    h.current_value,
    h.unrealised_gain,
    (h.unrealised_gain / NULLIF(h.cost_base, 0) * 100) as unrealised_gain_pct,
    h.purchase_date,
    (h.current_value / SUM(h.current_value) OVER (PARTITION BY h.member_id) * 100) as portfolio_weight_pct
FROM smsf_holdings h
WHERE h.is_active = TRUE;

-- Uncategorized transactions
CREATE VIEW v_uncategorized_transactions AS
SELECT 
    t.id,
    t.transaction_date,
    t.description,
    t.merchant_name,
    t.amount,
    a.name as account_name
FROM transactions t
JOIN accounts a ON t.account_id = a.id
WHERE t.is_categorized = FALSE
ORDER BY t.transaction_date DESC;
```

---

## Schema Version & Migrations

```sql
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    description TEXT,
    applied_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO schema_version (version, description) VALUES 
    (1, 'Initial schema creation');
```

---

## Indexes Summary

**High Priority Indexes** (performance critical):
- `idx_transactions_account` - Account-based queries
- `idx_transactions_date` - Date range queries
- `idx_transactions_external` - Deduplication
- `idx_smsf_holdings_member` - SMSF portfolio views
- `idx_networth_date` - Historical net worth

**Medium Priority Indexes**:
- `idx_transactions_category` - Spending analysis
- `idx_transactions_merchant` - Merchant lookup
- `idx_smsf_trans_date` - SMSF transaction history

**Low Priority Indexes** (can add later if needed):
- GIN indexes on arrays (tags, name_variations)
- Vector indexes (when RAG is implemented)

---

## Data Retention Policy

| Table | Retention | Reason |
|-------|-----------|--------|
| transactions | Unlimited | Tax compliance (7 years minimum) |
| smsf_transactions | Unlimited | ATO requirements (10 years) |
| smsf_documents | Unlimited | Legal/compliance |
| import_batches | 12 months | Audit trail |
| categorization_history | 24 months | Learning data |
| net_worth_snapshots | Unlimited | Historical tracking |

---

## Security Considerations

1. **Sensitive Data**:
   - TFN should be encrypted at rest (use `pgcrypto`)
   - Account numbers should be masked in views
   - Document file_path should be obfuscated

2. **Row-Level Security** (future):
   - Enable RLS if multi-user support added
   - Ensure members can only see their own data

3. **Backup**:
   - Daily full backups
   - Point-in-time recovery enabled
   - Test restore procedure quarterly

---

**Schema Status**: âœ… Ready for Implementation  
**Target Database**: PostgreSQL 14+  
**Extensions Required**: pgvector (for RAG)  
**Estimated Size**: ~100MB (first year, single user)

---

*End of Database Schema Document*
---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: John's Notes/Personal Finance Orig/DATABASE_SCHEMA.md
