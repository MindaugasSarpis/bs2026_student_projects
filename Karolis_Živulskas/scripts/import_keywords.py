#!/usr/bin/env python
"""Load keywords from data/keywords/keywords.csv into the database.

Usage:
    python scripts/import_keywords.py                  # import from default file
    python scripts/import_keywords.py --dry-run        # show changes without writing
    python scripts/import_keywords.py --list           # print what is currently in DB
    python scripts/import_keywords.py --export         # dump DB back to CSV
    python scripts/import_keywords.py --file path.csv  # import a different file

Rules:
  - Safe to re-run: existing patterns are updated, not duplicated.
  - Patterns removed from the CSV are NOT deleted unless --prune is passed.
  - Lines starting with # and blank lines are ignored.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

# Allow running from the repo root without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from repops.db import get_session
from repops.models import KeywordEntry, KeywordSet

_DEFAULT_FILE = Path("data/keywords/keywords.csv")
_SET_NAME = "keywords"
_SET_DESCRIPTION = "Main keyword list — hate speech and disinformation phrases"
_COMMENT_RE = re.compile(r"^\s*#")


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _parse(path: Path) -> list[dict]:  # type: ignore[type-arg]
    rows = []
    with path.open(encoding="utf-8") as f:
        clean_lines = [ln for ln in f if not _COMMENT_RE.match(ln) and ln.strip()]

    if not clean_lines:
        return []

    reader = csv.DictReader(clean_lines)
    for raw in reader:
        pattern = raw.get("pattern", "").strip()
        if not pattern:
            continue
        try:
            severity = max(1, min(3, int(raw.get("severity", "1").strip())))
        except ValueError:
            severity = 1
        category = raw.get("category", "hate_speech").strip()
        notes = raw.get("notes", "").strip()
        rows.append({"pattern": pattern, "severity": severity, "category": category, "notes": notes})
    return rows


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

def do_import(path: Path, dry_run: bool = False, prune: bool = False) -> None:
    rows = _parse(path)
    if not rows:
        print(f"No rows found in {path} (empty or all comments).")
        return

    print(f"{'[DRY run] ' if dry_run else ''}Importing {len(rows)} rows from {path}")

    if dry_run:
        for r in rows:
            print(f"  sev={r['severity']} [{r['category']}]  {r['pattern']!r}")
            if r["notes"]:
                print(f"    note: {r['notes']}")
        return

    inserted = updated = pruned = 0

    with get_session() as session:
        ks = session.scalar(select(KeywordSet).where(KeywordSet.name == _SET_NAME))
        if not ks:
            ks = KeywordSet(name=_SET_NAME, description=_SET_DESCRIPTION, language=None, is_active=True)
            session.add(ks)
            session.flush()
            print(f"Created keyword set '{_SET_NAME}'")
        else:
            print(f"Using existing keyword set '{_SET_NAME}' ({len(ks.entries)} entries before import)")

        existing: dict[str, KeywordEntry] = {e.pattern: e for e in ks.entries}
        csv_patterns: set[str] = set()

        for r in rows:
            csv_patterns.add(r["pattern"])
            if r["pattern"] in existing:
                e = existing[r["pattern"]]
                changed = (
                    e.severity != r["severity"]
                    or e.notes != (r["notes"] or None)
                )
                if changed:
                    e.severity = r["severity"]
                    e.notes = r["notes"] or None
                    updated += 1
            else:
                session.add(KeywordEntry(
                    keyword_set_id=ks.id,
                    pattern=r["pattern"],
                    severity=r["severity"],
                    is_regex=False,
                    notes=r["notes"] or None,
                    added_by="import_script",
                ))
                inserted += 1

        if prune:
            for pattern, entry in existing.items():
                if pattern not in csv_patterns:
                    session.delete(entry)
                    pruned += 1

        session.commit()

    print(f"Done: inserted={inserted}  updated={updated}  pruned={pruned}")


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

def do_list() -> None:
    with get_session() as session:
        sets = session.scalars(select(KeywordSet)).all()
        if not sets:
            print("No keyword sets in the database.")
            return
        for ks in sets:
            entries = session.scalars(
                select(KeywordEntry).where(KeywordEntry.keyword_set_id == ks.id)
            ).all()
            active = "active" if ks.is_active else "inactive"
            print(f"\n{ks.name}  [{active}]  {len(entries)} entries")
            for e in sorted(entries, key=lambda x: (-x.severity, x.pattern)):
                flag = "R" if e.is_regex else " "
                note = f"  # {e.notes}" if e.notes else ""
                print(f"  [{flag}] sev={e.severity}  {e.pattern!r}{note}")


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def do_export(out_path: Path) -> None:
    with get_session() as session:
        sets = session.scalars(select(KeywordSet)).all()
        for ks in sets:
            entries = session.scalars(
                select(KeywordEntry).where(KeywordEntry.keyword_set_id == ks.id)
            ).all()
            with out_path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["pattern", "severity", "category", "notes"])
                for e in sorted(entries, key=lambda x: (-x.severity, x.pattern)):
                    writer.writerow([e.pattern, e.severity, "hate_speech", e.notes or ""])
            print(f"Exported {len(entries)} entries from '{ks.name}' to {out_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Manage RepOps keyword database")
    parser.add_argument("--file", type=Path, default=_DEFAULT_FILE, help=f"CSV file to import (default: {_DEFAULT_FILE})")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing to DB")
    parser.add_argument("--prune", action="store_true", help="Remove DB entries that are no longer in the CSV")
    parser.add_argument("--list", action="store_true", help="List all keywords currently in the database")
    parser.add_argument("--export", type=Path, metavar="OUT", help="Export DB keywords to a CSV file")
    args = parser.parse_args()

    if args.list:
        do_list()
    elif args.export:
        do_export(args.export)
    else:
        do_import(args.file, dry_run=args.dry_run, prune=args.prune)


if __name__ == "__main__":
    main()
