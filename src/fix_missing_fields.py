#!/usr/bin/env python3
"""
Fix missing fields in publications.bib by extracting info from existing DOIs
or looking up metadata from CrossRef API.
"""

import re
import json
import urllib.request
import urllib.error
import time
import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import BibTexWriter

def get_crossref_metadata(doi):
    """Fetch metadata from CrossRef API for a given DOI."""
    url = f"https://api.crossref.org/works/{doi}"
    headers = {'User-Agent': 'AcademicCVBuilder/1.0 (mailto:joseph.bulbulia@vuw.ac.nz)'}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            return data.get('message', {})
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        print(f"  Error fetching {doi}: {e}")
        return None

def extract_metadata(crossref_data):
    """Extract relevant fields from CrossRef response."""
    if not crossref_data:
        return {}

    metadata = {}

    # Volume
    if 'volume' in crossref_data:
        metadata['volume'] = str(crossref_data['volume'])

    # Issue/Number
    if 'issue' in crossref_data:
        metadata['number'] = str(crossref_data['issue'])

    # Pages
    if 'page' in crossref_data:
        metadata['pages'] = crossref_data['page'].replace('-', '--')

    # Article number (for e-journals)
    if 'article-number' in crossref_data:
        if 'pages' not in metadata:
            metadata['pages'] = crossref_data['article-number']

    return metadata

def main():
    bib_path = '/sessions/relaxed-tender-edison/mnt/website/cv/publications.bib'

    # Load bib file
    parser = BibTexParser(common_strings=True)
    with open(bib_path, 'r', encoding='utf-8') as f:
        bib_db = bibtexparser.load(f, parser=parser)

    print(f"Loaded {len(bib_db.entries)} entries")

    # Find entries with DOI but missing volume/pages
    entries_to_fix = []
    for entry in bib_db.entries:
        doi = entry.get('doi', '')
        if doi and not doi.startswith('10.31234') and not doi.startswith('10.17605'):  # Skip preprints
            missing = []
            if not entry.get('volume'):
                missing.append('volume')
            if not entry.get('pages'):
                missing.append('pages')
            if missing:
                entries_to_fix.append((entry, missing))

    print(f"\nFound {len(entries_to_fix)} entries with DOI but missing volume/pages")

    # Process each entry
    fixed_count = 0
    for entry, missing in entries_to_fix[:30]:  # Limit to 30 to avoid rate limiting
        doi = entry.get('doi', '')
        entry_id = entry.get('ID', 'unknown')

        print(f"\n[{entry_id}] Missing: {', '.join(missing)}")
        print(f"  DOI: {doi}")

        # Fetch from CrossRef
        crossref_data = get_crossref_metadata(doi)
        if crossref_data:
            metadata = extract_metadata(crossref_data)

            # Update entry
            updated = False
            for field in missing:
                if field in metadata:
                    entry[field] = metadata[field]
                    print(f"  + {field}: {metadata[field]}")
                    updated = True

            if updated:
                fixed_count += 1

        time.sleep(0.5)  # Rate limiting

    print(f"\n\nFixed {fixed_count} entries")

    # Write back
    if fixed_count > 0:
        writer = BibTexWriter()
        writer.indent = '  '
        with open(bib_path, 'w', encoding='utf-8') as f:
            f.write(bibtexparser.dumps(bib_db, writer))
        print(f"Saved to {bib_path}")

if __name__ == '__main__':
    main()
