# Vault-to-DB Knowledge Mapping

Factual mapping of what knowledge exists in the database vs the vault for the top 5 projects.

## Coverage Summary

| Project | DB Knowledge | Domain Concepts | Workfiles | Vault Files | DB Coverage |
|---------|-------------|-----------------|-----------|-------------|-------------|
| claude-family | 15 entries | 1 | 10 | 57 (non-archive) | Partial |
| nimbus-mui | 15 entries | 7 + 15 OData | 10 | 0 (no vault folder) | Complete |
| nimbus-import | 15 entries | 0 (shares nimbus) | 0 | 0 (empty folder) | Complete |
| nimbus-user-loader | 15 entries | 0 (shares nimbus) | 0 | 0 (no vault folder) | Complete |
| project-metis | 15 entries | 20+ entities | 10 | 140+ files | Low |

## Key Findings

- **Nimbus projects**: Well-served by DB. No vault gaps.
- **claude-family**: Vault has ~57 design/architecture docs with no DB equivalent (identity system, session user stories, unified storage design, hook requirements).
- **project-metis**: Massive vault (140+ files). Gate deliverables are in DB as entities, but research, design docs, and governance docs are vault-only.

## Per-Project Details

- [claude-family detail](vault-to-db-mapping-claude-family.md)
- [nimbus projects detail](vault-to-db-mapping-nimbus.md)
- [project-metis detail](vault-to-db-mapping-metis.md)

---

**Version**: 1.0
**Created**: 2026-04-11
**Updated**: 2026-04-11
**Location**: docs/vault-to-db-mapping.md
