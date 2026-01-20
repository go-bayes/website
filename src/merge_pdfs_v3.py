#!/usr/bin/env python3
"""
Merge PDF links from LaTeX CV into the BibTeX file.
Improved title extraction and matching.
"""

import re
import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode

def read_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def extract_bibitems_with_pdfs(tex_content):
    """Extract bibitem entries along with their PDF links."""
    entries = []

    # Find all bibitem entries
    pattern = r'\\bibitem\{([^}]+)\}(.*?)(?=\\bibitem\{|\\subsubsection|\\end\{document\})'

    for match in re.finditer(pattern, tex_content, re.DOTALL):
        key = match.group(1)
        content = match.group(2)

        # Check for PDF link (not on commented line)
        pdf_url = None
        lines = content.split('\n')
        for line in lines:
            if line.strip().startswith('%'):
                continue
            pdf_match = re.search(r'\\href\{([^}]+)\}\{PDF\}', line)
            if pdf_match:
                url = pdf_match.group(1)
                if url.strip() and url != '{}':
                    pdf_url = url
                    break

        if not pdf_url:
            continue

        # Extract DOI
        doi = None
        doi_patterns = [
            r'doi\.org/([^\s\}\\,\%]+)',
            r'DOI[:\s]+([0-9]+\.[^\s\}\\,]+)',
        ]
        for pat in doi_patterns:
            doi_match = re.search(pat, content, re.IGNORECASE)
            if doi_match:
                doi = doi_match.group(1)
                doi = re.sub(r'[,;.\}%]+$', '', doi)
                doi = doi.replace('%2F', '/').replace('%2f', '/')
                break

        # Extract title - try multiple patterns
        title = None
        title_patterns = [
            r'\{\\em\s+([^}]+)\}',           # {\em title}
            r'\\emph\{([^}]+)\}',             # \emph{title}
            r'\\textit\{([^}]+)\}',           # \textit{title}
            r'\\newblock\s+([^\\]+?)\\newblock',  # \newblock title \newblock
        ]
        for pat in title_patterns:
            title_match = re.search(pat, content)
            if title_match:
                title = title_match.group(1).strip()
                # Clean up
                title = re.sub(r'[{}]', '', title)
                title = re.sub(r'\s+', ' ', title)
                if len(title) > 10:  # Reasonable title length
                    break
                else:
                    title = None

        # Extract year
        year_match = re.search(r'\((\d{4})\)', content)
        year = year_match.group(1) if year_match else None

        entries.append({
            'key': key,
            'pdf_url': pdf_url,
            'doi': doi.lower() if doi else None,
            'title': title,
            'year': year
        })

    return entries

def normalize_title(title):
    """Normalize title for matching."""
    if not title:
        return ''
    # Remove LaTeX commands
    title = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', title)
    title = re.sub(r'\\[a-zA-Z]+', '', title)
    title = re.sub(r'[{}\\]', '', title)
    # Remove punctuation and extra spaces
    title = re.sub(r'[^a-zA-Z0-9\s]', ' ', title)
    title = re.sub(r'\s+', ' ', title)
    return title.lower().strip()

def get_title_words(title):
    """Get significant words from title for matching."""
    normalized = normalize_title(title)
    words = normalized.split()
    # Filter out common short words
    stopwords = {'the', 'a', 'an', 'of', 'in', 'on', 'for', 'to', 'and', 'with', 'by', 'from', 'at', 'as', 'is', 'are', 'was', 'were'}
    significant = [w for w in words if w not in stopwords and len(w) > 2]
    return significant

def titles_match(title1, title2, threshold=0.6):
    """Check if two titles match using word overlap."""
    words1 = set(get_title_words(title1))
    words2 = set(get_title_words(title2))

    if not words1 or not words2:
        return False

    overlap = len(words1 & words2)
    min_len = min(len(words1), len(words2))

    if min_len < 3:
        return False

    return overlap / min_len >= threshold

def main():
    tex_file = '/sessions/relaxed-tender-edison/mnt/uploads/bulbulia-j-a-cv.tex'
    bib_file = '/sessions/relaxed-tender-edison/mnt/website/cv/publications.bib'
    output_file = '/sessions/relaxed-tender-edison/mnt/website/cv/publications.bib'

    print("Reading LaTeX CV...")
    tex_content = read_file(tex_file)

    print("Extracting bibitem entries with PDF links...")
    cv_entries = extract_bibitems_with_pdfs(tex_content)
    print(f"Found {len(cv_entries)} entries with PDF links")

    # Show what we extracted
    print("\nCV entries with PDFs:")
    for e in cv_entries[:10]:
        print(f"  {e['key']}: DOI={e['doi']}, Title={e['title'][:50] if e['title'] else 'None'}...")

    print("\nReading BibTeX file...")
    parser = BibTexParser(common_strings=True)
    parser.customization = convert_to_unicode

    with open(bib_file, 'r', encoding='utf-8') as f:
        bib_db = bibtexparser.load(f, parser=parser)

    print(f"Found {len(bib_db.entries)} entries in BibTeX file")

    # Add PDF links to entries
    pdf_added = 0
    matched_entries = []

    for entry in bib_db.entries:
        # Skip if already has a file field
        if 'file' in entry:
            continue

        # Try to match by DOI first
        bib_doi = entry.get('doi', '').lower()
        bib_doi = re.sub(r'^https?://(dx\.)?doi\.org/', '', bib_doi)

        matched = False
        for cv_entry in cv_entries:
            if cv_entry['doi'] and bib_doi:
                # Normalize DOIs for comparison
                cv_doi_norm = cv_entry['doi'].replace('%2f', '/').lower()
                bib_doi_norm = bib_doi.replace('%2f', '/').lower()
                if cv_doi_norm == bib_doi_norm or cv_doi_norm in bib_doi_norm or bib_doi_norm in cv_doi_norm:
                    entry['file'] = cv_entry['pdf_url']
                    pdf_added += 1
                    matched_entries.append((entry['ID'], cv_entry['key'], 'DOI'))
                    matched = True
                    break

        if matched:
            continue

        # Try to match by title
        bib_title = entry.get('title', '')
        for cv_entry in cv_entries:
            if cv_entry['title'] and titles_match(bib_title, cv_entry['title']):
                entry['file'] = cv_entry['pdf_url']
                pdf_added += 1
                matched_entries.append((entry['ID'], cv_entry['key'], 'title'))
                matched = True
                break

    print(f"\nMatched {pdf_added} PDF links:")
    for bib_id, cv_key, match_type in matched_entries:
        print(f"  {bib_id} <- {cv_key} ({match_type})")

    # Write updated BibTeX
    print(f"\nWriting updated BibTeX to {output_file}...")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"% Publications for Joseph A. Bulbulia\n")
        f.write(f"% Generated: 2026-01-20\n")
        f.write(f"% Total entries: {len(bib_db.entries)}\n")
        f.write(f"% PDF links added: {pdf_added}\n\n")

        for entry in bib_db.entries:
            f.write(f"@{entry['ENTRYTYPE']}{{{entry['ID']},\n")

            # Write fields in order
            field_order = ['author', 'title', 'journal', 'booktitle', 'volume', 'number',
                          'pages', 'year', 'month', 'publisher', 'doi', 'url', 'file',
                          'issn', 'isbn', 'editor', 'note']

            written = set(['ENTRYTYPE', 'ID'])
            for field in field_order:
                if field in entry:
                    value = entry[field]
                    f.write(f"  {field} = {{{value}}},\n")
                    written.add(field)

            # Write remaining fields
            for field, value in entry.items():
                if field not in written:
                    f.write(f"  {field} = {{{value}}},\n")

            f.write("}\n\n")

    print("Done!")

if __name__ == '__main__':
    main()
