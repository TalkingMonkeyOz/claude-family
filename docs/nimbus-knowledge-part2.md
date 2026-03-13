---
projects:
- claude-family
- nimbus-mui
tags:
- mcp
- nimbus
- shutdown-review
- migration
synced: false
---

# nimbus-knowledge: Migration and Recommendation

Part 2 of 2. See [overview](nimbus-knowledge-shutdown-review.md) and [data/dependents](nimbus-knowledge-part1.md).

---

## Migration Feasibility

### What Already Exists in claude.*

`migrate_entities.sql` already created `claude.entity_types`, `claude.entities`, and `claude.entity_relationships`. The `odata_entity` type is already registered — the conceptual home for this data exists.

### Data Migration Mapping

| nimbus_context table | Target | Approach |
|----------------------|--------|----------|
| `api_entities` (366) | `claude.entities` type=`odata_entity` | Store properties JSONB inline per entity to avoid 7K separate rows |
| `api_properties` (7,357) | Inline in entity `properties` JSONB | Aggregate as array per entity; do not create 7,357 individual entity rows |
| `code_patterns` (6) | `claude.knowledge` LONG tier | `remember()` with type='pattern' |
| `project_learnings` (6) | `claude.knowledge` LONG tier | `remember()` with type='pattern' or 'gotcha' |
| `project_facts` (22) | `claude.knowledge` LONG tier | `remember()` with type='constraint' or 'pattern' |

The api_properties-as-JSONB approach avoids creating 7,357 entity rows with embeddings (which would cost ~$0.04 in Voyage AI calls and add noise to semantic search). One entity row per OData entity, with all properties stored in the `properties` field.

### Migration Effort

| Task | Effort |
|------|--------|
| Migrate 34 small-table rows via `remember()` | Low — one session, no new code |
| Write migration SQL for api_entities with inline properties | Medium |
| Add `get_entity_schema` equivalent to project-tools | Medium — format output correctly |
| Add `search_entities` equivalent to project-tools | Low — wrapper around entity search |
| Embed new entities via existing pipeline | Low — automated |
| Update 3 active project CLAUDE.md files | Low |
| Update 3 settings.local.json files | Low |

---

## Risks

| Risk | Severity | Notes |
|------|----------|-------|
| Ergonomics of entity lookup degrade | Medium | Current tool groups properties into key/required/optional/navigation sections — genuinely useful; raw JSONB fetch loses this |
| nimbus-odata-configurator is heaviest user and actively developed | Medium | The app exists specifically to browse OData entities; losing the lookup tool mid-development would hurt |
| api_properties relational structure flattens to JSONB | Low | In practice every lookup is per-entity anyway |
| nimbus_context schema has legacy dependencies | Low | Old `03_link_schemas.sql` references it but those scripts are archived |

---

## Shutdown Steps (When Ready)

1. **Migrate small tables** — run 34 rows through `remember()` for patterns, learnings, facts
2. **File a feature** — add `get_entity_schema` and `search_entities` to project-tools targeting `claude.entities`
3. **Run data migration** — SQL INSERT SELECT from `nimbus_context.api_entities` into `claude.entities` with JSONB property aggregation
4. **Run embed pipeline** — `python scripts/embed_vault_documents.py` picks up new entity rows
5. **Update active project configs** — remove `nimbus-knowledge` from `enabledMcpjsonServers` and `mcp_configs` in: nimbus-odata-configurator, monash-nimbus-reports, nimbus-mui, nimbus-import, nimbus-user-loader
6. **Update CLAUDE.md files** — replace nimbus-knowledge tool references with recall_memories() and entity search equivalents in 3 active projects
7. **Deprecate schema** — add `COMMENT ON SCHEMA nimbus_context IS 'DEPRECATED ...'`; drop after 30 days of no activity
8. **Archive server** — `C:\Projects\nimbus-mui\mcp-server\` can be left in place (no harm) or removed

---

## Recommendation

**Migrate the 34 small-table rows now. Keep the entity server running until tooling replacement ships.**

The learnings (6), facts (22), and patterns (6) are exactly what the cognitive memory system is for. Moving them to `claude.knowledge` LONG tier means they surface automatically during Nimbus sessions via RAG — without any explicit tool call. This is net better than the current explicit `get_facts()` / `get_learnings()` calls. Cost: one session, no new code.

The 366-entity / 7,357-property dataset is a different category — it is structured reference data with a purpose-built query interface. The odata-configurator project is built around `get_entity_schema`. Retiring the server before the replacement tools exist would break active development. The current server is stable, the data is static, and the maintenance burden is low.

Do not leave this running indefinitely. The server lives in `nimbus-mui`, not in infrastructure. That is an architectural problem — shared tooling should live in claude-family. The full shutdown is the right long-term outcome; this review defines the correct sequencing to get there without disrupting active Nimbus work.

---

**Version**: 1.0
**Created**: 2026-03-13
**Updated**: 2026-03-13
**Location**: C:\Projects\claude-family\docs\nimbus-knowledge-part2.md
