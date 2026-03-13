---
projects:
- claude-family
- project-metis
tags:
- research
- data-model
- library-science
synced: false
---

# Data Structure Research: Historical Approaches

Part of [data-structure-research.md](data-structure-research.md) — library science and records management.

---

## Dublin Core (15 Universal Elements)

15 metadata elements designed to describe ANY resource type: Title, Creator, Subject, Description, Publisher, Contributor, Date, Type, Format, Identifier, Source, Language, Relation, Coverage, Rights.

Key design principles:
- All elements are OPTIONAL and REPEATABLE
- Works for books, maps, music, datasets, software, images — anything
- Deliberately simple; "Qualified Dublin Core" adds refinements for specificity

**Relevance**: Maps directly to our shared columns (title, description, type, source, tags, created_at). Universal enough for discovery; type-specific detail lives in JSONB.

## MARC (Machine-Readable Cataloging)

Used for 60+ years across billions of records. Separate record formats for books, serials, maps, music, computer files. Each has distinct field definitions.

**Cautionary tale**: Adding new media types requires multi-year committee processes, format extensions, software updates across thousands of systems. This is the per-type table failure mode — every new type has massive overhead.

**What MARC got right**: Universal container structure (leader + directory + variable fields) with type-specific content in the variable fields. Exactly the shared-columns + JSONB pattern.

## FRBR (Functional Requirements for Bibliographic Records)

4-level hierarchy:
- **Work**: Abstract intellectual creation (Beethoven's 9th)
- **Expression**: A realization (a specific performance recording)
- **Manifestation**: Physical embodiment (a specific CD release)
- **Item**: Single exemplar (your copy of that CD)

**Relevance**: Same content at multiple abstraction levels. An OData entity could be a Work (abstract ScheduleShift concept), Expression (v2.3 schema), Manifestation (JSON Schema doc), or Item (test instance). Entity relationships model these levels.

## Dewey Decimal / Library of Congress

Both are **hierarchical classification** systems. Dewey uses 10 main classes with decimal subdivision. LoC uses 21 letter-based classes.

**Cross-cutting topic problem**: A book on "political history of France" could go under Politics, History, or France. Libraries solve this with multiple access points (subject headings) — analogous to our tags + semantic search.

**Lesson**: Rigid single-hierarchy classification fails for real data. Faceted classification (Ranganathan) with independent dimensions (topic, time, place, form) works better. Our entity_type + tags + properties + embedding gives 4 independent access paths.

## ISO 15489 (Records Management)

Key principle: "Classification provides discovery, not storage structure. Store data in its natural form; make it findable through metadata."

Physical filing systems used:
- **Alphabetic**: Simple, direct access. Fails with growth.
- **Numeric (terminal digit)**: Even distribution, scalable. Requires an index.
- **Subject**: Groups related materials. Cross-cutting problem.
- **Alphanumeric**: Hybrid (our `project/component/title` triple).

**Relevance**: Store entities in their natural JSONB form. Make them findable through shared columns, tags, embeddings, and tsvector search.

---

**Version**: 1.0
**Created**: 2026-03-13
**Updated**: 2026-03-13
**Location**: docs/research/data-structure-historical.md
