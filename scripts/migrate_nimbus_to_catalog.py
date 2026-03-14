#!/usr/bin/env python3
"""
Migrate nimbus-knowledge MCP data to the universal Entity Catalog.

Source: nimbus_context schema (api_entities, api_properties, api_field_mappings,
        project_facts, project_learnings, code_patterns)
Target: claude.entities (via catalog() MCP tool pattern) + claude.knowledge (via remember())

This script reads directly from the database and writes to claude.entities,
bypassing MCP tools for bulk performance. Uses the same entity_type registry
and embedding logic as the catalog() MCP tool.

Usage:
    python scripts/migrate_nimbus_to_catalog.py [--dry-run] [--limit N]

Author: Claude Family
Date: 2026-03-14
"""

import json
import os
import sys
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('nimbus_migration')

# Project ID for nimbus-mui (entities are project-scoped)
NIMBUS_PROJECT = 'nimbus-mui'


def get_project_id(conn, project_name):
    cur = conn.cursor()
    cur.execute("SELECT project_id FROM claude.projects WHERE project_name = %s", (project_name,))
    row = cur.fetchone()
    if not row:
        return None
    return row['project_id'] if isinstance(row, dict) else row[0]


def get_entity_type_id(conn, type_name):
    cur = conn.cursor()
    cur.execute("SELECT type_id FROM claude.entity_types WHERE type_name = %s", (type_name,))
    row = cur.fetchone()
    if not row:
        return None
    return row['type_id'] if isinstance(row, dict) else row[0]


def get_embedding(text):
    """Generate Voyage AI embedding for entity search."""
    try:
        import voyageai
        client = voyageai.Client()
        result = client.embed([text], model="voyage-3", input_type="document")
        return result.embeddings[0]
    except Exception as e:
        logger.warning(f"Embedding failed: {e}")
        return None


def migrate_odata_entities(conn, dry_run=False, limit=None):
    """Migrate api_entities + api_properties + field_mappings → claude.entities"""
    cur = conn.cursor()

    # Get entity type ID for odata_entity
    odata_type_id = get_entity_type_id(conn, 'odata_entity')
    if not odata_type_id:
        logger.error("Entity type 'odata_entity' not found in claude.entity_types")
        return 0

    project_id = get_project_id(conn, NIMBUS_PROJECT)
    if not project_id:
        logger.error(f"Project '{NIMBUS_PROJECT}' not found")
        return 0

    # Load all entities
    query = """
        SELECT e.entity_id, e.entity_name, e.entity_set_name, e.namespace,
               e.base_type, e.is_open_type, e.has_stream, e.rest_endpoint,
               e.http_methods, e.description
        FROM nimbus_context.api_entities e
        ORDER BY e.entity_name
    """
    if limit:
        query += f" LIMIT {int(limit)}"

    cur.execute(query)
    entities = cur.fetchall()
    logger.info(f"Found {len(entities)} OData entities to migrate")

    # Helper to access row by name or index
    def col(row, name, idx):
        return row[name] if isinstance(row, dict) else row[idx]

    # Pre-load all field mappings
    cur.execute("SELECT entity_name, odata_field, rest_field, data_type, notes FROM nimbus_context.api_field_mappings")
    mappings_raw = cur.fetchall()
    mappings_by_entity = {}
    for m in mappings_raw:
        ename = col(m, 'entity_name', 0)
        if ename not in mappings_by_entity:
            mappings_by_entity[ename] = []
        mappings_by_entity[ename].append({
            'odata_field': col(m, 'odata_field', 1), 'rest_field': col(m, 'rest_field', 2),
            'data_type': col(m, 'data_type', 3), 'notes': col(m, 'notes', 4)
        })

    migrated = 0
    for entity in entities:
        eid = col(entity, 'entity_id', 0)
        name = col(entity, 'entity_name', 1)
        set_name = col(entity, 'entity_set_name', 2)
        namespace = col(entity, 'namespace', 3)
        base_type = col(entity, 'base_type', 4)
        is_open = col(entity, 'is_open_type', 5)
        has_stream = col(entity, 'has_stream', 6)
        rest_endpoint = col(entity, 'rest_endpoint', 7)
        http_methods = col(entity, 'http_methods', 8)
        description = col(entity, 'description', 9)

        # Load properties for this entity
        cur.execute("""
            SELECT property_name, property_type, is_key, is_nullable, max_length, description
            FROM nimbus_context.api_properties
            WHERE entity_id = %s
            ORDER BY is_key DESC, property_name
        """, (eid,))
        props = cur.fetchall()

        # Build properties dict
        fields = []
        key_fields = []
        for p in props:
            field = {
                'name': col(p, 'property_name', 0),
                'type': col(p, 'property_type', 1),
                'nullable': col(p, 'is_nullable', 3)
            }
            if col(p, 'max_length', 4):
                field['max_length'] = col(p, 'max_length', 4)
            if col(p, 'description', 5):
                field['description'] = col(p, 'description', 5)
            fields.append(field)
            if col(p, 'is_key', 2):
                key_fields.append(col(p, 'property_name', 0))

        # Get field mappings for this entity
        entity_mappings = mappings_by_entity.get(name, [])

        # Build catalog properties
        properties = {
            'name': name,
            'entity_set': set_name,
            'namespace': namespace or 'Default',
            'field_count': len(fields),
            'key_fields': key_fields,
            'fields': fields,
            'source': 'nimbus-odata'
        }
        if base_type:
            properties['base_type'] = base_type
        if rest_endpoint:
            properties['rest_endpoint'] = rest_endpoint
        if http_methods:
            properties['http_methods'] = http_methods
        if description:
            properties['description'] = description
        if entity_mappings:
            properties['field_mappings'] = entity_mappings

        # Build display name and search text
        display_name = f"{name} ({set_name})" if set_name and set_name != name else name
        search_text = f"OData entity {name} in namespace {namespace or 'Default'}. {len(fields)} fields. Keys: {', '.join(key_fields)}. {description or ''}"

        if dry_run:
            logger.info(f"[DRY RUN] Would catalog: {display_name} ({len(fields)} fields, {len(entity_mappings)} mappings)")
            migrated += 1
            continue

        # Generate embedding
        embedding = get_embedding(search_text)

        # display_name is GENERATED ALWAYS from properties->>'name' || properties->>'title'
        # So we just need properties.name to be set (which it is)

        # Check if already exists (dedup by type + properties->name)
        cur.execute("""
            SELECT entity_id FROM claude.entities
            WHERE entity_type_id = %s AND properties->>'name' = %s
        """, (odata_type_id, name))
        existing = cur.fetchone()

        if existing:
            existing_id = existing['entity_id'] if isinstance(existing, dict) else existing[0]
            cur.execute("""
                UPDATE claude.entities
                SET properties = %s::jsonb,
                    search_vector = to_tsvector('english', %s),
                    embedding = %s,
                    updated_at = NOW()
                WHERE entity_id = %s
            """, (json.dumps(properties), search_text, embedding, existing_id))
            logger.debug(f"Updated: {display_name}")
        else:
            cur.execute("""
                INSERT INTO claude.entities (entity_type_id, project_id,
                    properties, tags, search_vector, embedding, created_at)
                VALUES (%s, %s, %s::jsonb, %s, to_tsvector('english', %s), %s, NOW())
            """, (odata_type_id, project_id,
                  json.dumps(properties),
                  ['nimbus', 'odata', 'time2work'],
                  search_text, embedding))
            logger.debug(f"Inserted: {display_name}")

        migrated += 1
        if migrated % 50 == 0:
            conn.commit()
            logger.info(f"Progress: {migrated}/{len(entities)} entities migrated")

    conn.commit()
    logger.info(f"OData migration complete: {migrated} entities")
    return migrated


def migrate_knowledge(conn, dry_run=False):
    """Migrate project_facts, project_learnings, code_patterns → claude.knowledge via remember() pattern"""
    cur = conn.cursor()
    project_id = get_project_id(conn, NIMBUS_PROJECT)
    migrated = 0

    def col(row, name, idx):
        return row[name] if isinstance(row, dict) else row[idx]

    # Migrate project_facts (columns: fact_id, project_id, fact_type, fact_category, title, description, ...)
    cur.execute("SELECT title, description, fact_type, fact_category FROM nimbus_context.project_facts")
    facts = cur.fetchall()
    for f in facts:
        content = f"{col(f, 'title', 0)}: {col(f, 'description', 1) or ''}"
        if col(f, 'fact_category', 3):
            content += f" (Category: {col(f, 'fact_category', 3)})"

        if len(content) < 80:
            logger.debug(f"Skipping short fact: {content[:50]}")
            continue

        if dry_run:
            logger.info(f"[DRY RUN] Would remember fact: {content[:80]}...")
            migrated += 1
            continue

        # Check for existing similar knowledge
        embedding = get_embedding(content)
        if embedding:
            cur.execute("""
                INSERT INTO claude.knowledge (knowledge_id, title, description, knowledge_type, knowledge_category,
                    source, applies_to_projects, confidence_level, tier, embedding, created_at)
                VALUES (gen_random_uuid(), %s, %s, 'fact', 'nimbus', 'nimbus-knowledge-migration',
                    %s, 75, 'mid', %s, NOW())
                ON CONFLICT DO NOTHING
            """, (col(f, 'title', 0), content, ['nimbus-mui', 'nimbus-import', 'monash-nimbus-reports'],
                  embedding))
            migrated += 1

    # Migrate project_learnings (columns: learning_id, project_id, learning_type, situation, action_taken, outcome, lesson_learned, ...)
    cur.execute("SELECT situation, action_taken, outcome, lesson_learned, learning_type FROM nimbus_context.project_learnings")
    learnings = cur.fetchall()
    for l in learnings:
        situation = col(l, 'situation', 0) or ''
        lesson = col(l, 'lesson_learned', 3) or ''
        content = f"{situation}: {lesson}"
        outcome = col(l, 'outcome', 2)
        if outcome:
            content += f" (Outcome: {outcome})"

        if len(content) < 80:
            continue

        if dry_run:
            logger.info(f"[DRY RUN] Would remember learning: {content[:80]}...")
            migrated += 1
            continue

        embedding = get_embedding(content)
        if embedding:
            cur.execute("""
                INSERT INTO claude.knowledge (knowledge_id, title, description, knowledge_type, knowledge_category,
                    source, applies_to_projects, confidence_level, tier, embedding, created_at)
                VALUES (gen_random_uuid(), %s, %s, 'learned', 'nimbus', 'nimbus-knowledge-migration',
                    %s, 75, 'mid', %s, NOW())
                ON CONFLICT DO NOTHING
            """, (situation[:100] or 'nimbus learning', content, ['nimbus-mui', 'nimbus-import', 'monash-nimbus-reports'],
                  embedding))
            migrated += 1

    # Migrate code_patterns
    cur.execute("SELECT pattern_name, description, code_example, use_when FROM nimbus_context.code_patterns")
    patterns = cur.fetchall()
    for p in patterns:
        content = f"{col(p, 'pattern_name', 0)}: {col(p, 'description', 1) or ''}"
        if len(content) < 80:
            continue

        if dry_run:
            logger.info(f"[DRY RUN] Would remember pattern: {content[:80]}...")
            migrated += 1
            continue

        embedding = get_embedding(content)
        use_when = col(p, 'use_when', 3)
        if use_when:
            content += f" Use when: {use_when}"
        code_example = col(p, 'code_example', 2) or ''
        if embedding:
            cur.execute("""
                INSERT INTO claude.knowledge (knowledge_id, title, description, knowledge_type, knowledge_category,
                    source, applies_to_projects, confidence_level, tier, code_example, embedding, created_at)
                VALUES (gen_random_uuid(), %s, %s, 'pattern', 'nimbus', 'nimbus-knowledge-migration',
                    %s, 80, 'long', %s, %s, NOW())
                ON CONFLICT DO NOTHING
            """, (col(p, 'pattern_name', 0), content, ['nimbus-mui', 'nimbus-import', 'monash-nimbus-reports'],
                  code_example, embedding))
            migrated += 1

    conn.commit()
    logger.info(f"Knowledge migration complete: {migrated} entries (facts + learnings + patterns)")
    return migrated


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Migrate nimbus-knowledge to entity catalog')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be migrated without writing')
    parser.add_argument('--limit', type=int, help='Limit number of OData entities to migrate')
    parser.add_argument('--skip-knowledge', action='store_true', help='Skip facts/learnings/patterns migration')
    parser.add_argument('--skip-odata', action='store_true', help='Skip OData entity migration')
    args = parser.parse_args()

    conn = get_db_connection()
    if not conn:
        logger.error("Cannot connect to database")
        sys.exit(1)

    try:
        total = 0

        if not args.skip_odata:
            logger.info("=== Phase 1: OData Entities ===")
            total += migrate_odata_entities(conn, dry_run=args.dry_run, limit=args.limit)

        if not args.skip_knowledge:
            logger.info("=== Phase 2: Knowledge (facts, learnings, patterns) ===")
            total += migrate_knowledge(conn, dry_run=args.dry_run)

        logger.info(f"=== Migration complete: {total} items {'would be' if args.dry_run else ''} migrated ===")

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
