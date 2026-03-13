---
projects:
- claude-family
- project-metis
tags:
- research
- data-model
- knowledge-graphs
- semantic-web
synced: false
---

# Data Structure Research: Knowledge Graphs & Semantic Web

Part of [data-structure-research.md](data-structure-research.md) — Wikidata, RDF, JSON-LD, Schema.org.

---

## Wikidata — Strongest Evidence for Universal Structure

100M+ wildly heterogeneous entities (people, chemicals, cities, concepts, artworks) in ONE structure.

**Data model**:
- **Items**: Q-numbered entities (Q80 = Tim Berners-Lee)
- **Properties**: P-numbered predicates (P31 = instance of)
- **Statements**: Item + Property + Value + Qualifiers + References
- **No separate tables per type** — `instance of` (P31) is the type discriminator

Every entity (chemical compound and person) has the same row structure. They differ only in which properties are attached.

**Key insight**: If Wikidata handles 100M+ heterogeneous entities in one structure, our system (hundreds to low thousands) certainly can.

**Caveat**: Wikidata is read-heavy with batch writes, not transactional. But so is our system (recall >> remember).

## DBpedia

Maps Wikipedia infoboxes to a unified RDF graph. Different infobox types (Person, City, Film) map to different ontology classes, but storage is one triple store.

Same pattern: universal storage, type expressed as metadata.

## Schema.org — Type Registry Inspiration

827 types, 1,528 properties, 14 datatypes, 94 enumerations — ALL in ONE vocabulary.

Key features:
1. **Multiple inheritance**: `LocalBusiness` is both `Organization` and `Place`
2. **Flexible property domains**: Properties can apply to multiple types
3. **Self-describing**: Schema describes itself using its own vocabulary
4. **Pragmatic**: Properties are "guidelines" — entities CAN have extra properties

**Relevance**: Our type registry should follow this pattern. Types with optional inheritance, properties with flexible application, pragmatic approach that allows extra JSONB keys beyond the schema.

## JSON-LD

Serialization format: JSON objects with `@context` (maps property names to URIs) and `@type` (classifies entity).

Conceptually identical to our `entity_type` + `properties` JSONB approach. JSON-LD proves the pattern works at web scale.

## RDF/OWL — What Failed

Triple stores (Subject-Predicate-Object) are powerful but:
- Triples cannot carry properties on relationships (need reification)
- No built-in provenance
- Wildly variable query performance on heterogeneous data
- SPARQL has a massive tooling gap versus SQL
- Practical query optimization is extremely difficult

**Industry moved away** from pure RDF toward JSON-LD (RDF concepts in JSON syntax) and property graphs (labeled edges with properties).

**Verdict**: Don't adopt RDF. Take the conceptual patterns (universal entities, typed properties, flexible schema) and implement in PostgreSQL + JSONB.

---

## Sources

- Wikidata Data Model (mediawiki.org)
- Wikidata for Scholarly Communication (IU Press)
- Wikibase DataModel documentation
- Schema.org Data Model docs
- JSON-LD 1.1 W3C Specification
- DBpedia Ontology

---

**Version**: 1.0
**Created**: 2026-03-13
**Updated**: 2026-03-13
**Location**: docs/research/data-structure-knowledge-graphs.md
