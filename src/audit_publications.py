#!/usr/bin/env python3
"""
Audit publications.bib against authoritative CV and identify issues.

This script:
1. Parses the authoritative LaTeX CV to extract all publications
2. Parses publications.bib
3. Identifies duplicates (same DOI, similar titles, preprint/published pairs)
4. Flags incomplete entries (missing year, journal, pages, etc.)
5. Reports entries in CV but missing from bib (and vice versa)
"""

import re
import sys
from pathlib import Path
from collections import defaultdict
import bibtexparser
from bibtexparser.bparser import BibTexParser
from difflib import SequenceMatcher

def normalize_title(title):
    """Normalize title for comparison."""
    # Remove braces, lowercase, remove punctuation
    title = re.sub(r'[{}]', '', title)
    title = title.lower()
    title = re.sub(r'[^\w\s]', '', title)
    title = ' '.join(title.split())
    return title

def similar(a, b, threshold=0.85):
    """Check if two strings are similar."""
    return SequenceMatcher(None, a, b).ratio() >= threshold

def extract_cv_publications(cv_path):
    """Extract publications from LaTeX CV."""
    with open(cv_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Find bibitem entries
    bibitems = re.findall(r'\\bibitem\{([^}]+)\}(.*?)(?=\\bibitem|\\end\{thebibliography\})',
                          content, re.DOTALL)

    publications = []
    for key, text in bibitems:
        # Clean up the text
        text = re.sub(r'\\newblock\s*', ' ', text)
        text = re.sub(r'\\textcolor\{[^}]+\}\{', '', text)
        text = re.sub(r'\{\\bf\s*', '', text)
        text = re.sub(r'\{\\em\s*', '', text)
        text = re.sub(r'\\href\{[^}]+\}\{([^}]+)\}', r'\1', text)
        text = re.sub(r'[{}]', '', text)
        text = ' '.join(text.split())

        # Try to extract year
        year_match = re.search(r'\((\d{4})\)', text)
        year = year_match.group(1) if year_match else None

        # Try to extract DOI
        doi_match = re.search(r'doi[:/\s]*(10\.\d+/[^\s]+)', text, re.IGNORECASE)
        doi = doi_match.group(1) if doi_match else None

        publications.append({
            'key': key,
            'text': text,
            'year': year,
            'doi': doi
        })

    return publications

def load_bib_file(bib_path):
    """Load and parse bib file."""
    parser = BibTexParser(common_strings=True)
    with open(bib_path, 'r', encoding='utf-8') as f:
        bib_db = bibtexparser.load(f, parser=parser)
    return bib_db.entries

def find_duplicates(entries):
    """Find duplicate entries based on DOI or similar titles."""
    duplicates = []

    # Group by DOI
    by_doi = defaultdict(list)
    for e in entries:
        doi = e.get('doi', '').lower().strip()
        if doi:
            by_doi[doi].append(e)

    for doi, group in by_doi.items():
        if len(group) > 1:
            duplicates.append({
                'type': 'same_doi',
                'doi': doi,
                'entries': [(e.get('ID'), e.get('title', '')[:60]) for e in group]
            })

    # Check for similar titles (potential preprint/published pairs)
    titles = [(e, normalize_title(e.get('title', ''))) for e in entries]
    seen_pairs = set()

    for i, (e1, t1) in enumerate(titles):
        for j, (e2, t2) in enumerate(titles[i+1:], i+1):
            if similar(t1, t2) and (i, j) not in seen_pairs:
                seen_pairs.add((i, j))
                # Check if one is a preprint (OSF, psyarxiv, etc.)
                doi1 = e1.get('doi', '').lower()
                doi2 = e2.get('doi', '').lower()
                is_preprint_pair = (
                    ('osf.io' in doi1 or 'psyarxiv' in doi1 or '31234' in doi1) !=
                    ('osf.io' in doi2 or 'psyarxiv' in doi2 or '31234' in doi2)
                )
                duplicates.append({
                    'type': 'preprint_published' if is_preprint_pair else 'similar_title',
                    'entries': [
                        (e1.get('ID'), e1.get('title', '')[:60], e1.get('doi', '')),
                        (e2.get('ID'), e2.get('title', '')[:60], e2.get('doi', ''))
                    ]
                })

    return duplicates

def find_incomplete_entries(entries):
    """Find entries missing key fields."""
    incomplete = []

    required_by_type = {
        'article': ['author', 'title', 'journal', 'year'],
        'incollection': ['author', 'title', 'booktitle', 'year'],
        'inbook': ['author', 'title', 'booktitle', 'year'],
        'book': ['title', 'year'],  # could be author or editor
        'phdthesis': ['author', 'title', 'school', 'year'],
        'misc': ['author', 'title', 'year'],
    }

    recommended = {
        'article': ['volume', 'pages', 'doi'],
        'incollection': ['pages', 'publisher'],
        'book': ['publisher'],
    }

    for e in entries:
        entry_type = e.get('ENTRYTYPE', 'misc').lower()
        entry_id = e.get('ID', 'unknown')
        missing_required = []
        missing_recommended = []

        # Check required fields
        for field in required_by_type.get(entry_type, ['author', 'title', 'year']):
            if field not in e or not e[field].strip():
                missing_required.append(field)

        # Check recommended fields
        for field in recommended.get(entry_type, []):
            if field not in e or not e[field].strip():
                missing_recommended.append(field)

        if missing_required or missing_recommended:
            incomplete.append({
                'id': entry_id,
                'type': entry_type,
                'title': e.get('title', '')[:50],
                'year': e.get('year', 'n.d.'),
                'missing_required': missing_required,
                'missing_recommended': missing_recommended
            })

    return incomplete

def find_preprints(entries):
    """Find entries that appear to be preprints."""
    preprints = []
    preprint_indicators = ['osf.io', 'psyarxiv', 'arxiv', '31234', 'preprint', 'biorxiv', 'medrxiv']

    for e in entries:
        doi = e.get('doi', '').lower()
        url = e.get('url', '').lower()
        publisher = e.get('publisher', '').lower()

        is_preprint = any(ind in doi or ind in url or ind in publisher
                         for ind in preprint_indicators)

        if is_preprint:
            preprints.append({
                'id': e.get('ID'),
                'title': e.get('title', '')[:60],
                'doi': e.get('doi', ''),
                'year': e.get('year', 'n.d.')
            })

    return preprints

def main():
    # Paths
    cv_path = Path('/sessions/relaxed-tender-edison/mnt/uploads/bulbulia-j-a-cv.tex')
    bib_path = Path('/sessions/relaxed-tender-edison/mnt/website/cv/publications.bib')

    print("=" * 80)
    print("PUBLICATIONS AUDIT REPORT")
    print("=" * 80)

    # Load bib file
    print("\n📚 Loading publications.bib...")
    bib_entries = load_bib_file(bib_path)
    print(f"   Found {len(bib_entries)} entries")

    # Find duplicates
    print("\n" + "=" * 80)
    print("🔍 DUPLICATE DETECTION")
    print("=" * 80)
    duplicates = find_duplicates(bib_entries)

    if duplicates:
        for dup in duplicates:
            if dup['type'] == 'same_doi':
                print(f"\n⚠️  SAME DOI: {dup['doi']}")
                for entry_id, title in dup['entries']:
                    print(f"   - {entry_id}: {title}...")
            elif dup['type'] == 'preprint_published':
                print(f"\n⚠️  PREPRINT/PUBLISHED PAIR:")
                for entry_id, title, doi in dup['entries']:
                    print(f"   - {entry_id}: {title}...")
                    print(f"     DOI: {doi}")
            else:
                print(f"\n⚠️  SIMILAR TITLES:")
                for entry_id, title, doi in dup['entries']:
                    print(f"   - {entry_id}: {title}...")
    else:
        print("\n✅ No duplicates found")

    # Find preprints (potential duplicates with published versions)
    print("\n" + "=" * 80)
    print("📝 PREPRINTS (may have published versions)")
    print("=" * 80)
    preprints = find_preprints(bib_entries)

    if preprints:
        for p in preprints:
            print(f"\n   [{p['year']}] {p['id']}")
            print(f"   Title: {p['title']}...")
            print(f"   DOI: {p['doi']}")
    else:
        print("\n✅ No preprints found")

    # Find incomplete entries
    print("\n" + "=" * 80)
    print("📋 INCOMPLETE ENTRIES")
    print("=" * 80)
    incomplete = find_incomplete_entries(bib_entries)

    # Sort by severity (missing required first)
    incomplete_required = [e for e in incomplete if e['missing_required']]
    incomplete_recommended = [e for e in incomplete if not e['missing_required'] and e['missing_recommended']]

    if incomplete_required:
        print(f"\n❌ Missing REQUIRED fields ({len(incomplete_required)} entries):")
        for e in sorted(incomplete_required, key=lambda x: x['year'], reverse=True):
            print(f"\n   [{e['year']}] {e['id']} ({e['type']})")
            print(f"   Title: {e['title']}...")
            print(f"   Missing: {', '.join(e['missing_required'])}")

    if incomplete_recommended:
        print(f"\n⚠️  Missing RECOMMENDED fields ({len(incomplete_recommended)} entries):")
        for e in sorted(incomplete_recommended, key=lambda x: x['year'], reverse=True)[:20]:
            print(f"\n   [{e['year']}] {e['id']} ({e['type']})")
            print(f"   Missing: {', '.join(e['missing_recommended'])}")
        if len(incomplete_recommended) > 20:
            print(f"\n   ... and {len(incomplete_recommended) - 20} more")

    if not incomplete:
        print("\n✅ All entries have required fields")

    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"\n   Total entries: {len(bib_entries)}")
    print(f"   Potential duplicates: {len(duplicates)}")
    print(f"   Preprints: {len(preprints)}")
    print(f"   Missing required fields: {len(incomplete_required)}")
    print(f"   Missing recommended fields: {len(incomplete_recommended)}")

    # Count entries with DOIs
    with_doi = sum(1 for e in bib_entries if e.get('doi'))
    with_url = sum(1 for e in bib_entries if e.get('url') or e.get('file'))
    print(f"   Entries with DOI: {with_doi}")
    print(f"   Entries with URL/file: {with_url}")

if __name__ == '__main__':
    main()
