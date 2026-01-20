#!/usr/bin/env python3
"""
Find entries in the authoritative CV that are missing from publications.bib
"""

import re
import bibtexparser
from bibtexparser.bparser import BibTexParser
from difflib import SequenceMatcher

def normalize(text):
    """Normalize text for comparison."""
    text = re.sub(r'[{}\\]', '', text)
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = ' '.join(text.split())
    return text

def extract_cv_entries(cv_path):
    """Extract entries from LaTeX CV."""
    with open(cv_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Find bibitem entries
    bibitems = re.findall(r'\\bibitem\{([^}]+)\}(.*?)(?=\\bibitem|\\end\{thebibliography\})',
                          content, re.DOTALL)

    entries = []
    for key, text in bibitems:
        # Clean up the text
        text_clean = re.sub(r'\\newblock\s*', ' ', text)
        text_clean = re.sub(r'\\textcolor\{[^}]+\}\{', '', text_clean)
        text_clean = re.sub(r'\{\\bf\s*', '', text_clean)
        text_clean = re.sub(r'\{\\em\s*', '', text_clean)
        text_clean = re.sub(r'\\href\{[^}]+\}\{([^}]+)\}', r'\1', text_clean)
        text_clean = re.sub(r'[{}]', '', text_clean)
        text_clean = ' '.join(text_clean.split())

        # Try to extract year
        year_match = re.search(r'\((\d{4})\)', text_clean)
        year = year_match.group(1) if year_match else None

        # Try to extract title (text after year, before journal/book info)
        title_match = re.search(r'\(\d{4}\)[.\s]*([^.]+)', text_clean)
        title = title_match.group(1).strip() if title_match else ""

        entries.append({
            'key': key,
            'text': text_clean[:200],
            'year': year,
            'title': title,
            'normalized_title': normalize(title)
        })

    return entries

def load_bib_entries(bib_path):
    """Load bib entries."""
    parser = BibTexParser(common_strings=True)
    with open(bib_path, 'r', encoding='utf-8') as f:
        bib_db = bibtexparser.load(f, parser=parser)

    entries = []
    for e in bib_db.entries:
        title = e.get('title', '')
        entries.append({
            'id': e.get('ID'),
            'title': title,
            'normalized_title': normalize(title),
            'year': e.get('year', '')
        })
    return entries

def similar(a, b, threshold=0.75):
    """Check string similarity."""
    return SequenceMatcher(None, a, b).ratio() >= threshold

def main():
    cv_path = '/sessions/relaxed-tender-edison/mnt/uploads/bulbulia-j-a-cv.tex'
    bib_path = '/sessions/relaxed-tender-edison/mnt/website/cv/publications.bib'

    cv_entries = extract_cv_entries(cv_path)
    bib_entries = load_bib_entries(bib_path)

    print(f"CV entries: {len(cv_entries)}")
    print(f"Bib entries: {len(bib_entries)}")
    print()

    # Find CV entries not in bib
    missing = []
    for cv_e in cv_entries:
        found = False
        for bib_e in bib_entries:
            # Match by similar title
            if similar(cv_e['normalized_title'], bib_e['normalized_title']):
                found = True
                break
            # Or by year + partial title
            if cv_e['year'] == bib_e['year']:
                if similar(cv_e['normalized_title'][:50], bib_e['normalized_title'][:50], 0.7):
                    found = True
                    break

        if not found:
            missing.append(cv_e)

    print(f"Missing entries: {len(missing)}")
    print("=" * 80)
    for m in missing:
        print(f"\n[{m['year']}] {m['key']}")
        print(f"  {m['text'][:150]}...")

if __name__ == '__main__':
    main()
