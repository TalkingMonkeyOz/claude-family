---
projects:
- claude-family
tags:
- procedure
- document-analysis
- client-engagement
- parallel-agents
---

# Client Document Analysis — Standard Operating Procedure

## Purpose

Repeatable process for ingesting scattered client documentation, organizing it into structured knowledge, running coherence checks, and producing formal deliverable documents. Developed during the Monash engagement (March 2026).

## When to Use

- Client requires consolidated technical documentation from scattered sources
- Legal/compliance team needs system documentation with source attribution
- Any engagement where 10+ source documents must be synthesized into a deliverable

## Prerequisites

- Python with `python-docx`, `openpyxl`, `PyPDF2` available
- Project set up with `user-documents/`, `knowledge-vault/`, `output/drafts/` structure
- Deliverable requirements defined (what areas need to be covered)

## The 7 Phases

### Phase 1: INGEST
**Goal**: Extract readable text from all source documents.

1. Inventory all files in `user-documents/` (types, sizes, counts)
2. Extract zips into appropriate subdirectories
3. Run batch extraction:
   - `.docx` → `python-docx` → `_extracted_text/*.txt`
   - `.pdf` → `PyPDF2` → `_extracted_text/*.txt`
   - `.xlsx` → `openpyxl` → peek at structure, export key sheets to JSON
   - `.json` → peek at structure and record counts
4. Stash full inventory as pinned workfile

### Phase 2: CATEGORIZE
**Goal**: Map every document to deliverable requirements.

1. Define requirement areas (e.g., 7 areas for Monash legal team)
2. Spawn **3 parallel agents** (split documents into batches of 7-8)
3. Each agent reads extracted text and produces:
   - 2-3 sentence summary per document
   - Which requirement areas it covers (Primary/Partial/None)
   - Key facts extracted
   - GAP markers for missing content
4. Agents write results to `_analysis/batch-N.md`

### Phase 3: GAP ANALYSIS
**Goal**: Identify what's covered and what's missing.

1. Read all batch analysis files
2. Build coverage matrix: documents × requirement areas
3. Identify critical gaps per area
4. Stash gap analysis as pinned workfile
5. Store staging config summary as session fact if applicable

### Phase 4: ORGANIZE
**Goal**: Build structured knowledge base from raw documents.

1. Create `knowledge-vault/` subdirectories aligned with deliverable areas
2. Spawn **4 parallel agents** (one per knowledge domain):
   - Each reads 3-5 source documents
   - Writes organized knowledge files with `[Source:]` attribution
   - Marks unknowns with `[GAP:]` markers
3. Export structured data (config exports, rule sets) to JSON
4. Create human-readable summaries of complex data

### Phase 5: COHERENCE CHECK
**Goal**: Cross-reference knowledge files for consistency.

1. Spawn **3 parallel agents** for pairwise comparison:
   - Group files by overlap potential (e.g., ME vs controls vs config)
   - Check: fact agreement, terminology consistency, assumption alignment
2. Classify findings: CONTRADICTION, GAP, ASSUMPTION_CONFLICT, TERMINOLOGY_DRIFT, DUPLICATION, STALENESS
3. Agents write findings to `_analysis/coherence-check-N.md`
4. Stash findings summary as pinned workfile
5. Identify critical fixes list (typically 5-10 items)

### Phase 6: DRAFT
**Goal**: Produce formal document sections from knowledge base.

1. Create document outline in `output/drafts/document-outline.md`
2. Spawn **4 parallel agents** (one per section group):
   - Each reads relevant knowledge-vault files
   - Writes formal document sections with legal/professional tone
   - Every claim has `[Source:]` attribution
   - Every gap has `[GAP:]` marker
3. Write executive summary connecting all sections
4. Apply coherence fixes from Phase 5

### Phase 7: ASSEMBLE
**Goal**: Produce final deliverable.

1. Create knowledge-vault INDEX.md with reading order
2. Apply coherence fixes across all draft sections
3. Create assembly index mapping files to sections
4. Final gap register as appendix
5. Hand off to Claude Desktop for docx formatting

## Performance Notes

- Monash engagement: 32 source documents → 19 knowledge files → 12 draft sections (1,891 lines)
- Single session with 1M context and parallel agent delegation
- ~15 agents spawned total across all phases
- Key enabler: parallel agents for throughput (3-4 running simultaneously)

## Anti-Patterns

- Do NOT try to read all documents in main context — delegate to agents
- Do NOT skip the coherence check — it catches real contradictions
- Do NOT fabricate content — always use [GAP:] markers
- Do NOT combine extraction and categorization — separate phases

---
**Version**: 1.0
**Created**: 2026-03-18
**Updated**: 2026-03-18
**Location**: 40-Procedures/client-document-analysis-sop.md
