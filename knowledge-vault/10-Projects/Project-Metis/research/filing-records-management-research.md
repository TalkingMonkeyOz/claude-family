---
projects:
  - Project-Metis
tags:
  - project/Project-Metis
  - type/research
  - topic/filing-systems
  - topic/records-management
  - topic/knowledge-management
created: 2026-03-10
updated: 2026-03-10
status: active
---

# Filing and Records Management Systems: Research for AI Knowledge Assembly

## Purpose

This document surveys physical and digital filing systems, records management principles, and modern knowledge tools to extract design principles for an AI knowledge management system. The core problem: within a single AI coding session, a user might work on SQL queries, then deidentification, then a parallel run pipeline. Each is a different "work context" but they occur in one session. An advanced filing system tracks these as separate "files" with cross-references, linking to sessions, working notes, research, and callouts to other documents.

The research here informs the design of METIS's Augmentation Layer, particularly the workfile system and context assembly mechanisms.

---

## 1. Physical Filing Systems

Physical filing systems have been refined over more than a century of records management practice. Each system solves a specific organizational problem, and understanding their tradeoffs illuminates why digital systems make the choices they do.

### 1.1 Alphabetic Filing

The most frequently used system for collections under approximately 5,000 records. Files are arranged by name (personal, business, or institutional) in strict alphabetical order following standardized rules (ARMA filing rules or ANSI/ARMA 12-2005).

**Strengths:** Self-indexing (no separate index required), intuitive for anyone who knows the alphabet, fast retrieval when you know the name.

**Limitations:** Breaks down at scale because common letters (S, M, B) create congested sections while rare letters (Q, X, Z) waste space. Requires standardized rules for edge cases (Mac vs Mc, "The" prefix, abbreviations). Provides no topical grouping; unrelated records sit adjacent because their names happen to sort nearby.

**AI parallel:** Alphabetic filing is analogous to sorting knowledge entries by title or keyword. Simple, but fails when the retrieval question is conceptual rather than name-based ("how do I handle timezone edge cases" will not be found under "T" or "H").

### 1.2 Numeric Filing

Records are assigned numbers and filed in numeric sequence. Three major variants exist, each solving different problems.

**Straight Numeric (Serial) Filing:** Records filed in ascending order (000001, 000002, 000003...). Easy to train staff on. The newest records always cluster at the end of the file, creating congestion where multiple staff work on current records simultaneously. Misfiles are hard to spot because the eye must compare all digits at once.

**Terminal Digit Filing:** The record number is read in pairs from right to left. For number 45-82-17, the primary section is 17, secondary is 82, tertiary is 45. This creates 100 primary sections (00-99), and new records distribute evenly across all sections because only every 100th consecutive number lands in the same primary section. Originally developed for large medical records departments handling hundreds of thousands of files.

Benefits: even distribution eliminates congestion, enables quality control by assigning staff to specific sections, makes misfiles visually obvious (color-coded labels for each digit pair create a broken color pattern when a file is in the wrong section), and eliminates the need to backshift records when the collection grows.

**Middle Digit Filing:** The middle pair of digits is primary, left pair is secondary, right pair is tertiary. Provides more even distribution than straight numeric but less than terminal digit. Useful when transitioning from straight numeric because blocks of 100 sequential records stay together.

**AI parallel:** Terminal digit filing's principle of distributing records evenly across storage sections is directly analogous to how vector embeddings distribute knowledge across high-dimensional space. Both approaches solve the "hot spot" problem where sequential/recent items cluster together and create retrieval bottlenecks. The access_count field in the workfile system serves a similar purpose to terminal digit section assignment: it helps distribute retrieval attention across the knowledge base rather than always returning the most recently created items.

### 1.3 Alphanumeric Systems

Combine letters and numbers to create structured identifiers. The canonical example is the library call number system (Dewey Decimal: 636.7, Library of Congress: SF427.A3).

**Structure:** A letter prefix establishes the broad category, numbers provide specificity within that category, and additional letters/numbers enable infinite subdivision. For example, in Library of Congress classification: Q (Science) -> QA (Mathematics) -> QA76 (Computer science) -> QA76.73 (Programming languages) -> QA76.73.P98 (Python).

**Strengths:** Infinite expandability without renumbering, human-readable category identification from the prefix alone, natural grouping of related subjects on the shelf.

**Limitations:** Requires an index or classification scheme to use (indirect access), cross-cutting topics must be assigned to a single primary location, classification decisions are subjective and inconsistent across different classifiers.

**AI parallel:** The workfile system's (project, component, title) triple is an alphanumeric-style classification. The project is the broadest category, the component narrows it, and the title identifies the specific item. Like library classification, this forces a single primary location for each item, which is why semantic search exists as a complementary retrieval path.

### 1.4 Subject Filing

Records organized by topic rather than by name or number. Uses an encyclopedic arrangement where main subjects are divided into subdivisions. Common in administrative offices where correspondence and reports relate to topics (budget, personnel, facilities) rather than to specific people or case numbers.

**The cross-cutting problem:** A document about "budget implications of the new personnel policy for the facilities department" legitimately belongs under budget, personnel, AND facilities. Subject filing forces a primary classification and creates cross-references to the other two locations. This is the fundamental limitation of any single-hierarchy filing system.

**Implementation:** Requires a controlled vocabulary (subject headings list) to prevent the same topic from being filed under different names by different people. "Staff", "Personnel", "Employees", and "Human Resources" must all resolve to one heading with cross-references from the others.

**AI parallel:** Subject filing maps to tag-based or topic-based organization in digital systems. The controlled vocabulary problem is exactly the deduplication and merge challenge in the cognitive memory system, where remember() checks for >85% similarity before creating a new entry.

### 1.5 Geographic Filing

Records arranged by location: country > state/province > city > office. Used by organizations with distributed operations (sales territories, branch offices, field stations).

**Strengths:** Natural for location-based queries ("show me everything related to the Melbourne office"), supports territory assignment and regional reporting.

**Limitations:** Fails when work crosses geographic boundaries. A project involving both Melbourne and Sydney offices must be filed in one location with a cross-reference in the other.

**AI parallel:** Geographic filing maps to the client_domain concept in METIS's multi-tenancy model. Projects grouped by domain (nimbus, ato, finance) provide geographic-style scoping where "show me everything for nimbus" is a natural query.

### 1.6 Chronological Filing

Records arranged by date, with the most recent on top (reverse chronological) or in sequence (forward chronological). Used for correspondence, transaction records, and time-series data.

**Strengths:** Natural for "what happened recently" queries, easy to maintain (just add to the top/end), supports retention scheduling (everything older than X years can be reviewed for disposal).

**Limitations:** Requires knowing approximately when something happened to find it. A letter received six months ago about an ongoing topic requires scanning through six months of records unless a subject index exists alongside the chronological file.

**AI parallel:** Session-based organization is inherently chronological. Session facts, session notes, and session handoffs are all time-ordered. The limitation is identical: finding "that decision we made about the database schema" requires knowing which session it happened in, unless semantic search provides an alternative retrieval path.

### 1.7 The Filing Cabinet Metaphor

The physical filing cabinet provides a three-level hierarchy that maps directly to digital organization:

| Physical | Digital (Workfiles) | Purpose |
|----------|-------------------|---------|
| Cabinet | Project | Broadest scope: which body of work |
| Drawer | Component | Subsystem or area within the project |
| File folder | Title (document) | Specific named item within the component |
| Document pages | Content | The actual information |
| Label/tab | Metadata | Classification, dates, type |
| Cross-reference card | Relations/links | Pointers to related items elsewhere |
| Out card | Access tracking | Who has it, when accessed |
| Color-coded tab | Visual type indicator | Quick identification of category |

**Key insight from physical filing:** The cabinet metaphor works because it matches how people think about work organization. People naturally say "the session hooks stuff" (drawer/component) not "document ID 47382." The component-level grouping is the most natural unit of human retrieval, which is why the workfile system uses component as the primary retrieval key for unstash().

---

## 2. Records Management Principles

Records management is a formal discipline with internationally recognized standards (ISO 15489, ISO 23081). Its principles, developed for managing organizational records at scale, provide a theoretical foundation for AI knowledge lifecycle management.

### 2.1 Records Lifecycle

The records lifecycle describes five stages that every record passes through:

| Stage | Description | Duration | AI Memory Parallel |
|-------|-------------|----------|-------------------|
| **Creation/Receipt** | Record comes into existence | Instantaneous | `remember()`, `store_session_fact()`, `stash()` |
| **Active Use** | Record is regularly referenced and updated | Days to months | SHORT tier, current session workfiles |
| **Semi-Active** | Record is occasionally referenced but not regularly updated | Months to years | MID tier, infrequently accessed workfiles |
| **Inactive/Archive** | Record is retained for legal/historical purposes but rarely accessed | Years to decades | LONG tier, archived memories |
| **Disposition** | Record is destroyed or permanently preserved | Terminal | ARCHIVED tier (confidence < 30), eventual deletion |

**Key insight:** The lifecycle is not optional. Without active management of transitions between stages, every system eventually drowns in accumulated records. The cognitive memory system's consolidate_memories() function implements exactly this lifecycle management, promoting short-term facts to mid-term knowledge, mid-term to long-term, and decaying/archiving stale entries.

### 2.2 File Plans

A file plan is the master index of all records in an organization. It defines:

- What categories of records exist (the classification scheme)
- Where each category is stored (physical location or system)
- Who is responsible for each category (ownership)
- How long each category is retained (retention period)
- What happens at end of retention (destroy, archive, or review)

**Structure:** File plans are hierarchical, typically 3-4 levels deep. A government file plan might look like:

```
100 - Administration
  110 - Organization and Management
    111 - Policies and Procedures
    112 - Delegations of Authority
  120 - Human Resources
    121 - Recruitment
    122 - Training
200 - Finance
  210 - Budgeting
  220 - Accounting
```

**AI parallel:** The knowledge vault's folder structure (00-Inbox, 10-Projects, 20-Domains, 30-Patterns, 40-Procedures) is a file plan. The column_registry's valid values for workfile_type (notes, findings, questions, approach, investigation, reference) is a controlled vocabulary within that plan. The gap: there is no formal retention policy for knowledge entries. The consolidation mechanism handles lifecycle transitions, but there is no explicit "destroy after X days of zero access" policy equivalent to a retention schedule.

### 2.3 Retention Schedules

Retention schedules specify how long each category of record must be kept and what happens when that period expires. They are driven by legal requirements, regulatory compliance, operational need, and historical value.

| Retention Type | Trigger | Example |
|----------------|---------|---------|
| **Time-based** | Fixed period from creation | "Destroy after 7 years" |
| **Event-based** | Triggered by an event | "Destroy 2 years after project closure" |
| **Permanent** | Never destroyed | "Transfer to archives permanently" |
| **Review** | Periodic assessment | "Review at 5 years; destroy or reclassify" |

**AI parallel:** The cognitive memory system implements implicit retention through confidence decay: memories accessed infrequently lose confidence over time, and those below confidence 30 with no access in 90+ days are archived. This is an event-based retention policy. What is missing is time-based retention (session facts from 6 months ago should not persist at the same priority as yesterday's facts) and explicit review triggers ("this pattern has been accessed 50 times but never verified; flag for human review").

### 2.4 Provenance Principle

The principle of provenance (respect des fonds), established in European archival practice around 1840 and formalized in Prussian state archives in 1881, states that records created by one entity must not be intermixed with records created by another entity. The records of Department A stay with Department A's records, even if some of those records discuss Department B's activities.

**Two components:**
1. **Respect des fonds:** Records from different creators must be kept separate
2. **Original order:** The arrangement imposed by the creating entity must be preserved

**Why it matters:** Provenance preserves context. A memo that says "approved" means something different depending on whether it came from the legal department or the engineering team. Mixing records from different creators destroys that contextual meaning.

**AI parallel:** The workfile system's project-scoping enforces provenance. A workfile created in the claude-family project stays with claude-family, even if it discusses patterns that apply to nimbus. Cross-project knowledge goes into the knowledge vault (domain knowledge), not into project-specific workfiles. The session_id field on workfiles provides creator provenance: which session created this knowledge, and therefore in what context.

### 2.5 Original Order

Original order means maintaining the arrangement that the creating body imposed on its records. If a department filed its correspondence chronologically, the archivist preserves that chronological order rather than re-sorting alphabetically.

**Key nuance:** Original order does not mean original sequence. The logic and groupings matter more than the specific position of each document. If records were organized by project, they should remain organized by project, even if individual documents within each project group are not in strict date order.

**AI parallel:** When recalling workfiles with unstash(component), the system returns them in the order and grouping the user created. It does not re-sort or reorganize. The component grouping is the "original order" of the creator's thinking about their work.

### 2.6 Chain of Custody

Chain of custody tracks every transfer of a record from one custodian to another. In legal and medical contexts, an unbroken chain of custody establishes that a record has not been tampered with.

**Elements tracked:** Who had possession, when they received it, when they transferred it, to whom, and whether any modifications were made during their custody.

**AI parallel:** The audit_log table provides chain of custody for work items. Session_id on workfiles and knowledge entries records which session created or modified each item. What is not yet tracked: which sessions read (but did not modify) a knowledge entry. The access_count and last_accessed_at fields record aggregate access but not the identity of each accessor.

### 2.7 Disposition

Disposition is the controlled destruction or permanent preservation of records at the end of their retention period. It is not deletion; it is a formal, documented, authorized action.

**Disposition options:**
- **Destruction:** Secure, verified destruction with a certificate of destruction
- **Transfer to archives:** Permanent preservation in an archival repository
- **Transfer to successor:** Records go to the organizational unit that inherits the function
- **Sampling:** Destroy most, preserve a statistically representative sample

**AI parallel:** The ARCHIVED tier in cognitive memory is disposition-as-transfer. Memories are not destroyed; they are moved to a tier where they do not consume retrieval budget but remain available for explicit query. True destruction (DELETE FROM knowledge WHERE ...) is not currently implemented and arguably should not be, given the value of maintaining a complete audit trail. A sampling approach could be useful: archive most session facts but preserve a representative sample from each session for long-term pattern analysis.

---

## 3. Cross-Referencing and Linking

The challenge of connecting related information across different locations is as old as filing itself. Physical systems developed several mechanisms to solve it.

### 3.1 Cross-Reference Cards

When a record could logically be filed under multiple headings, the physical record goes in one location and a cross-reference card is placed in each alternative location. The card reads "See: [primary location]" and may include a brief description of why the record is relevant to this alternative heading.

**Implementation variants:**
- **Card cross-reference:** A card saying "See Also: Budget > 2025 > Q3 Report" placed in the Personnel file
- **Photocopy cross-reference:** A physical copy of the document placed in the secondary location (creates duplication but ensures the information is available without retrieval from the primary location)
- **Guide card cross-reference:** A permanent card at the front of a section listing all cross-references from that section to others

**AI parallel:** Knowledge relations (link_knowledge() with typed relationships like "related_to", "depends_on", "supersedes") are digital cross-reference cards. The workfile system does not yet have explicit cross-references between workfiles, but the semantic search (search_workfiles) provides implicit cross-referencing by returning semantically similar items regardless of their component placement.

### 3.2 Dossier Systems

A dossier is a comprehensive collection of all documents about a single subject, case, person, or entity, regardless of their original source. Unlike subject filing (which groups by topic), dossier filing groups by entity.

**Structure:** All correspondence, reports, decisions, and notes relating to "Client X" go into the Client X dossier, regardless of whether they were created by sales, engineering, support, or legal.

**Strength:** Provides a complete picture of one entity in one place. When you open the dossier, you see everything.

**Limitation:** Documents that relate to multiple entities (a contract between Client X and Client Y) must be placed in one dossier with a cross-reference in the other.

**AI parallel:** The workfile component is dossier-like. All workfiles with component="session-hooks" form a dossier of everything known about session hooks, regardless of which session created the knowledge. The recall_memories() function with a topic query creates an ad-hoc dossier by assembling all relevant memories across tiers.

### 3.3 Case File Methodology

Case files are the records management approach used in legal, medical, and social services contexts where work progresses through stages over time and all records must be kept together for continuity.

**Characteristics:**
- One folder (or set of folders) per case
- Documents accumulated over time in chronological order within the case
- The case file is the authoritative record of everything that happened
- Case files may be active for years or decades
- Closing a case triggers retention scheduling

**Medical records variant:** A patient's medical record is a case file that accumulates across every visit, procedure, and test over their lifetime. The unit numbering system assigns one number per patient, and all encounters file under that number. This is in contrast to serial numbering, where each visit gets its own number.

**AI parallel:** A feature in the work tracking system is a case file. Feature F130 (Cognitive Memory) accumulates build tasks, decisions, code changes, test results, and session notes over its lifetime. When the feature is completed, it is a complete record of everything that happened. The gap: there is no unified "case view" that assembles the feature record, its linked build tasks, relevant session notes, workfiles, and knowledge entries into a single coherent narrative.

### 3.4 Correspondence Filing

Tracking related messages across time, especially when a conversation spans multiple exchanges between multiple parties.

**Physical approach:** File by subject or by correspondent, with each piece of correspondence placed in chronological order. Cross-reference cards link correspondence about the same subject filed under different correspondents.

**Threading:** Modern email threading solves this digitally by linking reply chains. Physical filing achieved similar threading through subject lines and reference numbers on each letter ("Re: Your letter of 15 March regarding Contract 4521").

**AI parallel:** The messaging system (check_inbox, send_message, reply_to) implements correspondence filing. Messages have parent_message_id for threading. Session handoffs are a form of correspondence between sessions: "here is what happened, here is what to do next."

### 3.5 Out Cards and Charge-Out Systems

When a physical file is removed from its location, an out card (or charge-out slip) is inserted in its place. The out card records who took the file, when, and the expected return date.

**Purpose:** Prevents "lost file" situations and enables tracking of who currently has access to information. In medical records, charge-out is critical because a missing patient record can delay treatment.

**Digital evolution:** Modern systems track access electronically. Check-in/check-out in document management systems (SharePoint, Documentum) prevents simultaneous editing and maintains an access log.

**AI parallel:** The access_count and last_accessed_at fields on workfiles serve the same purpose as out cards: tracking who accessed what and when. The session_id recorded on each access could be extended to provide a full access history (which sessions retrieved this workfile), equivalent to a charge-out log.

### 3.6 Color Coding

Color-coded filing uses standardized colors for each digit (0-9) or letter (A-Z) to create visual patterns on file tabs. When files are in correct order, the colors form consistent bands. A misfiled record creates a visible break in the color pattern.

**Standards:** Each digit maps to a standard color (0 = red, 1 = blue, 2 = orange, etc.). End-tab folders with color-coded labels are arranged on open lateral shelves, making the color pattern visible from the aisle.

**Benefits:** Misfiles are instantly visible. Filing speed increases because staff match colors before reading numbers. Retrieval speed improves because the eye finds the color band first, then scans for the specific number within that band.

**AI parallel:** The workfile_type field (notes, findings, questions, approach, investigation, reference) serves as a color-coding system. In a visual interface, each type could be rendered with a distinct color, making it immediately obvious what kind of knowledge a workfile contains without reading its content. The knowledge tier labels ([SHORT], [MID], [LONG]) in RAG results serve a similar function: visual categorization that aids rapid assessment.

---

## 4. Digital Records Management

### 4.1 Electronic Document and Records Management Systems (EDRMS)

EDRMS platforms manage documents and records through their entire lifecycle within a unified system. Major platforms include Microsoft SharePoint, OpenText Content Suite, Micro Focus Content Manager, Hyland OnBase, and Laserfiche.

**Core capabilities:**
- **Classification:** Automatic or manual assignment of records to a file plan
- **Metadata:** Structured metadata capture at creation time, plus auto-extracted metadata
- **Retention:** Automated retention scheduling with disposal holds and review triggers
- **Access control:** Role-based permissions, read/write separation, audit trails
- **Search:** Full-text search plus metadata-filtered search
- **Workflow:** Routing records through approval, review, and disposition processes
- **Legal hold:** Freezing records from disposition when litigation is anticipated

**Lessons for AI knowledge systems:** EDRMS platforms prove that metadata-driven organization scales better than folder-only organization. The most successful deployments combine a light folder hierarchy (3-4 levels) with rich metadata (15-20 fields per record) and full-text search. Over-reliance on folders leads to deep hierarchies that no one navigates; over-reliance on search leads to poor discoverability when the user cannot formulate the right query.

### 4.2 Metadata Standards

ISO 15489 (Information and documentation -- Records management) establishes the international framework for records management. ISO 23081 (Metadata for records) defines what metadata records need.

**ISO 15489 core principles:**
- Records must be authentic (they are what they claim to be)
- Records must be reliable (their content can be trusted)
- Records must have integrity (they are complete and unaltered)
- Records must be usable (they can be located, retrieved, presented, and interpreted)

**ISO 23081 metadata categories:**

| Category | What It Captures | Workfile Equivalent |
|----------|-----------------|-------------------|
| **Identity** | Unique identifier, title, dates | workfile_id, title, created_at |
| **Description** | Content summary, keywords | content (first paragraph), tags |
| **Context** | Creator, creating activity, business process | session_id, component, project_id |
| **Relation** | Links to other records, parent/child | (not yet implemented for workfiles) |
| **Process** | Business rules applied, decisions made | workfile_type |
| **Use** | Access history, access rights | access_count, last_accessed_at |
| **Event** | Actions taken on the record | updated_at (only latest; no event log) |

**Gap analysis:** The workfile system captures Identity, Description, Context, and Use metadata. It is weak on Relation (no explicit links between workfiles) and Event (only the most recent update is tracked, not a history of all modifications).

### 4.3 Auto-Classification

Modern EDRMS platforms use content analysis and metadata inference to automatically classify records into the file plan. Approaches include:

- **Rule-based:** If the document contains keywords X and Y, classify as category Z
- **Template-based:** Documents created from a template inherit the template's classification
- **Machine learning:** Train classifiers on historically classified documents
- **Metadata inference:** Derive classification from the creator's department, the application used, or the file path

**Accuracy:** Auto-classification typically achieves 80-90% accuracy for well-defined categories and drops to 60-70% for ambiguous or cross-cutting topics. Human review remains necessary for edge cases.

**AI parallel:** The remember() function's auto-routing (determining whether a memory is SHORT, MID, or LONG tier) is auto-classification. The dedup/merge check (>85% similarity) is a form of auto-classification that prevents the same knowledge from being filed in multiple tiers. The workfile system could benefit from auto-suggesting the component based on content analysis: if a stash() call's content discusses "session hooks" but the user specified component="infrastructure", the system could suggest the more specific component.

### 4.4 Version Control for Documents

Document version control differs from code version control in important ways:

| Aspect | Document Version Control | Code Version Control |
|--------|------------------------|---------------------|
| **Granularity** | Whole document | Line-level diffs |
| **Branching** | Rare; usually linear | Common; merge workflows |
| **Concurrency** | Check-out/check-in (exclusive lock) | Concurrent editing with merge |
| **Semantics** | Major/minor versions (1.0, 1.1, 2.0) | Commit hashes |
| **Review** | Approval workflows before publish | Pull request review |
| **Retention** | All major versions may be retained | History is comprehensive |

**AI parallel:** The workfile system uses UPSERT semantics, which means only the latest version exists. This is equivalent to overwriting the previous version with no history. The mode="append" option preserves historical content by concatenating rather than replacing, which is closer to an append-only log than to version control. A future enhancement could store version history (previous content snapshots) to support "what did this workfile say two sessions ago?" queries.

### 4.5 Compound Documents

A compound document is a single logical "record" that contains multiple physical files, annotations, and cross-links. Examples include:

- A contract (the agreement PDF + amendments + correspondence + approval emails)
- A patient encounter (clinical notes + lab results + imaging + prescriptions)
- A building permit application (application form + architectural drawings + engineering reports + inspection certificates)

**Implementation:** EDRMS platforms model compound documents as a parent record with child attachments, where the parent carries the classification metadata and the children inherit it. Some systems use "virtual folders" that group related records from different physical locations into a single logical view.

**AI parallel:** A feature in the work tracking system is a compound document: the feature record is the parent, and its build tasks, linked session notes, relevant workfiles, and knowledge entries are children. The gap is that this compound view must be manually assembled (get_work_context does some of this); there is no automatic "show me everything related to F130" that spans all storage systems (features, tasks, workfiles, knowledge, session notes, vault documents).

---

## 5. The Advanced File Concept

Modern knowledge tools have moved beyond the filing cabinet metaphor to create rich, interconnected knowledge structures. Each takes a different approach to the fundamental problem of linking related information.

### 5.1 Notion: Structured Databases with Relations

Notion treats every page as both a document and a database row. Pages can contain blocks (text, code, tables, embeds), and databases can have typed properties including relations to other databases.

**Key concepts:**
- **Blocks:** Atomic content units (paragraph, heading, code block, toggle, callout)
- **Databases:** Collections of pages with typed properties (text, number, date, select, multi-select, relation, rollup)
- **Relations:** Bidirectional links between database entries. A "Tasks" database can have a relation to a "Projects" database, and each task shows its project while each project shows its tasks.
- **Backlinks:** Automatic reverse links showing all pages that link to the current page
- **Views:** The same database can be displayed as a table, board, calendar, gallery, or list, filtered and sorted differently for each view

**Design insight:** Notion's power comes from treating metadata as first-class. A task is not just a page with text; it is a structured record with status, assignee, due date, project relation, and tags. This structured metadata enables the views, filters, and rollups that make information discoverable.

### 5.2 Obsidian: Wiki-Links and Graph View

Obsidian is a local-first markdown knowledge base that emphasizes connections between notes.

**Key concepts:**
- **Wiki-links:** Double-bracket links [[like this]] that create connections between notes
- **Graph view:** A visual network diagram showing all notes as nodes and all links as edges, revealing clusters, orphans, and hub notes
- **Tags:** Hierarchical tags (#topic/subtopic) that enable faceted filtering
- **Maps of Content (MOCs):** Hub notes that curate links to related notes on a topic, serving as manually maintained indexes. An MOC for "Database Patterns" would link to individual notes on indexing, normalization, query optimization, and connection pooling.
- **Backlinks:** Every note shows which other notes link to it
- **Frontmatter:** YAML metadata at the top of each note for structured properties

**Design insight:** Obsidian proves that wiki-links plus search plus graph visualization covers most knowledge retrieval needs. The graph view is particularly powerful for discovering unexpected connections (two notes linked through a third that you did not realize was related). MOCs solve the "entry point" problem: when you arrive at a topic, where do you start?

### 5.3 Roam Research: Bidirectional Linking and Block References

Roam Research pioneered bidirectional linking as a core feature and introduced block-level references.

**Key concepts:**
- **Bidirectional links:** When note A links to note B, note B automatically shows a reference back to note A. Unlike backlinks in other tools, these are first-class navigation elements, not secondary UI.
- **Block references:** Any block (paragraph, bullet point) can be referenced from another note, creating a transclusion. The referenced block appears inline in the new context while remaining linked to its source.
- **Daily notes:** Every day gets an automatic page, encouraging chronological capture with topical links. Over time, the daily notes become a rich timeline cross-referenced to every topic discussed on each day.
- **Indentation as structure:** Nested bullet points create parent-child relationships that carry semantic meaning

**Design insight:** Block references solve a problem that page-level linking cannot: referencing a specific insight within a larger document. In a traditional wiki, you link to the whole page and hope the reader finds the relevant section. Block references link to the exact paragraph, creating precise connections. For AI knowledge systems, this suggests that the unit of linking should be smaller than the document: individual findings, decisions, or observations should be independently addressable and linkable.

### 5.4 Confluence: Spaces and Cross-Space Linking

Atlassian Confluence is an enterprise wiki organized around spaces (team or project containers) with pages, labels, and cross-space linking.

**Key concepts:**
- **Spaces:** Top-level containers, typically one per team or project
- **Page trees:** Hierarchical page structures within each space (parent > child > grandchild)
- **Labels:** Tags that work across spaces, enabling cross-cutting categorization
- **Cross-space linking:** Pages in one space can link to pages in any other space
- **Templates:** Standardized page structures for common document types (meeting notes, decision records, retrospectives)
- **Macros:** Dynamic content insertion (status badges, Jira issue lists, table of contents)

**Design insight:** Confluence demonstrates that cross-space (cross-project) linking is essential for organizations where work crosses team boundaries. The label system provides the associative organization layer on top of the hierarchical space/page structure. Templates enforce consistency, which improves discoverability because users know where to find specific information types within a standardized structure.

### 5.5 OneNote: Notebooks, Sections, and Pages

Microsoft OneNote uses a physical notebook metaphor with multiple organizational levels.

**Structure:** Notebook > Section Group > Section > Page > Subpage

**Key concepts:**
- **Freeform canvas:** Pages are infinite canvases where text, images, drawings, and clippings can be placed anywhere
- **Section tabs:** Color-coded tabs along the top, mimicking physical notebook dividers
- **Tagging:** Text-level tags (To Do, Important, Question, Critical) for in-page categorization
- **Quick Notes:** Unfiled notes captured rapidly and organized later

**Design insight:** OneNote's strength is low-friction capture (Quick Notes). Its weakness is poor cross-linking between notebooks. The lesson: capture should be frictionless and filing can happen later, but if cross-linking is not built into the core model, information silos form quickly.

### 5.6 Zettelkasten (Luhmann's Slip Box)

Niklas Luhmann, a German sociologist, used a paper-based Zettelkasten (slip box) system from the 1950s to the 1990s, producing approximately 90,000 notes that supported over 600 publications including roughly 60 books.

**Key concepts:**

**Atomicity:** Each note (Zettel) contains exactly one idea, expressed in the note-taker's own words. Not a quote, not a summary of a chapter, but a single thought.

**Sequence IDs and Branching:** Notes are numbered to indicate their position in a sequence of thought. The first note is 1. A continuation of that thought is 2. But a comment on note 1, or a branching idea, becomes 1a. A continuation of that branch becomes 1b. A comment on 1a becomes 1a1. This creates a tree structure of ideas where the numbering itself encodes the relationship.

**Hub Notes (Structure Notes/Index Notes):** Notes that serve as entry points to a topic, containing only links to other notes with brief descriptions of what each linked note covers. Similar to Obsidian's MOCs.

**Four types of relationships between notes:**
1. **Sequence links:** The next note in a train of thought (1 -> 2 -> 3)
2. **Branch links:** A comment or tangent on an existing note (1 -> 1a -> 1a1)
3. **Topic links:** Explicit connections between notes in different sequences ("see also 47b3")
4. **Hub links:** Connections from index/hub notes that organize access to a topic

**Why it worked:** The Zettelkasten's value came not from storing information but from forcing connections. Every new note required asking: "what existing notes does this relate to?" and physically inserting it near the most relevant note or linking it explicitly. The act of connecting creates new understanding.

**AI parallel:** The Zettelkasten is the closest historical analog to what METIS needs. Atomic knowledge entries (one insight per remember() call), typed relationships (link_knowledge with relation types), hub structures (MOCs in the vault, component-level workfile groupings), and sequence encoding (session ordering, feature-to-task chains) all have Zettelkasten equivalents. The gap: METIS does not yet enforce atomicity (a single remember() call can contain multiple unrelated insights) or require linking at creation time (remember() auto-links based on similarity but does not force the user to specify connections).

---

## 6. Work Context Assembly

The core problem: given a person working on "Task X," how do you automatically assemble the right context from multiple storage systems?

### 6.1 Personal Information Management (PIM) Research

PIM research studies how individuals organize, maintain, and re-find their own information. Key findings from decades of research:

**The fragmentation problem:** People's information is scattered across email, files, notes, bookmarks, messages, and paper. No single system contains everything relevant to a task. Studies show that knowledge workers spend 15-25% of their time searching for information they know they have but cannot locate.

**Filing vs piling:** Research identifies two dominant strategies. "Filers" maintain organized folder hierarchies and file immediately. "Pilers" accumulate information in a few locations (desktop, inbox) and rely on search or memory to find things later. Most people are hybrids, filing important items and piling everything else.

**Prospective vs retrospective organization:** Filers organize prospectively (deciding where something will go based on anticipated future need). This fails when future needs are unpredictable. Retrospective organization (tagging or searching when you need something) handles unpredictable needs but requires good metadata and search capabilities.

**AI parallel:** An AI session is a "piler" by nature. Knowledge accumulates during the session with minimal organization. The challenge is to impose enough structure during capture (store_session_fact type categorization, workfile component assignment) to enable retrospective retrieval without disrupting the flow of work. The remember() function's auto-routing attempts to be a low-friction "filer" that operates transparently.

### 6.2 Activity-Based Computing

Activity-Based Computing (ABC) is a research paradigm from the early 2000s (Bardram et al., ITU Copenhagen) that argues computers should organize resources by activity rather than by application or file type.

**The problem:** When a user switches from "writing a report" to "debugging a server issue," they must manually close applications, open new ones, find relevant files, restore browser tabs, and reconstruct their working context. The computer provides no support for this transition.

**The ABC solution:** An "activity" is a first-class computing object that aggregates all resources needed for a task: documents, applications, browser tabs, communication channels, and tool state. Switching activities restores the complete working context instantly.

**Research systems:**
- **Rooms (1986):** Virtual desktops grouped by task, one of the earliest implementations
- **Task Gallery (2000):** 3D task-based window management
- **GroupBar (2004):** Task-bar grouping of related windows
- **Activity-Based Computing framework (2006):** Full activity management with suspend/resume, sharing, and multi-device roaming

**Key finding from hospital deployments:** In medical settings, clinicians switched activities an average of 72 times per 8-hour shift. Activity-based systems reduced context reconstruction time by 40-60% compared to traditional desktop computing.

**AI parallel:** An AI session typically involves multiple "activities" (working on SQL, then deidentification, then pipeline). The workfile system's component grouping provides activity-scoped context, but switching between activities within a session is not explicitly supported. A future enhancement could track which "activity" the user is currently working on within a session and automatically surface relevant workfiles, knowledge, and session facts for that activity.

### 6.3 Project Spaces in Modern Tools

Modern project management tools create scoped contexts that automatically assemble relevant information:

| Tool | Scoping Mechanism | What Gets Assembled |
|------|-------------------|-------------------|
| **Linear** | Project + Cycle | Issues, PRs, documents, team members |
| **Jira** | Project + Board | Issues, sprints, epics, roadmap, releases |
| **Notion** | Database views | Tasks, docs, people, filtered by project tag |
| **GitHub** | Repository + Project board | Issues, PRs, discussions, wiki, actions |
| **Asana** | Project + Portfolio | Tasks, milestones, goals, status updates |

**Common pattern:** All these tools provide a "project home" that aggregates information from multiple subsystems (issues, code, docs, communication) into a single scoped view. The user does not need to manually navigate to each subsystem; the project space assembles the relevant subset automatically.

**AI parallel:** get_work_context(scope="project") attempts this aggregation but is limited to work tracking items (features, tasks, feedback). A richer project space would also include relevant workfiles, recent knowledge entries, active session facts, and vault documents related to the project.

### 6.4 Smart Folders and Saved Searches

Smart folders (macOS Finder, Outlook, Gmail) are dynamically assembled views based on criteria rather than manual filing.

**Characteristics:**
- Items do not move; the smart folder is a saved query that shows matching items wherever they are stored
- Criteria can combine metadata fields (date, type, author) with content search (full-text keywords)
- Smart folders update automatically as new matching items are created
- A single item can appear in multiple smart folders without duplication

**Power:** Smart folders decouple organization from storage. The physical location of a record becomes irrelevant; what matters is its metadata. This eliminates the "one file, one place" limitation of hierarchical filing.

**AI parallel:** recall_memories(query) is a smart folder: a dynamic assembly of relevant knowledge from across all tiers based on semantic similarity. search_workfiles(query) is another. The concept suggests that METIS should support saved/named queries that users (or the system) can define and reuse: "show me everything about timezone handling" as a persistent smart folder that automatically includes new knowledge as it is created.

### 6.5 Tagging vs Folders: Why Both Are Needed

The tags-versus-folders debate has been studied extensively. Research consistently shows:

**Folders provide:**
- Navigability (browse the hierarchy to explore what exists)
- Containment (everything in a folder shares a context)
- Exclusive classification (forces a decision about primary location)
- Spatial memory (people remember "it was in the third folder on the left")

**Tags provide:**
- Multi-classification (one item, many categories)
- Faceted filtering (show me items tagged both "database" and "performance")
- Emergent organization (tags can be added after the fact without restructuring)
- Cross-cutting concerns (a "gotcha" tag spans all projects and all components)

**Research finding:** Users who use both folders and tags together retrieve information faster than users who rely on either system alone. Folders handle the common case (browsing known categories), and tags handle the exceptional case (finding cross-cutting items that span categories).

**AI parallel:** The workfile system uses folders (project > component hierarchy) for navigability and embeddings for associative retrieval. The knowledge vault uses folders (00-Inbox through 40-Procedures) plus YAML tags. The cognitive memory system uses tiers (hierarchical) plus semantic search (associative). All three systems already implement the "both" approach, though not in a unified way.

### 6.6 Context Switching Costs

Research on context switching and task interruption reveals significant cognitive costs:

**Key findings:**
- Switching between tasks incurs a "resumption lag" of 15-25 minutes to fully re-engage with the interrupted task (Mark, Gonzalez, & Harris, CHI 2005)
- The cost increases with the complexity of both the interrupted and interrupting tasks
- Information workers switch tasks an average of every 3-5 minutes, with 57% of tasks interrupted before completion
- After an interruption, people work faster (to compensate) but produce more errors and experience more stress
- The primary cost is not the switch itself but the time spent reconstructing mental context ("where was I? what was I about to do?")

**Mitigating strategies identified in research:**
1. **State capture:** Recording what you were doing and what you planned to do next before switching
2. **Environmental cues:** Leaving visual indicators of your current state (open documents, cursor position, written notes)
3. **Defer switching:** Completing the current logical unit before switching
4. **Context restoration aids:** Tools that help reconstruct the pre-interruption state

**AI parallel:** An AI session's context is the model's prompt. When context compaction occurs (the AI equivalent of a task interruption), the PreCompact hook attempts state capture by injecting active work items, session facts, and session notes. The resume strategy relies on the compacted context plus any persisted state. The workfile system specifically addresses context switching between sessions: stash() captures state, unstash() restores it. Within a session, switching between work contexts (SQL to deidentification to pipeline) does not have explicit support; the model must reconstruct from its prompt history or from stored facts.

---

## 7. Key Principles for AI Knowledge Assembly

Distilled from the research above, these principles should guide the design of METIS's knowledge management and context assembly systems.

### Principle 1: Multi-Axis Classification

**From:** Subject filing, tags vs folders research, Notion databases

Every knowledge item needs both hierarchical placement (where it lives in the structure) AND associative classification (what topics it relates to). Hierarchical placement provides navigability; associative classification provides discoverability across structural boundaries.

**Implementation:** The workfile system's (project, component, title) provides hierarchy. Semantic embeddings provide association. What is missing is explicit tagging that enables faceted filtering ("show me all workfiles tagged 'performance' across all components").

### Principle 2: Metadata Richness Determines Retrieval Quality

**From:** ISO 15489/23081, EDRMS best practices, PIM research

Sparse metadata (just a title and content) forces retrieval to rely entirely on content analysis (full-text search, embeddings). Rich metadata (type, creator, creation context, relationships, access history) enables precise filtering that narrows the search space before content analysis. The most discoverable records are those with the richest metadata.

**Implementation:** Every knowledge item should capture: what it is (type), who created it (session/creator), why it was created (the triggering context), what it relates to (explicit links), and how important it is (access patterns, confidence scores).

### Principle 3: Lifecycle Management Prevents Information Overload

**From:** Records lifecycle, retention schedules, disposition

Without active lifecycle management, knowledge stores grow monotonically until retrieval quality degrades. Every item competes for retrieval attention. The solution is not to create less knowledge but to manage its progression through lifecycle stages: active capture, regular use, semi-active reference, archive, and eventual disposition.

**Implementation:** The cognitive memory system's consolidate_memories() implements lifecycle transitions. The key is that this must be automatic and continuous, not dependent on manual curation. Time-based decay, access-frequency-based promotion, and confidence-threshold archival all contribute to keeping the active knowledge set manageable.

### Principle 4: Cross-References Carry Information Value

**From:** Cross-reference cards, Zettelkasten, Roam Research bidirectional linking

The relationships between knowledge items are as valuable as the items themselves. "These two items are related" is itself a piece of knowledge. "This decision superseded that earlier decision" is critical context that neither decision document contains on its own. Systems that track only items and not their relationships lose the connective tissue that makes knowledge navigable.

**Implementation:** The knowledge relations system (link_knowledge) provides explicit typed relationships. The workfile system lacks explicit cross-references. Session facts lack relationships entirely. A unified relationship layer across all knowledge stores would enable queries like "what is connected to this item?" regardless of which store the connected items live in.

### Principle 5: Access Patterns Reveal Importance

**From:** Out cards, charge-out systems, color-coded filing, PIM research

Records that are accessed frequently are important. Records that are accessed together are related (co-access patterns). Records that were recently accessed are more likely to be relevant. Records that were never accessed after creation may be noise.

**Implementation:** access_count and last_accessed_at on workfiles capture frequency and recency. What is not captured: co-access patterns (which workfiles are typically retrieved together in the same session), access source (was it retrieved by a human query or by an automatic process), and access outcome (did the retrieved knowledge actually help, or was it irrelevant to the query?).

### Principle 6: Activity-Scoped Context Assembly

**From:** Activity-based computing, project spaces, smart folders

The unit of context assembly should be the user's current activity, not the storage location of individual items. When the user is working on "timezone handling in the pipeline," the system should automatically assemble relevant workfiles (pipeline component), knowledge entries (timezone patterns), session facts (pipeline configuration), and vault documents (timezone documentation) into a single coherent context, regardless of where each item is physically stored.

**Implementation:** recall_memories(query) provides activity-scoped retrieval from the knowledge store. get_work_context provides activity-scoped retrieval from the work tracking system. search_workfiles provides activity-scoped retrieval from workfiles. These are three separate systems with separate queries. A unified context assembly function that queries all three (plus vault RAG) for a single activity description would implement true activity-scoped assembly.

### Principle 7: Provenance Preserves Trust

**From:** Provenance principle, chain of custody, ISO 15489 authenticity

Knowing who created a piece of knowledge, when, and in what context determines whether it should be trusted. A "fact" remembered from a session where the user was exploring hypotheticals has different reliability than one recorded during a production debugging session. Provenance metadata (creator, creation context, verification status, confidence level) enables the system to weight knowledge appropriately during retrieval.

**Implementation:** session_id on workfiles and knowledge entries provides creator provenance. The knowledge tier system provides implicit reliability weighting (LONG tier = more trusted than SHORT tier). What is missing: explicit confidence tracking that reflects how a piece of knowledge was created (observed from code vs. told by user vs. inferred by AI) and whether it has been verified against reality.

---

## References and Further Reading

### Standards
- ISO 15489-1:2016 Information and documentation -- Records management -- Part 1: Concepts and principles
- ISO 23081-1:2006 Metadata for records -- Part 1: Principles
- ISO 23081-2:2009 Metadata for records -- Part 2: Conceptual and implementation issues
- ANSI/ARMA 12-2005 Establishing Alphabetic, Numeric and Subject Filing Systems

### Academic Research
- Bardram, J.E. (2009). Activity-Based Computing for Medical Work in Hospitals. ACM TOCHI.
- Bardram, J.E. et al. (2006). Support for Activity-Based Computing in a Personal Computing Operating System. CHI 2006.
- Gonzalez, V.M. & Mark, G. (2004). Constant, Constant, Multi-tasking Craziness: Managing Multiple Working Spheres. CHI 2004.
- Mark, G., Gonzalez, V.M., & Harris, J. (2005). No Task Left Behind? Examining the Nature of Fragmented Work. CHI 2005.
- Bergman, O. et al. (2008). Folder vs Tag Preference in Personal Information Management. JASIST.
- Luhmann, N. (1981). Kommunikation mit Zettelkasten. (Communication with Slip Boxes)

### Practitioner Resources
- ARMA International. Records and Information Management Core Competencies.
- Society of American Archivists. Dictionary of Archives Terminology.
- National Archives (US). Principles of Arrangement.
- zettelkasten.de - Introduction to the Zettelkasten Method

### Related METIS Documents
- [[augmentation-layer-research]] - Context engineering and cognitive architecture research
- [[system-product-definition]] - METIS product definition and knowledge model
- [[cognitive-memory-processes]] - Three-tier memory system design

---

**Version**: 1.0
**Created**: 2026-03-10
**Updated**: 2026-03-10
**Location**: knowledge-vault/10-Projects/Project-Metis/research/filing-records-management-research.md