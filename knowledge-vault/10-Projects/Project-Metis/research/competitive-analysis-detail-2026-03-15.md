---
projects:
- Project-Metis
tags:
- type/research
- scope/market
---

# Competitive Analysis Detail: Per-Competitor Breakdowns

Companion to [[competitive-analysis-2026-03-15]]. Deep dives on each competitor.

---

## Enterprise RAG / Knowledge Platforms

### Glean

**What it does**: Enterprise AI search across 100+ workplace tools. Knowledge graph maps people, content, and interactions. Custom AI applications without coding. $50+/user/month, enterprise quotes only.

**Overlap**: Semantic search, knowledge retrieval, enterprise connectors. Both aim to make organisational knowledge actionable.

**METIS edge**: Glean finds answers; METIS executes governed workflows using those answers. Glean has no BPMN process enforcement, no cross-engagement compounding, no PS-specific domain model.

**Glean edge**: Proven at scale, 100+ connectors out of the box, knowledge graph already built, funded and shipping. METIS has none of this.

### Microsoft Copilot for M365

**What it does**: AI embedded in Office apps. Wave 3 (2026) adds Cowork — agentic mode that breaks down complex requests into multi-step plans, executes across tools, runs for hours. 8M paying subscribers but only 1.8% conversion from 440M M365 users.

**Overlap**: Document generation, multi-step task execution, enterprise data grounding. Cowork's agentic capabilities overlap significantly with METIS's execution model.

**METIS edge**: PS-specific domain model, BPMN governance (Copilot has no quality gate enforcement), knowledge compounding across engagements, product/client knowledge separation.

**Copilot edge**: Ubiquity. Every enterprise already has M365. Graph grounding gives enterprise-specific responses. Cowork runs inside the customer's tenant. No additional platform to buy.

**Threat level**: HIGH. If Microsoft adds PS-specific agent templates with quality gates, the core METIS value prop erodes significantly.

### Google Vertex AI Search

**What it does**: Managed enterprise RAG. Document parsing, chunking, embedding, retrieval, grounded answers. Gemini 2.0 Flash for RAG. Pay-per-query pricing.

**Overlap**: RAG pipeline, document processing, semantic search.

**METIS edge**: Vertex is infrastructure; METIS is a product. Vertex doesn't know what a consulting engagement is.

**Vertex edge**: Google-scale infrastructure, managed service, no ops burden, proven RAG quality.

**Threat level**: LOW as competitor. HIGH as something METIS should build on top of.

---

## AI Agent Frameworks

### LangChain / LangGraph

**What it does**: Most popular agent framework. LangGraph adds graph-based multi-agent workflows with state management. Most token-efficient in benchmarks.

**Overlap**: Multi-agent orchestration, stateful workflows, tool use.

**METIS edge**: LangGraph is a framework, not a product. It has no domain model, no governance, no knowledge lifecycle management.

**Their edge**: Massive community, production-proven, can be used to build a METIS competitor.

### CrewAI

**What it does**: Role-based agent teams with Crews (dynamic collaboration) and Flows (deterministic orchestration). Easiest to reason about for business workflows.

**Overlap**: Role-based agents, task orchestration, structured workflows.

**METIS edge**: BPMN governance, PS domain knowledge, knowledge compounding. CrewAI is generic.

**Their edge**: Active development, growing community, Flows layer adds determinism that's architecturally similar to METIS's BPMN approach.

### AWS Bedrock Agents / AgentCore

**What it does**: Managed agent execution with stateful runtime (co-designed with OpenAI). Session isolation, persistent memory, 8hr long-running tasks, built-in observability.

**Overlap**: Stateful agent execution, enterprise governance, multi-step workflows.

**METIS edge**: PS vertical focus. Bedrock is horizontal infrastructure.

**Their edge**: AWS ecosystem, managed infrastructure, stateful runtime solves hard engineering problems METIS would need to build.

**Threat level**: LOW as competitor, HIGH as infrastructure METIS should evaluate.

---

## Professional Services Automation

### ServiceNow Autonomous Workforce

**What it does**: AI agents that autonomously diagnose, plan, and execute workflows. L1 Service Desk AI Specialist handles 90%+ of IT requests, 99% faster than humans. Expanding to ITSM, CSM, HR, and enterprise ops.

**Overlap**: Autonomous workflow execution, process governance, enterprise-grade controls.

**METIS edge**: ServiceNow automates IT/HR/service processes. METIS targets consulting delivery — requirements gathering, design, implementation governance. Different workflows entirely.

**Their edge**: Massive enterprise installed base, proven autonomous execution, expanding AI specialist roster.

**Threat level**: MEDIUM. If ServiceNow builds "Consulting Delivery AI Specialist," they have the platform and the customers. But PS delivery is far from their core.

### Salesforce Agentforce

**What it does**: Autonomous AI agents that analyse data, reason through options, and execute actions. Trust Layer for security. Conversation-based pricing ($2/conversation).

**Overlap**: Autonomous multi-step execution, trust/governance layer, enterprise data grounding.

**METIS edge**: PS delivery focus vs CRM focus. Knowledge compounding across engagements. BPMN governance.

**Their edge**: CRM dominance, Trust Layer is architecturally similar to what METIS needs, massive ecosystem.

---

## Big 4 Internal Tools (Key Comparison)

These validate METIS's thesis but are not direct competitors (yet).

| Firm | Tool | Investment | Key Capability | Productisation Risk |
|------|------|-----------|----------------|-------------------|
| McKinsey | Lilli + QuantumBlack | 7,000 staff, 40% of revenue | Knowledge retrieval for consultants | HIGH — OpenAI partnership announced |
| Deloitte | PairD + Zora AI | $3B through 2030 | Agentic AI with Nvidia, 100+ GenAI accelerators | MEDIUM — focused on internal scale |
| EY | EY.ai / EYQ | Custom LLM | Firm-wide AI across audit/tax/consulting | LOW — deeply integrated with EY processes |
| KPMG | KymChat | $2B Microsoft alliance | Azure-based AI across services | LOW — Microsoft-dependent |
| Accenture | myWizard/SynOps | $3B, 80K AI workforce | Client delivery automation | HIGH — OpenAI partnership |

The OpenAI partnerships with McKinsey, BCG, Accenture, and Capgemini (announced Feb 2026) are the biggest threat signal. If these lead to productised PS AI tools, the mid-market gap METIS targets could close from above.

---

## Process Mining

### Celonis

**What it does**: Process Intelligence Graph creates digital twins of business processes. AgentC (2024) deploys AI agents for process optimisation. 100+ ERP connectors.

**Relevance to METIS**: Complementary, not competitive. Celonis discovers how processes actually run in ERP systems. METIS governs how knowledge work should run. Potential integration partner.

### UiPath

**What it does**: RPA + process mining + task mining + communications mining. Integrated automation from discovery to execution.

**Relevance to METIS**: Complementary. UiPath automates repetitive tasks. METIS orchestrates knowledge work. Different layers of the same enterprise stack.

---

## Vertical AI Startups

### Compounding Technologies

**What it does**: 10-week cohort program for PS firms to become AI-enabled. Firm-wide AI audit, 5+ automations, long-term roadmap. Consulting model, not a platform.

**Relevance**: Validates market demand. But it's a services play, not a product play. METIS is the product they'd want to exist.

### Market Dynamics

The vertical AI startup space is exploding but focused on legal ($300B market), healthcare, and finance. Professional services delivery automation for mid-market consulting firms is genuinely underserved. The AI knowledge management market grew 47.2% CAGR (2024-2025) and is projected to hit $35.8B by 2029.

---

**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/Project-Metis/research/competitive-analysis-detail-2026-03-15.md
