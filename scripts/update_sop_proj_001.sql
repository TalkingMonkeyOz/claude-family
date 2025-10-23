-- Update SOP-PROJ-001 to version 3.1 with documentation system integration
-- Run: psql -U postgres -d ai_company_foundation -f scripts/update_sop_proj_001.sql

UPDATE public.sops
SET
  version = '3.1',
  procedure_steps = $json$[
    {
      "phase": "Phase 1: Discovery Interview",
      "action": "Conduct strategic discovery interview with user",
      "details": "Diana asks: Problem/opportunity questions (what problem, who experiences it, how currently solved, why worth solving), Commercial intent (revenue model, market size, differentiation), Technical constraints (tech requirements, scale, compliance), Resources & success (budget, metrics, risks). Output: Initial project brief with key findings.",
      "duration": "~30 minutes",
      "responsible": "Diana",
      "step_number": 1
    },
    {
      "phase": "Phase 2: Research & Analysis",
      "action": "Diana conducts autonomous market and technical research",
      "details": "Use WebSearch MCP for: competitor landscape, market size (TAM/SAM/SOM), customer pain points, technology trends, regulatory landscape. Use Postgres MCP to check for similar projects, lessons learned, related SOPs. Use Memory MCP for institutional knowledge. Use Tree-sitter MCP if analyzing existing code. Output: Research findings document with competitive analysis, market opportunity assessment, technical feasibility, risk assessment.",
      "duration": "~1-2 hours",
      "responsible": "Diana",
      "step_number": 2
    },
    {
      "phase": "Phase 3: Living Document Creation",
      "action": "Diana drafts all 6 living documents, user approves",
      "details": "Create from templates in C:\\Projects\\ai-workspace\\_templates\\project-initiation: 1) PROJECT_BRIEF.md (problem statement, target audience, opportunity size, success criteria), 2) BUSINESS_CASE.md (market analysis, competitive landscape, revenue model, GTM strategy), 3) ARCHITECTURE.md (system design, tech stack, scalability, security), 4) EXECUTION_PLAN.md (phases, milestones, work packages, agent assignments, timeline), 5) COMPLIANCE.md (regulatory requirements, data privacy, industry standards), 6) RISKS.md (risk register with mitigation and contingency plans). All docs have version numbers, status (DRAFT/APPROVED/ACTIVE), author/approver fields.",
      "duration": "~2-3 hours collaborative",
      "responsible": "Diana with user approval",
      "step_number": 3
    },
    {
      "phase": "Phase 4: Approval Gate",
      "action": "Diana presents complete package, user decides GO/PAUSE/NO-GO",
      "details": "Executive summary of findings, all 6 living documents, Diana's GO/NO-GO recommendation with reasoning, resource requirements. User decision: GO (proceed to execution), PAUSE (need more research/refinement), NO-GO (archive as learning). Only proceed to Phase 5 if GO decision.",
      "duration": "~30 minutes",
      "responsible": "User decision",
      "step_number": 4
    },
    {
      "phase": "Phase 5: Project Setup (if GO)",
      "action": "Diana creates triple-redundant project infrastructure",
      "details": "Database: INSERT INTO projects with metadata JSONB (filesystem_path: C:\\Projects\\{name}, project_type: commercial/internal, revenue_model, tech_stack, phase, living_docs_version). Filesystem: Create C:\\Projects\\{project-name}/docs/ (copy all 6 living docs here), /src or /backend, /frontend (if web), /tests, /data, README.md, .gitignore. Work Packages: INSERT INTO work_packages from EXECUTION_PLAN.md breakdown, assign to Claude Family agents. Memory MCP: Create project entity with overview, key decisions, phase status.",
      "duration": "~30 minutes",
      "responsible": "Diana",
      "step_number": 5
    },
    {
      "phase": "Phase 5: Project Setup (if GO)",
      "action": "Initialize documentation management system",
      "details": "Run: python C:\\Projects\\claude-family\\scripts\\init_project_docs.py C:\\Projects\\{project-name}. This creates: .docs-manifest.json (tracks all markdown files), git pre-commit hook (enforces CLAUDE.md <=250 lines), initial categorization of 6 living docs. Creates filesystem structure: CLAUDE.md (AI context file), .docs-manifest.json, .git/hooks/pre-commit. This integrates with monthly documentation audit process and prevents documentation bloat.",
      "duration": "~5 minutes",
      "responsible": "Diana",
      "step_number": "5.1"
    },
    {
      "phase": "Phase 5: Project Setup (if GO)",
      "action": "Create CLAUDE.md with project context",
      "details": "Create CLAUDE.md (<=250 lines enforced by git hook) containing: Project type & purpose, Build commands, Key constraints/gotchas, Tech stack, File structure overview, Recent work (SQL query to session_history). Template at C:\\Projects\\claude-family\\templates\\CLAUDE.md. This file auto-loads when Claude Code opens the project, providing instant context restoration. Update as project evolves, monthly audit ensures it stays under 250 lines.",
      "duration": "~15 minutes",
      "responsible": "Diana",
      "step_number": "5.2"
    },
    {
      "phase": "Phase 6: Execution & Monitoring (ongoing)",
      "action": "Diana orchestrates execution and maintains living documents",
      "details": "Daily monitoring: Query stalled work packages (status=IN_PROGRESS AND updated_at < NOW() - INTERVAL '24 hours'), check project health. Living document updates: Update EXECUTION_PLAN.md as milestones complete, RISKS.md as new risks identified, version increment on major changes, sync to database metadata. Agent coordination: Assign work packages as dependencies complete, intervene if work stalls >24 hours, escalate blockers to user. Progress reporting: Weekly status updates, milestone notifications, risk alerts. Monthly documentation audit: Run audit_docs.py on project, archive old session notes/reports quarterly, update .docs-manifest.json when adding new docs, ensure CLAUDE.md stays under 250 lines.",
      "duration": "Ongoing throughout project lifecycle",
      "responsible": "Diana with Claude Family",
      "step_number": 6
    }
  ]$json$::jsonb,
  description = 'Comprehensive project initiation, planning, and management standard - from initial idea through living documentation to execution. Integrates Diana''s Project Initiation Framework with 6-phase discovery process. Updated to include documentation management system (CLAUDE.md, .docs-manifest.json, git hooks, monthly audits).',
  updated_at = CURRENT_TIMESTAMP
WHERE sop_code = 'SOP-PROJ-001'
RETURNING sop_code, version, title, updated_at;
