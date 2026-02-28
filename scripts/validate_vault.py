#!/usr/bin/env python3
"""
Vault Structural Validation - Checks vault design documents for structural issues.

Checks 1-5 are filesystem-only (no DB access):
  1. Broken wiki-links      (ERROR)   - [[Target]] references that resolve to no file
  2. Missing YAML frontmatter (WARNING) - Files without --- delimited frontmatter / required tags
  3. Missing version footer  (WARNING) - Files without **Version**: in last 10 lines
  4. Orphan files           (INFO)    - Files with zero incoming wiki-links from other files
  5. Terminology drift      (INFO)    - Non-canonical terms found (from terminology-rules.yaml)

Checks 6-8 require the concept index (claude.knowledge with design_concept category):
  6. Unindexed files        (WARNING) - Vault files not yet extracted to concept index
  7. Area coverage gaps     (WARNING) - Areas with fewer than min_concepts (default 3)
  8. Decision count drift   (INFO)    - Mismatch between decision tracker and index

Usage:
    python scripts/validate_vault.py
    python scripts/validate_vault.py --project Project-Metis
    python scripts/validate_vault.py --check links
    python scripts/validate_vault.py --json
    python scripts/validate_vault.py --verbose
    python scripts/validate_vault.py --skip-db          # Skip checks 6-8

Exit codes:
    0  No errors found
    1  One or more ERROR-severity findings
    2  Script-level error (bad args, missing files, etc.)
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

# Database access for checks 6-8 (optional — gracefully skip if unavailable)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from config import get_database_uri
    import psycopg
    from psycopg.rows import dict_row
    _HAS_DB = True
except ImportError:
    _HAS_DB = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VAULT_PATH = Path("C:/Projects/claude-family/knowledge-vault")
TERMINOLOGY_RULES_PATH = Path("C:/Projects/claude-family/scripts/terminology-rules.yaml")

# Folders excluded from most checks (not from link-target resolution)
EXCLUDED_SCAN_FOLDERS = {"_templates"}

# Folders whose files are excluded from orphan check (unlinked files are expected here)
ORPHAN_EXEMPT_FOLDERS = {"_templates", "00-Inbox"}

# Filenames excluded from frontmatter / footer / orphan checks
EXCLUDED_FILENAMES = {"README.md"}

# Number of trailing lines to inspect for version footer
FOOTER_SEARCH_LINES = 10

# Wiki-link pattern: [[target]] or [[target|display]] or [[target#section]] etc.
WIKILINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")

# Version footer pattern
FOOTER_PATTERN = re.compile(r"\*\*Version\*\*:", re.IGNORECASE)

# Severity constants
SEV_ERROR = "ERROR"
SEV_WARNING = "WARNING"
SEV_INFO = "INFO"

# Check name constants (for --check filter)
CHECK_LINKS = "links"
CHECK_FRONTMATTER = "frontmatter"
CHECK_FOOTER = "footer"
CHECK_ORPHANS = "orphans"
CHECK_TERMINOLOGY = "terminology"
CHECK_UNINDEXED = "unindexed"
CHECK_AREA_COVERAGE = "area-coverage"
CHECK_DECISION_DRIFT = "decision-drift"

CHECK_ALIASES: Dict[str, str] = {
    "1": CHECK_LINKS,
    "2": CHECK_FRONTMATTER,
    "3": CHECK_FOOTER,
    "4": CHECK_ORPHANS,
    "5": CHECK_TERMINOLOGY,
    "6": CHECK_UNINDEXED,
    "7": CHECK_AREA_COVERAGE,
    "8": CHECK_DECISION_DRIFT,
    CHECK_LINKS: CHECK_LINKS,
    CHECK_FRONTMATTER: CHECK_FRONTMATTER,
    CHECK_FOOTER: CHECK_FOOTER,
    CHECK_ORPHANS: CHECK_ORPHANS,
    CHECK_TERMINOLOGY: CHECK_TERMINOLOGY,
    CHECK_UNINDEXED: CHECK_UNINDEXED,
    CHECK_AREA_COVERAGE: CHECK_AREA_COVERAGE,
    CHECK_DECISION_DRIFT: CHECK_DECISION_DRIFT,
}

# Checks that require database access
DB_CHECKS = {CHECK_UNINDEXED, CHECK_AREA_COVERAGE, CHECK_DECISION_DRIFT}

# Minimum concepts per area for area coverage check
DEFAULT_MIN_AREA_CONCEPTS = 3


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

Finding = Dict  # {severity, check, file, line (optional), message, detail (optional)}


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------

def collect_markdown_files(root: Path) -> List[Path]:
    """Return all .md files under root, sorted, skipping binary errors."""
    files = []
    for path in sorted(root.rglob("*.md")):
        files.append(path)
    return files


def is_excluded_from_scan(path: Path, vault_root: Path) -> bool:
    """True if this file lives in a folder that we skip for checks 2/3/4/5."""
    rel = path.relative_to(vault_root)
    parts = set(rel.parts[:-1])  # all folder segments, not the filename
    if parts & EXCLUDED_SCAN_FOLDERS:
        return True
    if path.name in EXCLUDED_FILENAMES:
        return True
    return False


def is_orphan_exempt(path: Path, vault_root: Path) -> bool:
    """True if the file is exempt from the orphan check."""
    rel = path.relative_to(vault_root)
    parts = set(rel.parts[:-1])
    if parts & ORPHAN_EXEMPT_FOLDERS:
        return True
    if path.name in EXCLUDED_FILENAMES:
        return True
    return False


def read_file_safe(path: Path) -> Optional[str]:
    """Read a text file gracefully. Returns None on encoding errors."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="latin-1")
        except Exception:
            return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Build lookup: filename stem → set of absolute Paths (case-insensitive)
# ---------------------------------------------------------------------------

def build_filename_index(all_files: List[Path]) -> Dict[str, List[Path]]:
    """
    Map lowercase stem → list of paths.
    Used by the broken-link checker to resolve [[Target]] references.
    """
    index: Dict[str, List[Path]] = {}
    for path in all_files:
        key = path.stem.lower()
        index.setdefault(key, []).append(path)
    return index


# ---------------------------------------------------------------------------
# Check 1: Broken wiki-links
# ---------------------------------------------------------------------------

def check_broken_links(
    scan_files: List[Path],
    all_files: List[Path],
    vault_root: Path,
) -> List[Finding]:
    """
    Find [[Target]] and [[Target|Display]] and [[Target#Section]] patterns.
    Resolve target against the full vault filename index.
    """
    filename_index = build_filename_index(all_files)
    findings: List[Finding] = []

    for path in scan_files:
        content = read_file_safe(path)
        if content is None:
            continue

        rel_path = str(path.relative_to(vault_root))

        for lineno, line in enumerate(content.splitlines(), start=1):
            for match in WIKILINK_PATTERN.finditer(line):
                raw = match.group(1)

                # Strip display text: [[Target|Display]] → Target
                if "|" in raw:
                    raw = raw.split("|", 1)[0]

                # Strip section anchor: [[Target#Section]] → Target
                if "#" in raw:
                    raw = raw.split("#", 1)[0]

                raw = raw.strip()
                if not raw:
                    continue

                # Normalise to a stem for lookup
                stem = Path(raw).stem.lower()

                # Check if any file matches the stem
                candidates = filename_index.get(stem, [])

                # If link contains a path (e.g. "orchestration-infra/file"),
                # narrow candidates to those whose relative path ends with the link path
                resolved = False
                if candidates:
                    if "/" in raw:
                        link_suffix = raw.lower().replace("\\", "/")
                        if not link_suffix.endswith(".md"):
                            link_suffix += ".md"
                        for cand in candidates:
                            cand_rel = str(cand.relative_to(vault_root)).lower().replace("\\", "/")
                            if cand_rel.endswith(link_suffix):
                                resolved = True
                                break
                        # If path-based match fails, still accept stem-only match
                        # (Obsidian resolves by filename if path doesn't match)
                        if not resolved:
                            resolved = True
                    else:
                        resolved = True

                if not resolved:
                    findings.append({
                        "severity": SEV_ERROR,
                        "check": "BROKEN-LINK",
                        "file": rel_path,
                        "line": lineno,
                        "message": f"[[{match.group(1)}]] not found in vault",
                        "detail": {
                            "link_text": raw,
                            "display_text": match.group(1).split("|", 1)[1].strip()
                            if "|" in match.group(1)
                            else None,
                        },
                    })

    return findings


# ---------------------------------------------------------------------------
# Check 2: Missing YAML frontmatter
# ---------------------------------------------------------------------------

def parse_frontmatter(content: str) -> Tuple[bool, Optional[Dict]]:
    """
    Parse YAML frontmatter from file content.
    Returns (has_frontmatter, parsed_dict_or_None).
    """
    if not content.startswith("---"):
        return False, None

    # Match --- ... --- block
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", content, re.DOTALL)
    if not match:
        # Try with just --- at start/end lines (no trailing content)
        match = re.match(r"^---\r?\n(.*?)\r?\n---\s*$", content, re.DOTALL)
    if not match:
        return False, None

    fm_text = match.group(1)
    try:
        parsed = yaml.safe_load(fm_text)
        if not isinstance(parsed, dict):
            return True, {}
        return True, parsed
    except yaml.YAMLError:
        return True, {}


def check_frontmatter(
    scan_files: List[Path],
    vault_root: Path,
) -> List[Finding]:
    """Check for missing / incomplete YAML frontmatter."""
    findings: List[Finding] = []

    for path in scan_files:
        content = read_file_safe(path)
        if content is None:
            continue

        rel_path = str(path.relative_to(vault_root))
        has_fm, parsed = parse_frontmatter(content)

        if not has_fm:
            findings.append({
                "severity": SEV_WARNING,
                "check": "NO-FRONTMATTER",
                "file": rel_path,
                "line": None,
                "message": "Missing YAML frontmatter",
                "detail": {},
            })
            continue

        # Has frontmatter — check required fields
        if not parsed or "tags" not in parsed:
            findings.append({
                "severity": SEV_WARNING,
                "check": "NO-TAGS",
                "file": rel_path,
                "line": None,
                "message": "Frontmatter missing 'tags' field",
                "detail": {"found_keys": list(parsed.keys()) if parsed else []},
            })

        # Optional but flagged if absent
        if parsed and "projects" not in parsed:
            findings.append({
                "severity": SEV_WARNING,
                "check": "NO-PROJECTS",
                "file": rel_path,
                "line": None,
                "message": "Frontmatter missing 'projects' field (optional but recommended)",
                "detail": {"found_keys": list(parsed.keys())},
            })

    return findings


# ---------------------------------------------------------------------------
# Check 3: Missing version footer
# ---------------------------------------------------------------------------

def check_version_footer(
    scan_files: List[Path],
    vault_root: Path,
) -> List[Finding]:
    """Check that each file has a **Version**: line in its last N lines."""
    findings: List[Finding] = []

    for path in scan_files:
        content = read_file_safe(path)
        if content is None:
            continue

        lines = content.splitlines()
        tail = lines[-FOOTER_SEARCH_LINES:] if len(lines) >= FOOTER_SEARCH_LINES else lines
        tail_text = "\n".join(tail)

        if not FOOTER_PATTERN.search(tail_text):
            rel_path = str(path.relative_to(vault_root))
            findings.append({
                "severity": SEV_WARNING,
                "check": "NO-FOOTER",
                "file": rel_path,
                "line": None,
                "message": "Missing version footer (no **Version**: in last 10 lines)",
                "detail": {},
            })

    return findings


# ---------------------------------------------------------------------------
# Check 4: Orphan files
# ---------------------------------------------------------------------------

def build_incoming_links_map(
    all_files: List[Path],
    vault_root: Path,
    filename_index: Dict[str, List[Path]],
) -> Dict[str, Set[str]]:
    """
    Build a map of rel_path → set of rel_paths that link to it.
    We scan every .md file for wiki-links and record which files each link
    points to (resolved via the filename index).
    """
    incoming: Dict[str, Set[str]] = {
        str(p.relative_to(vault_root)): set() for p in all_files
    }

    for path in all_files:
        content = read_file_safe(path)
        if content is None:
            continue

        src_rel = str(path.relative_to(vault_root))

        for match in WIKILINK_PATTERN.finditer(content):
            raw = match.group(1)
            if "|" in raw:
                raw = raw.split("|", 1)[0]
            if "#" in raw:
                raw = raw.split("#", 1)[0]
            raw = raw.strip()
            if not raw:
                continue

            stem = Path(raw).stem.lower()
            targets = filename_index.get(stem, [])
            for target_path in targets:
                target_rel = str(target_path.relative_to(vault_root))
                if target_rel != src_rel:  # don't count self-links
                    incoming[target_rel].add(src_rel)

    return incoming


def check_orphans(
    scan_files: List[Path],
    all_files: List[Path],
    vault_root: Path,
) -> List[Finding]:
    """Find files with zero incoming wiki-links from any other vault file."""
    filename_index = build_filename_index(all_files)
    incoming = build_incoming_links_map(all_files, vault_root, filename_index)
    findings: List[Finding] = []

    for path in scan_files:
        if is_orphan_exempt(path, vault_root):
            continue

        rel_path = str(path.relative_to(vault_root))
        linkers = incoming.get(rel_path, set())

        if not linkers:
            findings.append({
                "severity": SEV_INFO,
                "check": "ORPHAN",
                "file": rel_path,
                "line": None,
                "message": "No incoming links from any other vault file",
                "detail": {"suggestion": "Link to this file from a relevant index or parent document"},
            })

    return findings


# ---------------------------------------------------------------------------
# Check 5: Terminology drift
# ---------------------------------------------------------------------------

def load_terminology_rules() -> List[Dict]:
    """Load rules from terminology-rules.yaml."""
    if not TERMINOLOGY_RULES_PATH.exists():
        return []
    try:
        raw = TERMINOLOGY_RULES_PATH.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
        return data.get("rules", []) if isinstance(data, dict) else []
    except Exception:
        return []


def file_is_in_scope(rel_path: str, scope: str) -> bool:
    """True if the file falls within the rule's scope."""
    if scope == "all":
        return True
    # Treat scope as a path prefix
    return scope.lower() in rel_path.lower()


def check_terminology(
    scan_files: List[Path],
    vault_root: Path,
) -> List[Finding]:
    """Find non-canonical terminology variants in vault files."""
    rules = load_terminology_rules()
    if not rules:
        return []

    findings: List[Finding] = []

    for path in scan_files:
        content = read_file_safe(path)
        if content is None:
            continue

        rel_path = str(path.relative_to(vault_root))

        for rule in rules:
            canonical = rule.get("canonical", "")
            variants = rule.get("variants", [])
            scope = rule.get("scope", "all")

            if not file_is_in_scope(rel_path, scope):
                continue

            for variant in variants:
                # Case-insensitive whole-token match
                pattern = re.compile(re.escape(variant), re.IGNORECASE)
                for lineno, line in enumerate(content.splitlines(), start=1):
                    if pattern.search(line):
                        findings.append({
                            "severity": SEV_INFO,
                            "check": "TERMINOLOGY",
                            "file": rel_path,
                            "line": lineno,
                            "message": (
                                f'"{variant}" — use "{canonical}" instead'
                            ),
                            "detail": {
                                "found": variant,
                                "canonical": canonical,
                            },
                        })

    return findings


# ---------------------------------------------------------------------------
# Database helpers for checks 6-8
# ---------------------------------------------------------------------------

_AREA_RE = re.compile(r'\bArea:\s*([^\n|,]+)', re.IGNORECASE)
_TYPE_RE = re.compile(r'\bType:\s*([^\n|,]+)', re.IGNORECASE)


def _get_db_connection():
    """Get a database connection, or None if unavailable."""
    if not _HAS_DB:
        return None
    uri = get_database_uri()
    if not uri:
        return None
    try:
        return psycopg.connect(uri, row_factory=dict_row)
    except Exception:
        return None


def _fetch_design_concepts(conn, project_name: str) -> List[Dict]:
    """Fetch all design_concept knowledge entries for a project."""
    cur = conn.cursor()
    cur.execute("""
        SELECT
            knowledge_id::text AS knowledge_id,
            title,
            description,
            source,
            created_at
        FROM claude.knowledge
        WHERE knowledge_category = 'design_concept'
          AND %s = ANY(applies_to_projects)
        ORDER BY created_at
    """, (project_name,))
    rows = cur.fetchall()
    cur.close()
    return rows


def _extract_source_files(concepts: List[Dict]) -> Set[str]:
    """Extract unique source file paths from concept descriptions.

    Concepts store source as 'Source: path/to/file.md' in the description.
    """
    source_re = re.compile(r'\bSource:\s*([^\n|,]+\.md)', re.IGNORECASE)
    sources: Set[str] = set()
    for c in concepts:
        desc = c.get('description', '')
        m = source_re.search(desc)
        if m:
            sources.add(m.group(1).strip())
    return sources


def _extract_area(description: str) -> str:
    """Extract area name from concept description."""
    m = _AREA_RE.search(description or '')
    return m.group(1).strip() if m else 'Unclassified'


def _extract_type(description: str) -> str:
    """Extract concept type from concept description."""
    m = _TYPE_RE.search(description or '')
    return m.group(1).strip().lower() if m else ''


# ---------------------------------------------------------------------------
# Check 6: Unindexed files
# ---------------------------------------------------------------------------

def check_unindexed_files(
    scan_files: List[Path],
    vault_root: Path,
    concepts: List[Dict],
) -> List[Finding]:
    """Find vault files that haven't been extracted to the concept index."""
    indexed_sources = _extract_source_files(concepts)

    # Normalise indexed source paths for comparison
    indexed_normalised: Set[str] = set()
    for src in indexed_sources:
        normalised = src.replace("\\", "/").lower()
        indexed_normalised.add(normalised)

    findings: List[Finding] = []

    for path in scan_files:
        rel_path = str(path.relative_to(vault_root))
        rel_normalised = rel_path.replace("\\", "/").lower()

        # Also check if the filename alone (without full path) matches
        filename_match = any(
            s.endswith("/" + path.name.lower()) or s == path.name.lower()
            for s in indexed_normalised
        )

        if rel_normalised not in indexed_normalised and not filename_match:
            findings.append({
                "severity": SEV_WARNING,
                "check": "UNINDEXED",
                "file": rel_path,
                "line": None,
                "message": "File not yet extracted to concept index",
                "detail": {
                    "suggestion": "Run Phase 1 (EXTRACT) of the Design Coherence skill on this file"
                },
            })

    return findings


# ---------------------------------------------------------------------------
# Check 7: Area coverage gaps
# ---------------------------------------------------------------------------

def check_area_coverage(
    concepts: List[Dict],
    min_concepts: int = DEFAULT_MIN_AREA_CONCEPTS,
) -> List[Finding]:
    """Find areas with fewer than min_concepts in the index."""
    area_counts: Dict[str, int] = {}
    for c in concepts:
        area = _extract_area(c.get('description', ''))
        area_counts[area] = area_counts.get(area, 0) + 1

    findings: List[Finding] = []

    for area, count in sorted(area_counts.items()):
        if area == 'Unclassified':
            continue  # Don't flag unclassified — separate concern
        if count < min_concepts:
            findings.append({
                "severity": SEV_WARNING,
                "check": "AREA-COVERAGE",
                "file": f"(area: {area})",
                "line": None,
                "message": (
                    f"Area '{area}' has only {count} concept(s) "
                    f"(minimum: {min_concepts})"
                ),
                "detail": {
                    "area": area,
                    "concept_count": count,
                    "minimum": min_concepts,
                },
            })

    return findings


# ---------------------------------------------------------------------------
# Check 8: Decision count drift
# ---------------------------------------------------------------------------

def _count_decisions_in_tracker(scan_files: List[Path], vault_root: Path) -> Optional[int]:
    """Count numbered decisions in decision tracker files.

    Looks for files named *decision* and counts patterns like:
    - 'D1:', 'D2:', etc. (decision numbering)
    - '| D1 |', '| D2 |' (table format)
    - '## Decision 1', '## Decision 2' (header format)
    """
    decision_pattern = re.compile(
        r'(?:^|\|)\s*D(\d+)\s*(?:\||:)|'  # D1: or | D1 |
        r'##\s*Decision\s+(\d+)',          # ## Decision 1
        re.IGNORECASE | re.MULTILINE
    )

    tracker_files = [
        p for p in scan_files
        if 'decision' in p.name.lower()
    ]

    if not tracker_files:
        return None

    decision_ids: Set[str] = set()
    for path in tracker_files:
        content = read_file_safe(path)
        if content is None:
            continue
        for m in decision_pattern.finditer(content):
            d_id = m.group(1) or m.group(2)
            if d_id:
                decision_ids.add(d_id)

    return len(decision_ids) if decision_ids else None


def check_decision_drift(
    scan_files: List[Path],
    vault_root: Path,
    concepts: List[Dict],
) -> List[Finding]:
    """Compare decision count in tracker files vs indexed decision concepts."""
    tracker_count = _count_decisions_in_tracker(scan_files, vault_root)
    if tracker_count is None:
        return []  # No decision tracker found — skip

    # Count indexed decisions
    indexed_decisions = sum(
        1 for c in concepts if _extract_type(c.get('description', '')) == 'decision'
    )

    findings: List[Finding] = []

    # Only flag if there's significant drift (>= 3 difference or >50% drift)
    drift = abs(tracker_count - indexed_decisions)
    if drift >= 3 or (tracker_count > 0 and drift / tracker_count > 0.5):
        findings.append({
            "severity": SEV_INFO,
            "check": "DECISION-DRIFT",
            "file": "(decision tracker vs index)",
            "line": None,
            "message": (
                f"Decision tracker shows {tracker_count} decisions, "
                f"index has {indexed_decisions} — drift of {drift}"
            ),
            "detail": {
                "tracker_count": tracker_count,
                "index_count": indexed_decisions,
                "drift": drift,
                "suggestion": "Re-run Phase 1 (EXTRACT) to sync decisions to index",
            },
        })

    return findings


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_finding_human(finding: Finding) -> str:
    """Format a single finding for human-readable output."""
    check = finding["check"]
    file_str = finding["file"]
    line = finding.get("line")
    message = finding["message"]

    location = f"{file_str}:{line}" if line else file_str
    return f"  [{check}] {location} — {message}"


def print_human_report(
    findings: List[Finding],
    scope_label: str,
    files_scanned: int,
    verbose: bool,
) -> None:
    """Print the full human-readable validation report."""
    errors = [f for f in findings if f["severity"] == SEV_ERROR]
    warnings = [f for f in findings if f["severity"] == SEV_WARNING]
    infos = [f for f in findings if f["severity"] == SEV_INFO]

    print("Vault Structural Validation Report")
    print("===================================")
    print()
    print(f"Scope: {scope_label}")
    print(f"Files scanned: {files_scanned}")
    print()

    if errors:
        print(f"ERRORS ({len(errors)})")
        for f in errors:
            print(format_finding_human(f))
        print()

    if warnings:
        print(f"WARNINGS ({len(warnings)})")
        for f in warnings:
            print(format_finding_human(f))
        print()

    if infos:
        print(f"INFO ({len(infos)})")
        for f in infos:
            print(format_finding_human(f))
        print()

    if verbose and not findings:
        print("No issues found.")
        print()

    print(
        f"Summary: {len(errors)} errors, {len(warnings)} warnings, {len(infos)} info"
        f" | {files_scanned} files scanned"
    )


def print_json_report(
    findings: List[Finding],
    scope_label: str,
    files_scanned: int,
) -> None:
    """Print JSON-formatted report."""
    errors = sum(1 for f in findings if f["severity"] == SEV_ERROR)
    warnings = sum(1 for f in findings if f["severity"] == SEV_WARNING)
    infos = sum(1 for f in findings if f["severity"] == SEV_INFO)

    output = {
        "scope": scope_label,
        "files_scanned": files_scanned,
        "findings": findings,
        "summary": {"errors": errors, "warnings": warnings, "info": infos},
    }
    print(json.dumps(output, indent=2))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate vault markdown files structurally (no LLM needed)."
    )
    parser.add_argument(
        "--project",
        metavar="PROJECT",
        help="Scope to 10-Projects/PROJECT/ subdirectory (e.g. Project-Metis)",
    )
    parser.add_argument(
        "--check",
        metavar="CHECK",
        help=(
            "Run only a specific check. "
            "One of: 1/links, 2/frontmatter, 3/footer, 4/orphans, "
            "5/terminology, 6/unindexed, 7/area-coverage, 8/decision-drift"
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output as JSON instead of human-readable text",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show passing files too, not just failures",
    )
    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Skip checks 6-8 (index-dependent, require database)",
    )
    parser.add_argument(
        "--min-area-concepts",
        type=int,
        default=DEFAULT_MIN_AREA_CONCEPTS,
        metavar="N",
        help=f"Minimum concepts per area for check 7 (default: {DEFAULT_MIN_AREA_CONCEPTS})",
    )
    return parser.parse_args()


def resolve_check_filter(raw: Optional[str]) -> Optional[str]:
    """Normalise --check argument to a canonical check name, or None for all."""
    if raw is None:
        return None
    key = raw.strip().lower()
    if key not in CHECK_ALIASES:
        print(
            f"ERROR: Unknown check '{raw}'. "
            "Use one of: 1/links, 2/frontmatter, 3/footer, 4/orphans, "
            "5/terminology, 6/unindexed, 7/area-coverage, 8/decision-drift",
            file=sys.stderr,
        )
        sys.exit(2)
    return CHECK_ALIASES[key]


def main() -> None:
    args = parse_args()
    check_filter = resolve_check_filter(args.check)

    # --- Determine scan root ---
    if args.project:
        scan_root = VAULT_PATH / "10-Projects" / args.project
        if not scan_root.exists():
            print(
                f"ERROR: Project directory not found: {scan_root}",
                file=sys.stderr,
            )
            sys.exit(2)
        scope_label = f"knowledge-vault/10-Projects/{args.project}/"
    else:
        scan_root = VAULT_PATH
        scope_label = "knowledge-vault/ (full vault)"

    # --- Collect files ---
    all_vault_files = collect_markdown_files(VAULT_PATH)  # needed for link resolution
    scan_files_raw = collect_markdown_files(scan_root)

    # Files eligible for checks 2/3/4/5 (no template/README exclusions)
    scan_files_checked = [
        p for p in scan_files_raw if not is_excluded_from_scan(p, VAULT_PATH)
    ]

    findings: List[Finding] = []

    # --- Run selected checks ---
    run_all = check_filter is None

    if run_all or check_filter == CHECK_LINKS:
        # For link checking: scan every file in scope (including templates as sources)
        findings.extend(
            check_broken_links(scan_files_raw, all_vault_files, VAULT_PATH)
        )

    if run_all or check_filter == CHECK_FRONTMATTER:
        findings.extend(check_frontmatter(scan_files_checked, VAULT_PATH))

    if run_all or check_filter == CHECK_FOOTER:
        findings.extend(check_version_footer(scan_files_checked, VAULT_PATH))

    if run_all or check_filter == CHECK_ORPHANS:
        # Orphan check needs full vault scope for incoming-link map, but only
        # reports on the scoped scan files.
        findings.extend(
            check_orphans(scan_files_checked, all_vault_files, VAULT_PATH)
        )

    if run_all or check_filter == CHECK_TERMINOLOGY:
        findings.extend(check_terminology(scan_files_checked, VAULT_PATH))

    # --- Checks 6-8: Index-dependent (require database) ---
    needs_db = (
        not args.skip_db
        and (run_all or check_filter in DB_CHECKS)
    )

    if needs_db:
        # Determine project name for DB queries
        project_name = args.project or ""
        if not project_name:
            # Default: skip DB checks when no project specified
            if not args.output_json:
                print("(Checks 6-8 skipped: --project required for index checks)")
                print()
        else:
            conn = _get_db_connection()
            if conn is None:
                if not args.output_json:
                    print("(Checks 6-8 skipped: database not available)")
                    print()
            else:
                try:
                    concepts = _fetch_design_concepts(conn, project_name)
                    concept_count = len(concepts)

                    if concept_count == 0:
                        if not args.output_json:
                            print(
                                f"(Checks 6-8 skipped: no design_concept entries "
                                f"for project '{project_name}')"
                            )
                            print()
                    else:
                        if not args.output_json:
                            print(
                                f"Concept index: {concept_count} entries "
                                f"for '{project_name}'"
                            )
                            print()

                        if run_all or check_filter == CHECK_UNINDEXED:
                            findings.extend(
                                check_unindexed_files(
                                    scan_files_checked, VAULT_PATH, concepts
                                )
                            )

                        if run_all or check_filter == CHECK_AREA_COVERAGE:
                            findings.extend(
                                check_area_coverage(
                                    concepts, args.min_area_concepts
                                )
                            )

                        if run_all or check_filter == CHECK_DECISION_DRIFT:
                            findings.extend(
                                check_decision_drift(
                                    scan_files_checked, VAULT_PATH, concepts
                                )
                            )
                finally:
                    conn.close()

    # --- Output ---
    if args.output_json:
        print_json_report(findings, scope_label, len(scan_files_raw))
    else:
        print_human_report(findings, scope_label, len(scan_files_raw), args.verbose)

    # --- Exit code ---
    has_errors = any(f["severity"] == SEV_ERROR for f in findings)
    sys.exit(1 if has_errors else 0)


if __name__ == "__main__":
    main()
