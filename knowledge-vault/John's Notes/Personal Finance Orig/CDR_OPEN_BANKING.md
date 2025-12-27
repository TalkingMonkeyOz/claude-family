---
tags: []
projects: []
---
# Consumer Data Right (CDR) / Open Banking in Australia
## Free and Paid Options for Personal Finance App

**Date:** 26 December 2025  
**Purpose:** Research CDR options for automated transaction downloads

---

## What is CDR (Consumer Data Right)?

The **Consumer Data Right** is Australia's open banking framework. It lets you:
- Authorize apps to access your banking data
- Download transactions automatically from your bank
- Get real-time balance updates
- Access data from multiple institutions via standardized API

**Key Point:** CDR is the **official, free, secure way** to access your bank data in Australia.

---

## Option 1: Direct CDR Access (Free, Complex)

### How It Works
You register your app with ACCC, become an "Accredited Data Recipient" (ADR), and connect directly to banks' CDR APIs.

### Requirements
1. **ACCC Accreditation** - Must prove you're legitimate
2. **Security Standards** - FAPI-compliant security (very strict)
3. **Ongoing Compliance** - Annual audits, incident reporting
4. **Technical Complexity** - OAuth 2.0 + OIDC + FAPI + MTLS

### Cost
- **Free** data access (no per-transaction fees)
- **$0-10,000** accreditation/legal setup
- **Time:** 6-12 months to get accredited

### Pros
- âœ… No ongoing data fees
- âœ… Direct bank connection
- âœ… Full control
- âœ… Most secure

### Cons
- âŒ Extremely complex to set up
- âŒ Requires company/ABN (not for individuals)
- âŒ Annual compliance burden
- âŒ 6+ month timeline

**Verdict:** ❌ **Not viable for personal use** - designed for businesses/fintechs

---

## Option 2: CDR via Aggregator (Paid, Easy)

Use a third-party service that's already CDR-accredited. They handle compliance, you just use their API.

### Major Australian CDR Aggregators

#### **Basiq** (Recommended)
- **Website:** basiq.io
- **Coverage:** 80+ Australian financial institutions
- **Pricing:**
  - **Sandbox:** FREE (for development/testing)
  - **Production:** ~$50-100/month for personal use
  - **Per-connection:** ~$0.50-1.00/month per bank account
- **API Quality:** âœ… Excellent documentation, REST API
- **CDR Compliant:** âœ… Fully accredited

**Example Basiq Pricing:**
- 5 bank accounts × $1/month = $5/month
- Base API access = $50/month
- **Total:** ~$55/month

#### **Frollo**
- **Website:** frollo.com.au
- **Coverage:** 90+ Australian financial institutions
- **Pricing:**
  - **Sandbox:** FREE
  - **Production:** ~$30-60/month
  - **Per-connection:** Similar to Basiq
- **API Quality:** âœ… Good, growing platform
- **CDR Compliant:** âœ… Accredited

**Cheaper than Basiq but slightly less mature.**

#### **Illion** (formerly Proviso)
- **Website:** illion.com.au
- **Coverage:** 100+ institutions
- **Pricing:** $$$ (enterprise-focused, $500+/month)
- **Verdict:** âŒ Too expensive for personal use

#### **Regional Australia Bank (RAB) CDR Gateway**
- **Website:** rab.com.au/cdr
- **Coverage:** Limited (RAB customers only)
- **Pricing:** Free for RAB customers
- **Verdict:** âŒ Not useful unless you bank with RAB

### Comparison: Basiq vs Frollo

| Factor | Basiq | Frollo |
|--------|-------|--------|
| **Coverage** | 80+ banks | 90+ banks |
| **Price** | ~$55/month | ~$35/month |
| **Docs** | Excellent | Good |
| **Maturity** | More established | Newer, growing |
| **Support** | Strong | Good |
| **Best For** | Established apps | Cost-conscious |

**Recommendation:** **Try Frollo first** (cheaper), fall back to Basiq if needed.

---

## Option 3: Non-CDR Aggregators (Paid, Legacy)

These existed before CDR and use "screen scraping" (log in as you, scrape data). Less secure than CDR.

### **Yodlee**
- **Coverage:** Good
- **Pricing:** $$$ (enterprise)
- **Method:** Screen scraping (not CDR)
- **Verdict:** âŒ Being replaced by CDR, don't use

### **Plaid** (US-based)
- **Coverage:** Limited in Australia
- **Method:** Screen scraping
- **Verdict:** âŒ Not recommended for Australia

**Avoid these** - CDR is the modern, secure standard.

---

## Option 4: Manual CSV Import (Free, Manual)

Most banks let you export transactions as CSV. You import manually.

### How It Works
1. Log into online banking
2. Download CSV (usually "Export Transactions")
3. Import into your app

### Pros
- âœ… Completely free
- âœ… Works with any bank
- âœ… No third-party access
- âœ… Full privacy

### Cons
- âŒ Manual process (weekly/monthly)
- âŒ Can't get real-time updates
- âŒ Each bank has different CSV format

**Verdict:** âœ… **Good starting point** - use this while you evaluate CDR aggregators

---

## Recommendation for Your App

### Phase 1: Start with Manual CSV Import (Now)
**Why:**
- Free, works immediately
- No subscriptions while building
- Test with real data
- Build import logic you'll need anyway

**Implementation:**
1. Download CSV from Westpac
2. Build CSV parser (handle Westpac format)
3. Import to PostgreSQL
4. Deduplicate based on external_id

### Phase 2: Add Frollo CDR (When App is Working)
**Why:**
- Cheapest CDR option (~$35/month)
- Automate the weekly manual process
- Real-time balance updates
- Professional solution

**Implementation:**
1. Sign up for Frollo sandbox (free)
2. Build OAuth flow in your app
3. Test with sandbox data
4. Upgrade to production when ready
5. Connect your Westpac account

### Phase 3: Optional - Add Basiq (If Frollo Insufficient)
**Why:**
- Better coverage if needed
- More established API
- Fallback if Frollo has issues

---

## Cost Analysis (Annual)

### Manual CSV Import
- **Cost:** $0/year
- **Time Cost:** ~5 min/week = 260 min/year
- **Value of Time:** $0 (you do it anyway during weekly review)

### Frollo CDR
- **Cost:** $35/month × 12 = $420/year
- **Time Saved:** ~4 min/week × 52 = 208 min/year
- **Cost per minute saved:** $2.02

### Basiq CDR
- **Cost:** $55/month × 12 = $660/year
- **Time Saved:** Same as Frollo
- **Cost per minute saved:** $3.17

### Is CDR Worth It?

**For you specifically:**
- Income: $140,000/year = ~$67/hour
- 208 minutes/year = 3.5 hours
- Time value: 3.5 hours × $67 = $233

**Cost vs Benefit:**
- Frollo: $420/year vs $233 time saved = **-$187 net** (costs more than time saved)
- Manual: $0 vs $233 opportunity cost = **+$233 net** (better deal)

**Verdict:** **Start with manual CSV import**. Only add CDR automation if:
- You find the weekly manual process annoying
- You want real-time data
- You're willing to pay $35/month for convenience

---

## CDR Technical Overview (If You Go This Route)

### Authentication Flow (OAuth 2.0 + FAPI)
```
1. User clicks "Connect Westpac"
2. Your app redirects to Frollo → Frollo redirects to Westpac
3. User logs into Westpac, grants permission
4. Westpac redirects back to Frollo with auth code
5. Frollo exchanges code for access token
6. Your app uses Frollo API with token to fetch transactions
```

### Example API Call (Basiq)
```http
GET https://au-api.basiq.io/accounts/{account_id}/transactions
Authorization: Bearer {access_token}

Response:
{
  "data": [
    {
      "id": "trans_123",
      "description": "Woolworths Sydney",
      "amount": "-45.67",
      "postDate": "2025-12-20",
      "transactionDate": "2025-12-19",
      "balance": "1234.56",
      "class": "debit"
    }
  ]
}
```

### Consent Management
- User can revoke access anytime
- Consent expires after 12 months (must re-authorize)
- CDR rules: must show what data you're accessing

---

## Banks with CDR Support (Partial List)

**Big 4:**
- âœ… Commonwealth Bank (CBA)
- âœ… Westpac
- âœ… ANZ
- âœ… NAB

**Others:**
- âœ… ING
- âœ… Macquarie Bank
- âœ… Bank of Melbourne
- âœ… Bendigo Bank
- âœ… UP Bank
- âœ… 86 400 (now part of UP)

**Credit Cards:**
- âœ… American Express
- âœ… Most bank-issued cards

**Not Yet Supported:**
- âŒ Some credit unions
- âŒ International banks (HSBC, Citibank)
- âŒ Most investment platforms (Commsec, Westpac Broking)

---

## Free Testing (No Risk)

### 1. Frollo Sandbox
- **URL:** https://frollo.com.au/developers
- **Sign up:** Free account
- **Get:** Sandbox API key
- **Test:** Mock bank data, no real accounts needed
- **Learn:** Build integration before paying

### 2. Basiq Sandbox
- **URL:** https://basiq.io/get-started
- **Sign up:** Free developer account
- **Get:** Sandbox API key
- **Test:** Sample transactions, realistic data
- **Learn:** Full API without production costs

**Recommendation:** Sign up for both, test in parallel, choose the one that works better.

---

## Security & Privacy Considerations

### CDR Pros
- âœ… Regulated by government (ACCC oversight)
- âœ… Bank-grade security (FAPI standard)
- âœ… No password sharing (OAuth)
- âœ… Revokable access
- âœ… Data minimization (only request what you need)

### CDR Cons
- âŒ Third party (Frollo/Basiq) sees your data
- âŒ Depends on aggregator staying in business
- âŒ Consent expires (need to re-authorize)

### Manual CSV Pros
- âœ… No third party access
- âœ… Complete privacy
- âœ… You control what data is imported

### Manual CSV Cons
- âŒ Have to log into banks (phishing risk)
- âŒ Manual process (human error)

---

## Recommended Implementation Plan

### Week 1-2: Manual Import
- âœ… Download Westpac CSV
- âœ… Build CSV parser
- âœ… Import to PostgreSQL
- âœ… Test deduplication

### Week 3-4: Test CDR Sandbox
- âœ… Sign up for Frollo sandbox
- âœ… Test OAuth flow (locally)
- âœ… Parse API responses
- âœ… Compare to manual CSV format

### Month 2: Decide
- âœ… If manual CSV is fine → stick with it
- âœ… If want automation → upgrade Frollo to production ($35/month)

### Month 3+: Optimize
- âœ… Daily auto-sync if using CDR
- âœ… OR weekly manual import if using CSV
- âœ… Add more banks as needed

---

## Final Recommendations

### For Immediate Start (This Week):
âœ… **Manual CSV Import**
- Free, works now
- No dependencies
- Privacy-first

### For Future Automation (Month 2-3):
âœ… **Frollo CDR**
- Cheapest CDR option ($35/month)
- Good coverage
- Professional solution

### NOT Recommended:
- âŒ Direct CDR access (too complex for personal use)
- âŒ Basiq as first choice (more expensive than Frollo)
- âŒ Yodlee/Plaid (outdated, use CDR instead)

---

## Sample CSV Formats (Australian Banks)

### Westpac Transaction Export
```csv
Date,Description,Debit Amount,Credit Amount,Balance
20/12/2025,WOOLWORTHS SYDNEY,45.67,,1234.56
19/12/2025,Salary,,3500.00,4734.56
18/12/2025,NANDOS PARRAMATTA,32.50,,1234.56
```

### CommBank Transaction Export
```csv
Date,Description,Amount,Balance
20/12/2025,WOOLWORTHS SYDNEY,-45.67,1234.56
19/12/2025,Salary,3500.00,4734.56
18/12/2025,NANDOS PARRAMATTA,-32.50,1234.56
```

**Note:** Each bank has slightly different format - your parser needs to handle variations.

---

**Decision:** âœ… **Start with Manual CSV, evaluate CDR in Month 2**  
**Cost:** $0 initially, $35/month if you want automation  
**Risk:** None - can always cancel CDR if not worth it

---

*End of CDR/Open Banking Guide*
---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: John's Notes/Personal Finance Orig/CDR_OPEN_BANKING.md
